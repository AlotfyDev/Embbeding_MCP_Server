# Stage Adapter Pattern — كل Stage عبارة عن Adapter

## Concept

Every pipeline stage implements the same abstract interface (`PipelineStage`). Stages are **composable, swappable, and testable** — just like the `EmbeddingModel` and `VectorDB` adapters in Phase 0. The pipeline becomes a chain of these adapters, each transforming `StageContext` and passing it forward.

## Core Abstraction

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageContext:
    """Context object passed between stages — carries data, config, and state.

    Each stage reads from and writes to this object. The pipeline
    initializes it once and passes it through the chain.
    """
    capability: str
    input_data: dict[str, Any]
    config: dict[str, Any] = field(default_factory=dict)
    output_data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)

    def add_error(self, code: str, message: str, stage: str | None = None) -> None:
        self.errors.append({
            "code": code,
            "message": message,
            "stage": stage or "unknown",
        })

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class PipelineStage(ABC):
    """Every stage follows this interface — name, validate, execute."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage name used in YAML config references."""

    @abstractmethod
    def validate(self, ctx: StageContext) -> bool:
        """Pre-execution validation. Return False to skip/stop."""

    @abstractmethod
    def execute(self, ctx: StageContext) -> StageContext:
        """Transform context. Must return ctx (mutated or new)."""

    # Optional lifecycle hooks
    def before_execute(self, ctx: StageContext) -> None:
        """Called before execute() — setup, logging, metrics start."""

    def after_execute(self, ctx: StageContext) -> None:
        """Called after execute() — cleanup, logging, metrics end."""

    def on_error(self, ctx: StageContext, error: Exception) -> None:
        """Called when execute() raises. Can mutate ctx as fallback."""
        ctx.add_error("STAGE_ERROR", str(error), stage=self.name)
```

## Error Types

```python
class StageError(Exception):
    """Base error for all stage failures."""
    def __init__(self, message: str, code: str = "STAGE_ERROR", stage: str | None = None):
        self.code = code
        self.stage = stage
        super().__init__(message)


class StageValidationError(StageError):
    """Raised when validate() fails — pipeline should stop."""
    def __init__(self, message: str, stage: str | None = None):
        super().__init__(message, code="STAGE_VALIDATION_ERROR", stage=stage)


class StageSkip(StageError):
    """Raised by execute() to signal 'skip this stage gracefully'.

    Not an error — the pipeline continues to the next stage.
    The context is passed through unchanged for this stage.
    """
    def __init__(self, message: str = "", stage: str | None = None):
        super().__init__(message, code="STAGE_SKIP", stage=stage)
```

## StageFactory

Each stage category gets its own factory. Factories are discoverable and registered by stage type.

```python
from abc import ABC, abstractmethod


class StageFactory(ABC):
    """Factory for a category of stages (pre_process, embed, store, ...)."""

    @abstractmethod
    def create(self, stage_config: dict) -> PipelineStage:
        """Instantiate a stage from its YAML config block."""

    @property
    @abstractmethod
    def stage_type(self) -> str:
        """Category name, e.g. 'pre_process', 'embed', 'store'."""


class PreProcessFactory(StageFactory):
    """Creates pre-processing stages by name."""

    _registry: dict[str, type[PipelineStage]] = {}

    @classmethod
    def register(cls, name: str, stage_cls: type[PipelineStage]) -> None:
        cls._registry[name] = stage_cls

    def create(self, stage_config: dict) -> PipelineStage:
        name = stage_config.get("stage")
        if name not in self._registry:
            raise StageError(f"Unknown pre_process stage: '{name}'")
        config = stage_config.get("config", {})
        return self._registry[name](**config)

    @property
    def stage_type(self) -> str:
        return "pre_process"


# Factory registry — extensible via register()
FACTORY_REGISTRY: dict[str, StageFactory] = {
    "pre_process": PreProcessFactory(),
    "embed": EmbedFactory(),
    "store": StoreFactory(),
    "post_process": PostProcessFactory(),
}


def create_stage(category: str, stage_config: dict) -> PipelineStage:
    """Top-level factory dispatch."""
    factory = FACTORY_REGISTRY.get(category)
    if not factory:
        raise StageError(f"Unknown stage category: '{category}'")
    return factory.create(stage_config)
```

## CompositeStage — Sub-Pipeline Composition

```python
class CompositeStage(PipelineStage):
    """A stage that wraps multiple sub-stages (sub-pipeline).

    Executes children in order. Each child receives the same context.
    Useful for grouping related transformations under one name.
    """

    def __init__(self, name: str, stages: list[PipelineStage]):
        self._name = name
        self._stages = stages

    @property
    def name(self) -> str:
        return self._name

    def validate(self, ctx: StageContext) -> bool:
        return all(stage.validate(ctx) for stage in self._stages)

    def execute(self, ctx: StageContext) -> StageContext:
        for stage in self._stages:
            if ctx.has_errors:
                break
            try:
                stage.before_execute(ctx)
                if stage.validate(ctx):
                    ctx = stage.execute(ctx)
                stage.after_execute(ctx)
            except StageSkip:
                continue
            except StageError:
                raise
            except Exception as e:
                stage.on_error(ctx, e)
                raise StageError(str(e), stage=stage.name) from e
        return ctx
```

## Pipeline — Top-Level Orchestrator

```python
class Pipeline:
    """Orchestrates a chain of stages for one capability.

    Owns the StageContext lifecycle and error boundaries.
    """

    def __init__(self, capability: str, stages: list[PipelineStage], version: str = "1.0"):
        self.capability = capability
        self._stages = stages
        self.version = version

    def execute(self, **params) -> Any:
        """Run the full pipeline.

        Args:
            **params: Input parameters matching the capability schema.

        Returns:
            Pipeline output (dict, list, or scalar).
        """
        ctx = StageContext(
            capability=self.capability,
            input_data=params,
        )

        for stage in self._stages:
            if ctx.has_errors:
                break
            try:
                stage.before_execute(ctx)
                if not stage.validate(ctx):
                    raise StageValidationError(
                        f"Validation failed for stage '{stage.name}'",
                        stage=stage.name,
                    )
                ctx = stage.execute(ctx)
                stage.after_execute(ctx)
            except StageSkip:
                logger.info("Stage '%s' skipped", stage.name)
                continue
            except StageValidationError:
                raise  # fatal — stop pipeline
            except StageError:
                raise
            except Exception as e:
                stage.on_error(ctx, e)
                raise StageError(
                    f"Unexpected error in stage '{stage.name}': {e}",
                    code="INTERNAL_ERROR",
                    stage=stage.name,
                ) from e

        if ctx.has_errors:
            raise StageError(
                "Pipeline completed with errors",
                code="PIPELINE_ERRORS",
            )

        return ctx.output_data
```

## Example: Document Ingestion Pipeline

### Stage Implementations

```python
class StripStage(PipelineStage):
    @property
    def name(self) -> str:
        return "strip"

    def validate(self, ctx: StageContext) -> bool:
        text = ctx.input_data.get("text", "")
        return isinstance(text, str) and len(text.strip()) > 0

    def execute(self, ctx: StageContext) -> StageContext:
        ctx.input_data["text"] = ctx.input_data["text"].strip()
        return ctx


class NormalizeWhitespaceStage(PipelineStage):
    @property
    def name(self) -> str:
        return "normalize_whitespace"

    def validate(self, ctx: StageContext) -> bool:
        return "text" in ctx.input_data

    def execute(self, ctx: StageContext) -> StageContext:
        import re
        ctx.input_data["text"] = re.sub(r'\s+', ' ', ctx.input_data["text"])
        return ctx


class EmbedStage(PipelineStage):
    def __init__(self, model, prefix: str = "passage: "):
        self._model = model
        self._prefix = prefix

    @property
    def name(self) -> str:
        return "embed"

    def validate(self, ctx: StageContext) -> bool:
        return "text" in ctx.input_data

    def execute(self, ctx: StageContext) -> StageContext:
        text = self._prefix + ctx.input_data["text"]
        ctx.output_data = self._model.embed(text)
        ctx.metadata["dim"] = len(ctx.output_data)
        return ctx


class StoreStage(PipelineStage):
    def __init__(self, vec_db):
        self._vec_db = vec_db

    @property
    def name(self) -> str:
        return "store"

    def validate(self, ctx: StageContext) -> bool:
        return "key" in ctx.input_data and ctx.output_data is not None

    def execute(self, ctx: StageContext) -> StageContext:
        self._vec_db.store(
            key=ctx.input_data["key"],
            vector=ctx.output_data,
            metadata=ctx.input_data.get("metadata"),
        )
        ctx.output_data = {
            "status": "stored",
            "key": ctx.input_data["key"],
            "dim": ctx.metadata.get("dim"),
        }
        return ctx
```

### Building the Pipeline

```python
# Manual construction (for testing / simple cases)
pipeline = Pipeline(
    capability="document.ingest",
    stages=[
        StripStage(),
        NormalizeWhitespaceStage(),
        EmbedStage(model=model),
        StoreStage(vec_db=vec_db),
    ],
)

result = pipeline.execute(
    key="doc-001",
    text="  Attention mechanism revolutionized NLP.  ",
    metadata={"type": "doc"},
)
# → {"status": "stored", "key": "doc-001", "dim": 384}
```

### From YAML Config

```python
# Auto-constructed from YAML (see 09-pipeline-config-format.md)
# pipelines/document-ingest.yaml →
#   pre_process: [strip, normalize_whitespace]
#   embed: {prefix: "passage: ", model_field: embedding_model}
#   store: {db_type_field: vec_db_type}

def build_pipeline_from_config(config: dict, settings: Settings) -> Pipeline:
    stages: list[PipelineStage] = []

    # Build pre_process stages
    for stage_cfg in config.get("pipeline", {}).get("pre_process", []):
        stage = create_stage("pre_process", stage_cfg)
        stages.append(stage)

    # Build embed stage
    embed_cfg = config.get("pipeline", {}).get("embed", {})
    if embed_cfg:
        model = create_embedding_model(settings)
        stages.append(EmbedStage(
            model=model,
            prefix=embed_cfg.get("prefix", "passage: "),
        ))

    # Build store stage
    store_cfg = config.get("pipeline", {}).get("store", {})
    if store_cfg:
        vec_db = create_vector_db(settings)
        stages.append(StoreStage(vec_db=vec_db))

    # Build post_process stages
    for stage_cfg in config.get("pipeline", {}).get("post_process", []):
        stage = create_stage("post_process", stage_cfg)
        stages.append(stage)

    return Pipeline(
        capability=config["capability"],
        stages=stages,
        version=config.get("version", "1.0"),
    )
```

## Stage Isolation Principle

Each stage is an isolated unit:

```
                    ┌─────────────────────┐
                    │     StageContext     │
                    │  input_data: {...}   │
                    │  output_data: Any    │
                    │  metadata: {...}     │
                    │  errors: [...]       │
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    PipelineStage     │
                    │                     │
                    │  1. before_execute  │  ← lifecycle hook
                    │  2. validate(ctx)   │  ← guard (bool)
                    │  3. execute(ctx)    │  ← transform
                    │  4. after_execute   │  ← lifecycle hook
                    │  5. on_error(err)   │  ← fallback hook
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │     StageContext     │  (mutated)
                    │  input_data: {...}   │  ← may be modified
                    │  output_data: Any    │  ← stage result
                    │  metadata: {...}     │  ← enriched
                    │  errors: [...]       │  ← appended if any
                    └─────────────────────┘
```

### Rules

1. **Validation before execution** — `validate()` runs first; if it returns `False`, the pipeline raises `StageValidationError` and stops.
2. **No cross-stage coupling** — A stage cannot access another stage's internals. Only `StageContext` passes data.
3. **Idempotent validation** — `validate()` must be side-effect-free (read-only on context).
4. **Deterministic execution** — Same context → same output (for pure stages; I/O stages like `store` are stateful by nature).
5. **StageSkip is not an error** — It signals "nothing to do here" and the pipeline continues.

## Error Propagation Flow

```
execute() called
    │
    ├─ StageValidationError  ──→ pipeline stops immediately
    ├─ StageSkip             ──→ continue to next stage
    ├─ StageError            ──→ pipeline stops (re-raised)
    └─ Exception             ──→ on_error() hook → StageError
```

## Summary

| Element | Role | Phase 0 Parallel |
|---------|------|-----------------|
| `PipelineStage` | Abstract interface for all stages | `EmbeddingModel ABC`, `VectorDB ABC` |
| `StageContext` | Data bus between stages | `SearchResult` dataclass |
| `StageFactory` | Creates stages by type/category | `EmbeddingModelFactory`, `VectorDBFactory` |
| `CompositeStage` | Groups sub-stages into one | — |
| `Pipeline` | Orchestrates stage chain | `EmbeddingService` (top-level) |
| `StageError` | Uniform error type | `EmbeddingError` hierarchy |
