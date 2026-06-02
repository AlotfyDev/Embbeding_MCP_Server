"""Pipeline stages package - auto-discovers and exports all stages."""
import importlib
import inspect
import pkgutil
from pathlib import Path

from embedding_mcp.pipelines.base import PipelineStage


def discover_stages() -> dict[str, type[PipelineStage]]:
    """Discover all PipelineStage subclasses in stages/ subdirectories."""
    stages = {}
    stages_dir = Path(__file__).parent / "stages"

    if not stages_dir.exists():
        return stages

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
                    # Get instance name property
                    try:
                        instance = obj.__new__(obj)
                        stage_name = instance.name
                        stages[stage_name] = obj
                    except Exception:
                        pass

    return stages


__all__ = ["discover_stages"]