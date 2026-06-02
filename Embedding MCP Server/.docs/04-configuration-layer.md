# طبقة الإعدادات — Configuration Layer

## مبدأ Configurable System

**مصدر الحقيقة الوحيد هو config.** لا قيم hardcoded في الكود. تغيير الموديل أو نوع Vector DB أو transport يتم عبر config فقط، بدون تغيير سطر كود.

## Settings Model — Pydantic BaseSettings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Embedding Model ──
    embedding_model: str = "e5-small"            # "e5-small" | "e5-base"
    embedding_model_path: str = "models/multilingual-e5-small/onnx"
    embedding_device: str = "cpu"                # "cpu" | "cuda"
    embedding_dim: int = 384                     # يُشتق تلقائيًا من الموديل
    max_batch_size: int = 32

    # ── Vector DB ──
    vec_db_type: str = "faiss"                   # "faiss" | "pgvector" | "falkordb" | "ladybug" | "kuzu"
    vec_db_path: str = "data/vectors"
    pgvector_conn_str: str = ""
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379

    # ── MCP Transport ──
    mcp_transport: str = "local"                 # "local" (stdio) | "network" (sse)
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # ── Performance ──
    cache_size: int = 1000                       # LRU cache للـ embeddings
    request_timeout: int = 30                    # ثوانٍ

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
```

### Priority Order

```
1. Environment Variables    (الأعلى أولوية)
2. .env file
3. Default values           (الأدنى أولوية)
```

**مثال env vars:**

```bash
# .env
EMBEDDING_MODEL=e5-base
EMBEDDING_MODEL_PATH=models/multilingual-e5-base/onnx
EMBEDDING_DEVICE=cpu
EMBEDDING_DIM=768
VEC_DB_TYPE=faiss
VEC_DB_PATH=data/vectors
MCP_TRANSPORT=local
```

## Field Descriptions

| Config Field | الوصف | القيم الممكنة | الافتراضي |
|-------------|-------|---------------|-----------|
| `embedding_model` | اسم الموديل | `e5-small`, `e5-base` | `e5-small` |
| `embedding_model_path` | مسار ملفات الموديل (ONNX + tokenizer) | مسار مجلد | `models/multilingual-e5-small/onnx` |
| `embedding_device` | جهاز التشغيل | `cpu`, `cuda` | `cpu` |
| `embedding_dim` | بُعد المتجهات | 384 (e5-small), 768 (e5-base) | 384 |
| `max_batch_size` | الحد الأقصى لحجم الدفعة | 1–128 | 32 |
| `vec_db_type` | نوع قاعدة المتجهات | `faiss`, `pgvector`, `falkordb`, `ladybug`, `kuzu` | `faiss` |
| `vec_db_path` | مسار ملفات FAISS/Ladybug/Kuzu | مسار مجلد | `data/vectors` |
| `pgvector_conn_str` | PostgreSQL connection string | `postgresql://user:pass@host/db` | `""` |
| `falkordb_host` | FalkorDB host | hostname/IP | `localhost` |
| `falkordb_port` | FalkorDB port | port number | 6379 |
| `mcp_transport` | نوع MCP Transport | `local`, `network` | `local` |
| `mcp_host` | ربط الـ network server | IP | `0.0.0.0` |
| `mcp_port` | منفذ الـ network server | port number | 8000 |
| `cache_size` | حجم LRU cache للـ embeddings | integer | 1000 |
| `request_timeout` | مهلة الطلب بالثواني | integer | 30 |

## Validation — Pydantic validators

```python
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    embedding_model: str = "e5-small"
    embedding_dim: int = 384
    vec_db_type: str = "faiss"

    @field_validator("embedding_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        allowed = {"e5-small", "e5-base"}
        if v not in allowed:
            raise ValueError(f"الموديل '{v}' غير مدعوم. الاختيارات: {allowed}")
        return v

    @field_validator("vec_db_type")
    @classmethod
    def validate_vec_db(cls, v: str) -> str:
        allowed = {"faiss", "pgvector", "falkordb", "ladybug", "kuzu"}
        if v not in allowed:
            raise ValueError(f"Vector DB '{v}' غير مدعوم. الاختيارات: {allowed}")
        return v

    @field_validator("mcp_transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        allowed = {"local", "network"}
        if v not in allowed:
            raise ValueError(f"Transport '{v}' غير مدعوم")
        return v

    @field_validator("max_batch_size")
    @classmethod
    def validate_batch(cls, v: int) -> int:
        if v < 1 or v > 128:
            raise ValueError("max_batch_size بين 1 و 128")
        return v
```

### Cross-Field Validation

```python
@model_validator(mode="after")
def validate_dim_match(self):
    """التأكد أن dim يتطابق مع الموديل المختار."""
    expected = {"e5-small": 384, "e5-base": 768}
    if self.embedding_dim != expected.get(self.embedding_model):
        raise ValueError(
            f"{self.embedding_model} يتطلب dim={expected[self.embedding_model]}"
        )
    return self
```

## كيفية استخدام config

```python
# في main.py
config = Settings()                      # يقرأ env vars + .env + defaults
model = create_embedding_model(config)   # EmbeddingModelFactory
vec_db = create_vector_db(config)       # VectorDBFactory
service = EmbeddingService(model, vec_db)
```

### Switching بين Local و Network

```
# Local (stdio)
MCP_TRANSPORT=local  →  FastMCP(transport="stdio")

# Network (SSE)
MCP_TRANSPORT=network  →  FastMCP(transport="sse") + uvicorn
```

## Diagram — Config Flow

```
┌─────────────┐   ┌──────────┐   ┌──────────┐
│ Environment │   │  .env    │   │ Defaults │
│ Variables   │   │  file    │   │ (code)   │
└──────┬──────┘   └────┬─────┘   └────┬─────┘
       │               │              │
       └───────┬───────┴──────┬───────┘
               ▼              ▼
       ┌──────────────────────────┐
       │     Settings (Pydantic)  │
       │  • Validation            │
       │  • Cross-field checks    │
       └────────────┬─────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ EmbeddingModel  │   │   VectorDB      │
│ Factory         │   │   Factory       │
└─────────────────┘   └─────────────────┘
```
