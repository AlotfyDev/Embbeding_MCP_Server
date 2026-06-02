"""Pipeline system - capability-oriented composable execution flows."""
from __future__ import annotations

import inspect
import importlib
import pkgutil
import yaml
from pathlib import Path
from typing import Any

from embedding_mcp.pipelines.base import Pipeline, PipelineStage
from embedding_mcp.pipelines.router import CapabilityRouter


class PipelineAssembler:
    """Discovers stages, loads configs, builds pipelines automatically."""

    def __init__(self, pipelines_dir: str | Path, settings=None):
        self._pipelines_dir = Path(pipelines_dir)
        self._settings = settings
        self._stages: dict[str, type[PipelineStage]] = {}
        self._router = CapabilityRouter()

    def discover_stages(self) -> dict[str, type[PipelineStage]]:
        """Scan stages/*/ for PipelineStage subclasses."""
        stages_dir = self._pipelines_dir / "stages"
        if not stages_dir.exists():
            return {}

        for category_dir in stages_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            for module_info in pkgutil.iter_modules([str(category_dir)]):
                module = importlib.import_module(
                    f"embedding_mcp.pipelines.stages.{category_dir.name}.{module_info.name}"
                )
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PipelineStage)
                            and obj is not PipelineStage
                            and not inspect.isabstract(obj)):
                        instance = obj.__new__(obj)
                        stage_name = getattr(instance, "name", obj.__name__)
                        self._stages[stage_name] = obj

        return self._stages

    def load_configs(self) -> list[dict]:
        """Load all YAML configs from pipelines/configs/."""
        configs_dir = self._pipelines_dir / "configs"
        if not configs_dir.exists():
            return []

        configs = []
        for yaml_file in sorted(configs_dir.glob("*.yaml")):
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                if config:
                    config["_source"] = yaml_file.name
                    configs.append(config)
        return configs

    def build_pipeline(self, config: dict) -> Pipeline:
        """Build a Pipeline from a YAML config dict."""
        from embedding_mcp.pipelines.stages.validation import validate_input

        stages: list[PipelineStage] = []

        # Build each stage category
        for category in ["pre_process", "embed", "store", "search",
                         "compare", "management", "post_process"]:
            category_configs = config.get("pipeline", {}).get(category, [])
            if isinstance(category_configs, list):
                for stage_cfg in category_configs:
                    stage = self._build_single_stage(category, stage_cfg)
                    if stage:
                        stages.append(stage)
            elif isinstance(category_configs, dict):
                # Single dict config
                stage = self._build_single_stage(category, category_configs)
                if stage:
                    stages.append(stage)

        return Pipeline(
            capability=config["capability"],
            stages=stages,
            version=config.get("version", "1.0"),
            description=config.get("description", ""),
        )

    def _build_single_stage(self, category: str, config: dict) -> PipelineStage | None:
        """Instantiate one stage from config, injecting dependencies."""
        if not isinstance(config, dict):
            return None

        stage_name = config.get("stage", category)
        stage_cls = self._stages.get(stage_name)
        if not stage_cls:
            return None

        stage_config = self._resolve_settings_refs(config.get("config", {}))

        # Inject dependencies based on stage type
        kwargs = dict(stage_config)
        sig = inspect.signature(stage_cls.__init__)

        if "model" in sig.parameters and self._settings:
            from embedding_mcp.embedding_model.e5_model import create_embedding_model
            kwargs["model"] = create_embedding_model(
                self._settings.embedding_model,
                self._settings.embedding_model_path,
                self._settings.embedding_device,
            )
        if "vec_db" in sig.parameters and self._settings:
            from embedding_mcp.vector_db.factory import create_vector_db
            kwargs["vec_db"] = create_vector_db(
                self._settings.vec_db_type,
                self._settings.vec_db_path,
                self._settings.embedding_dim,
            )

        return stage_cls(**kwargs)

    def _resolve_settings_refs(self, config: dict) -> dict:
        """Replace ${setting_name} with actual Settings values."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                setting_name = value[2:-1]
                if self._settings:
                    resolved[key] = getattr(self._settings, setting_name, value)
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    def assemble(self) -> CapabilityRouter:
        """Full assembly: discover stages → load configs → build → register."""
        self.discover_stages()
        configs = self.load_configs()
        for config in configs:
            pipeline = self.build_pipeline(config)
            self._router.register(pipeline)
        return self._router


# Export main classes
from embedding_mcp.pipelines.base import PipelineStage, StageContext, StageError
from embedding_mcp.pipelines.router import CapabilityRouter, UnknownCapabilityError

__all__ = [
    "PipelineAssembler",
    "PipelineStage",
    "StageContext",
    "StageError",
    "CapabilityRouter",
    "UnknownCapabilityError",
]