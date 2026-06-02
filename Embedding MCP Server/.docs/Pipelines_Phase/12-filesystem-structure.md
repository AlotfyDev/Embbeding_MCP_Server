# هيكل الملفات والمجلدات — Pipelines Phase Implementation

## Principle: Specialized Directories + Auto-Discovery Assembler

Each directory owns its concerns. The `PipelineAssembler` discovers all stages automatically from the filesystem — no manual registration. YAML configs drive pipeline composition, not code.

## Complete Directory Tree

```
Embedding MCP Server/
│
├── pipelines/                              ← NEW — جذر نظام الـ pipelines
│   ├── __init__.py                         ← PipelineAssembler, auto-discover
│   ├── router.py                           ← CapabilityRouter (من 07-capability-router.md)
│   ├── base.py                             ← Pipeline ABC, PipelineStage ABC, StageContext, errors
│   │
│   ├── stages/                             ← كل stage في مجلد متخصص
│   │   ├── __init__.py                     ← exports: discover_stages(), register_stages()
│   │   │
│   │   ├── pre_process/                    ← pre-processing stages
│   │   │   ├── __init__.py                 ← exports stage classes
│   │   │   ├── base.py                     ← PreProcessStage ABC (extends PipelineStage)
│   │   │   ├── strip.py                    ← StripStage
│   │   │   ├── normalize.py                ← NormalizeWhitespaceStage
│   │   │   ├── metadata_defaults.py        ← ApplyMetadataDefaultsStage
│   │   │   └── chunker.py                  ← TextChunkerStage (optional, future)
│   │   │
│   │   ├── embed/                          ← embedding stages
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     ← EmbedStage ABC
│   │   │   ├── passage_embed.py            ← PassageEmbedStage (document prefix)
│   │   │   └── query_embed.py              ← QueryEmbedStage (query prefix)
│   │   │
│   │   ├── store/                          ← storage stages
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     ← StoreStage ABC
│   │   │   ├── single_store.py             ← SingleStoreStage (vec_db.store)
│   │   │   └── batch_store.py              ← BatchStoreStage (vec_db.store_batch)
│   │   │
│   │   ├── search/                         ← search stages
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     ← SearchStage ABC
│   │   │   ├── semantic_search.py          ← SemanticSearchStage
│   │   │   └── hybrid_boost.py             ← HybridBoostStage (keyword boosting)
│   │   │
│   │   ├── compare/                        ← comparison stages
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     ← CompareStage ABC
│   │   │   ├── cosine_similarity.py        ← CosineSimilarityStage
│   │   │   └── fetch_vectors.py            ← FetchVectorsStage (future: get_vector_by_key)
│   │   │
│   │   ├── management/                     ← management stages (delete, count, health)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     ← ManagementStage ABC
│   │   │   ├── delete_stage.py             ← DeleteStage
│   │   │   ├── count_stage.py              ← CountStage
│   │   │   └── health_stage.py             ← HealthStage (model check + db check)
│   │   │
│   │   └── post_process/                   ← post-processing stages
│   │       ├── __init__.py
│   │       ├── base.py                     ← PostProcessStage ABC
│   │       ├── score_normalizer.py         ← ScoreNormalizerStage
│   │       ├── response_projector.py       ← ResponseProjectorStage (field filtering)
│   │       └── format_response.py          ← FormatResponseStage
│   │
│   ├── schemas/                            ← schema enforcement layer (تنفيذ 08-schema-enforcement-layer.md)
│   │   ├── __init__.py
│   │   ├── base.py                         ← DocumentSchema, FieldDef, FieldType
│   │   ├── registry.py                     ← SchemaRegistry (register, get, load_from_config)
│   │   └── loader.py                       ← SchemaLoader (YAML → DocumentSchema)
│   │
│   └── configs/                            ← YAML pipeline definitions (09-pipeline-config-format.md)
│       ├── document-ingest.yaml
│       ├── batch-ingest.yaml
│       ├── semantic-search.yaml
│       ├── hybrid-search.yaml
│       ├── document-compare.yaml
│       ├── document-delete.yaml
│       ├── document-count.yaml
│       └── system-health.yaml
│
├── config/
│   ├── __init__.py
│   ├── settings.py                         ← أضف: pipelines_dir: str = "pipelines"
│   │                                          أضف: default_capability: str = ""
│   └── ...
│
├── embedding_service/
│   ├── __init__.py
│   ├── service.py                          ← يبقى core business logic دون تغيير
│   │                                          (يُستدعى من stages عبر dependency injection)
│   ├── exceptions.py                       ← EmbeddingError hierarchy (موجود)
│   └── ...
│
├── mcp_local/
│   ├── __init__.py
│   ├── handlers.py                         ← يصبح thin layer ← يستدعي router.route()
│   │                                          (بدون capability → legacy flow)
│   └── tools.py                            ← يضيف capability parameter (اختياري)
│
├── mcp_network/
│   └── ...
│
└── tests/
    ├── pipelines/                          ← NEW — اختبارات نظام الـ pipelines
    │   ├── test_assembler.py
    │   ├── test_router.py
    │   ├── test_base.py
    │   ├── test_pre_process.py
    │   ├── test_embed.py
    │   ├── test_store.py
    │   ├── test_search.py
    │   ├── test_post_process.py
    │   ├── test_composite.py
    │   ├── test_schema_registry.py
    │   └── test_yaml_pipelines.py
    └── ...
```

## Directory and Module Roles

### `pipelines/base.py` — Core Abstractions

Contains the foundational ABCs all stages depend on:

| Export | Type | Description |
|--------|------|-------------|
| `PipelineStage` | ABC | `name`, `validate(ctx)`, `execute(ctx)`, lifecycle hooks |
| `StageContext` | dataclass | Data bus: `input_data`, `output_data`, `metadata`, `errors` |
| `Pipeline` | class | Orchestrator: owns context lifecycle, error boundaries |
| `CompositeStage` | class | Groups sub-stages into one logical stage |
| `StageError` | Exception | Base error |
| `StageValidationError` | Exception | Validation failure → stops pipeline |
| `StageSkip` | Exception | Graceful skip → continues pipeline |

### `pipelines/router.py` — Capability Router

Implements the router from `07-capability-router.md`:

| Export | Type | Description |
|--------|------|-------------|
| `CapabilityRouter` | class | Entry point: `route(capability, **params)` → result |
| `SchemaValidationMiddleware` | class | Middleware: validates params before pipeline execution |
| `ErrorHandlingMiddleware` | class | Middleware: catches and normalizes errors |
| `UnknownCapabilityError` | Exception | Raised when capability not registered |

### `pipelines/__init__.py` — PipelineAssembler

The assembler is the **entry point for wiring everything together**:

```python
# concept — design only, not implementation
from pathlib import Path
import importlib
import inspect
import pkgutil

class PipelineAssembler:
    """Discovers stages, loads configs, builds pipelines automatically."""

    def __init__(self, pipelines_dir: str | Path, settings):
        self._pipelines_dir = Path(pipelines_dir)
        self._settings = settings
        self._stages: dict[str, type[PipelineStage]] = {}
        self._router = CapabilityRouter()

    def discover_stages(self) -> dict[str, type[PipelineStage]]:
        """Scan stages/*/ for PipelineStage subclasses.

        Walks stages/pre_process/, stages/embed/, etc.
        Registers each class by its .name property (not class name).
        """
        stages_dir = self._pipelines_dir / "stages"
        if not stages_dir.exists():
            return {}

        for category_dir in stages_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            for module_info in pkgutil.iter_modules([str(category_dir)]):
                module = importlib.import_module(
                    f"pipelines.stages.{category_dir.name}.{module_info.name}"
                )
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PipelineStage)
                            and obj is not PipelineStage
                            and not inspect.isabstract(obj)):
                        instance = obj.__new__(obj)
                        stage_name = instance.name
                        self._stages[stage_name] = obj

        return self._stages

    def load_configs(self) -> list[dict]:
        """Load all YAML configs from pipelines/configs/."""
        configs_dir = self._pipelines_dir / "configs"
        if not configs_dir.exists():
            return []

        import yaml
        configs = []
        for yaml_file in sorted(configs_dir.glob("*.yaml")):
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                config["_source"] = yaml_file.name
                configs.append(config)
        return configs

    def build_pipeline(self, config: dict) -> Pipeline:
        """Build a Pipeline from a YAML config dict.

        Resolves stage names to classes, injects dependencies
        (model, vec_db) from settings, and chains stages in order.
        """
        stages: list[PipelineStage] = []

        for category in ["pre_process", "embed", "store", "search",
                         "compare", "management", "post_process"]:
            category_configs = config.get("pipeline", {}).get(category, [])
            if isinstance(category_configs, dict):
                # Single stage config (e.g. embed: {prefix: ..., model_field: ...})
                stage = self._build_single_stage(category, category_configs)
                if stage:
                    stages.append(stage)
            elif isinstance(category_configs, list):
                # List of stage configs (e.g. pre_process: [strip, normalize])
                for stage_cfg in category_configs:
                    stage = self._build_single_stage(category, stage_cfg)
                    if stage:
                        stages.append(stage)

        return Pipeline(
            capability=config["capability"],
            stages=stages,
            version=config.get("version", "1.0"),
        )

    def _build_single_stage(self, category: str, config: dict) -> PipelineStage | None:
        """Instantiate one stage from config, injecting dependencies."""
        if isinstance(config, dict) and "stage" in config:
            stage_name = config["stage"]
        elif isinstance(config, dict):
            stage_name = category  # e.g. embed stage named "embed"
        else:
            return None

        stage_cls = self._stages.get(stage_name)
        if not stage_cls:
            return None

        # Resolve $settings references
        stage_config = self._resolve_settings_refs(config.get("config", {}))

        # Inject dependencies based on stage type
        sig = inspect.signature(stage_cls.__init__)
        kwargs = {}
        if "model" in sig.parameters:
            from embedding_model.factory import create_embedding_model
            kwargs["model"] = create_embedding_model(self._settings)
        if "vec_db" in sig.parameters:
            from vector_db.factory import create_vector_db
            kwargs["vec_db"] = create_vector_db(self._settings)

        return stage_cls(**stage_config, **kwargs)

    def _resolve_settings_refs(self, config: dict) -> dict:
        """Replace ${setting_name} with actual Settings values."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                setting_name = value[2:-1]
                resolved[key] = getattr(self._settings, setting_name, value)
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
```

### `pipelines/stages/*/base.py` — Category-Specific ABCs

Each sub-directory has a `base.py` that extends `PipelineStage` with category-specific contracts:

| File | ABC | Additional Contract |
|------|-----|-------------------|
| `stages/pre_process/base.py` | `PreProcessStage` | `text_transform(text) → str` |
| `stages/embed/base.py` | `EmbedStage` | `prefix` property, `model` injection |
| `stages/store/base.py` | `StoreStage` | `vec_db` injection, key validation |
| `stages/search/base.py` | `SearchStage` | `vec_db` injection, score access |
| `stages/compare/base.py` | `CompareStage` | Similarity metric config |
| `stages/management/base.py` | `ManagementStage` | Read-only DB access |
| `stages/post_process/base.py` | `PostProcessStage` | Output formatting contract |

### `pipelines/schemas/` — Schema Enforcement Layer

Implements `08-schema-enforcement-layer.md`:

| File | Exports | Role |
|------|---------|------|
| `base.py` | `DocumentSchema`, `FieldDef`, `FieldType`, `SchemaValidationError` | Core schema types and validation logic |
| `registry.py` | `SchemaRegistry` | Register/get/load schemas, deep field path resolution |
| `loader.py` | `SchemaLoader` | YAML → `DocumentSchema` deserialization with versioning |

### `pipelines/configs/` — YAML Pipeline Definitions

One file per capability (see `09-pipeline-config-format.md`):

```
configs/
├── document-ingest.yaml     ← document.ingest
├── batch-ingest.yaml        ← document.ingest.batch
├── semantic-search.yaml     ← search.semantic
├── hybrid-search.yaml       ← search.hybrid
├── document-compare.yaml    ← document.compare
├── document-delete.yaml     ← document.delete
├── document-count.yaml      ← document.count
└── system-health.yaml       ← system.health
```

Each YAML declares `schema` (input validation), `pipeline` (stages), and capability metadata.

## Backward Compatibility: MCP Handler Transition

### Current (`mcp_local/handlers.py`)

```python
# Legacy flow — direct service call, no capability
def handle_search(service, query, top_k=10, filters="{}"):
    results = service.search_similar(query, top_k, json.loads(filters))
    return json.dumps([r.to_dict() for r in results])
```

### Future (Thin Router Delegation)

```python
# New flow — router delegates to pipeline
def handle_search(router, query, top_k=10, filters="{}"):
    result = router.route(
        "search.semantic",
        query=query,
        top_k=top_k,
        filters=json.loads(filters),
    )
    return json.dumps(result)
```

### Compatibility Layer

```python
class CompatRouter:
    """Wraps CapabilityRouter for backward compatibility.

    When no capability is provided, falls back to legacy behavior
    (direct EmbeddingService call) or a default pipeline.
    """

    def __init__(self, router: CapabilityRouter, fallback_service=None):
        self._router = router
        self._fallback = fallback_service

    def route(self, capability: str | None = None, **params) -> Any:
        if capability is None or capability == "":
            # Legacy fallback — infer from params shape
            return self._legacy_route(**params)
        return self._router.route(capability, **params)

    def _legacy_route(self, **params) -> Any:
        """Heuristic: guess capability from parameter names."""
        if "query" in params:
            return self._router.route("search.semantic", **params)
        if "items" in params:
            return self._router.route("document.ingest.batch", **params)
        if "key" in params and "text" in params:
            return self._router.route("document.ingest", **params)
        if "key" in params:
            return self._router.route("document.delete", **params)
        return self._router.route("system.health", **params)
```

## Stage Discovery Flow

```
PipelineAssembler.assemble()
    │
    ├─ 1. discover_stages()
    │      │
    │      ├─ scan stages/pre_process/*.py  →  StripStage, NormalizeStage, ...
    │      ├─ scan stages/embed/*.py         →  PassageEmbedStage, QueryEmbedStage
    │      ├─ scan stages/store/*.py         →  SingleStoreStage, BatchStoreStage
    │      ├─ scan stages/search/*.py        →  SemanticSearchStage, HybridBoostStage
    │      ├─ scan stages/compare/*.py       →  CosineSimilarityStage, FetchVectorsStage
    │      ├─ scan stages/management/*.py    →  DeleteStage, CountStage, HealthStage
    │      └─ scan stages/post_process/*.py  →  ScoreNormalizerStage, ResponseProjectorStage
    │
    ├─ 2. load_configs()
    │      │
    │      └─ read pipelines/configs/*.yaml  →  list[dict]
    │
    └─ 3. for each config:
           │
           ├─ resolve ${settings} references
           ├─ map stage names → stage classes (from step 1)
           ├─ inject dependencies (model, vec_db)
           ├─ build Pipeline(stages=[...])
           └─ router.register(pipeline)
```

## Dependency Injection Points

Stages receive external dependencies at construction time, not via globals:

| Dependency | Injected Into | Source |
|-----------|---------------|--------|
| `EmbeddingModel` | `EmbedStage`, `HealthStage` | `embedding_model/factory.py` |
| `VectorDB` | `StoreStage`, `SearchStage`, `DeleteStage`, `CountStage` | `vector_db/factory.py` |
| `Settings` | All stages via `PipelineAssembler` | `config/settings.py` |
| `SchemaRegistry` | `Router` (as middleware) | `pipelines/schemas/registry.py` |

## Settings Additions

Add to `config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Pipelines Phase
    pipelines_dir: str = "pipelines"           # root of pipeline system
    default_capability: str = ""               # legacy fallback capability
    pipeline_auto_discover: bool = True        # enable auto-discovery
    schema_dir: str = "pipelines/schemas"      # schema YAML files
    configs_dir: str = "pipelines/configs"     # pipeline YAML files
```

## Summary

| Concern | Mechanism | File(s) |
|---------|-----------|---------|
| Stage definition | `PipelineStage` ABC | `pipelines/base.py` |
| Stage categorization | Sub-directory ABCs | `pipelines/stages/*/base.py` |
| Stage implementation | Concrete classes | `pipelines/stages/*/*.py` |
| Pipeline composition | YAML + `PipelineAssembler` | `pipelines/configs/*.yaml`, `pipelines/__init__.py` |
| Request routing | `CapabilityRouter` | `pipelines/router.py` |
| Schema validation | `SchemaRegistry` + middleware | `pipelines/schemas/` |
| Dependency injection | `PipelineAssembler._build_single_stage()` | `pipelines/__init__.py` |
| Backward compatibility | `CompatRouter` | `pipelines/router.py` |

> **No manual registration.** Adding a new stage = create a file in the right `stages/*/` directory. Adding a new pipeline = create a YAML file in `configs/`. The assembler handles the rest.
