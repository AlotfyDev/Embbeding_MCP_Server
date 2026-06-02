# طبقة قواعد المتجهات — Vector DB Adapter Layer

## مبدأ Adapter Pattern

نفس فلسفة Repository/SQLite في SDG: **واجهة مجردة واحدة (ABC)، تنفيذات متعددة**. الـ Service لا يعرف نوع قاعدة المتجهات — يتعامل مع `VectorDB` فقط. تغيير DB يتطلب تغيير config فقط.

## VectorDB ABC

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SearchResult:
    key: str
    score: float
    metadata: dict

class VectorDB(ABC):
    @abstractmethod
    def store(self, key: str, vector: list[float],
              metadata: dict | None = None) -> None: ...

    @abstractmethod
    def store_batch(self, items: list[tuple[str, list[float],
                                            dict | None]]) -> None: ...

    @abstractmethod
    def search(self, vector: list[float], top_k: int = 10,
               filters: dict | None = None) -> list[SearchResult]: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...
```

| Method | الغرض |
|--------|-------|
| `store(key, vector, metadata)` | تخزين متجه مع مفتاح وبيانات وصفية |
| `store_batch(items)` | تخزين مجموعة (أداء أفضل) |
| `search(vector, top_k, filters)` | بحث أقرب الجيران. `filters` شرط على metadata |
| `delete(key)` | حذف متجه بمفتاحه |
| `count()` | عدد المتجهات المخزنة |
| `clear()` | مسح كل المتجهات |

## FAISSAdapter — Index In-Memory

```python
import faiss
import numpy as np

class FAISSAdapter(VectorDB):
    def __init__(self, db_path: str, dim: int):
        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)  # Inner Product ≈ cosine
        self._keys: list[str] = []
        self._metadata: dict[str, dict] = {}
        self._db_path = db_path
        self._load()

    def store(self, key: str, vector: list[float],
              metadata: dict | None = None) -> None:
        vec = np.array([vector], dtype=np.float32)
        self._index.add(vec)
        self._keys.append(key)
        if metadata:
            self._metadata[key] = metadata

    def search(self, vector: list[float], top_k: int = 10,
               filters: dict | None = None) -> list[SearchResult]:
        vec = np.array([vector], dtype=np.float32)
        scores, indices = self._index.search(vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            key = self._keys[idx]
            meta = self._metadata.get(key, {})
            if filters and not self._matches_filters(meta, filters):
                continue
            results.append(SearchResult(key=key, score=float(score),
                                        metadata=meta))
        return results
```

**لماذا IndexFlatIP؟** كل المتجهات طبيعية (L2 normalized) → Inner Product = Cosine Similarity. للـ large-scale: `IndexIVFFlat` أو `IndexHNSWFlat` من config.

### Save / Load from Disk

```python
def _save(self):
    faiss.write_index(self._index, f"{self._db_path}/index.faiss")
    import pickle
    with open(f"{self._db_path}/meta.pkl", "wb") as f:
        pickle.dump({"keys": self._keys, "metadata": self._metadata}, f)

def _load(self):
    import os, pickle
    if os.path.exists(f"{self._db_path}/index.faiss"):
        self._index = faiss.read_index(f"{self._db_path}/index.faiss")
        with open(f"{self._db_path}/meta.pkl", "rb") as f:
            data = pickle.load(f)
            self._keys = data["keys"]
            self._metadata = data["metadata"]
```

## PgVectorAdapter — PostgreSQL + pgvector

```python
import asyncpg  # أو sqlalchemy

class PgVectorAdapter(VectorDB):
    def __init__(self, conn_str: str, dim: int):
        self._conn_str = conn_str
        self._dim = dim
        # CREATE TABLE vec_embeddings (
        #     key TEXT PRIMARY KEY,
        #     embedding vector(384),  -- dim من config
        #     metadata JSONB
        # );
        # CREATE INDEX ON vec_embeddings USING ivfflat (embedding vector_cosine_ops);
```

- **Table:** `vec_embeddings(key TEXT, embedding vector(N), metadata JSONB)`
- **Index:** IVFFlat (cosine) للبحث السريع
- **Metadata filters:** WHERE metadata->>'field' = 'value' مباشرة في SQL

## FalkorDBAdapter — Graph + Vector

```python
class FalkorDBAdapter(VectorDB):
    def __init__(self, host: str, port: int, dim: int):
        # FalkorDB: كل متجه يُخزّن كـ node property
        # CREATE VECTOR INDEX FOR (n:Embedding) ON (n.embedding) DIMENSION {dim}
        self._conn = FalkorDB(host=host, port=port)
```

## LadybugAdapter — LadybugDB

```python
class LadybugAdapter(VectorDB):
    def __init__(self, db_path: str, dim: int):
        # يتصل بـ lbug.exe
        self._client = LadybugClient(f"{db_path}/vectors.lbug")
```

## KuzuDBAdapter — Kùzu Embedded

```python
class KuzuDBAdapter(VectorDB):
    def __init__(self, db_path: str, dim: int):
        import kuzu
        self._db = kuzu.Database(f"{db_path}/kuzu_vec")
        self._conn = kuzu.Connection(self._db)
        # CREATE NODE TABLE Embedding(key STRING, embedding FLOAT[{dim}],
        #                            metadata JSON, PRIMARY KEY(key))
```

## VectorDBFactory

```python
def create_vector_db(config: Settings) -> VectorDB:
    if config.vec_db_type == "faiss":
        return FAISSAdapter(config.vec_db_path, config.embedding_dim)
    elif config.vec_db_type == "pgvector":
        return PgVectorAdapter(config.pgvector_conn_str, config.embedding_dim)
    elif config.vec_db_type == "falkordb":
        return FalkorDBAdapter(config.falkordb_host, config.falkordb_port,
                               config.embedding_dim)
    elif config.vec_db_type == "ladybug":
        return LadybugAdapter(config.vec_db_path, config.embedding_dim)
    elif config.vec_db_type == "kuzu":
        return KuzuDBAdapter(config.vec_db_path, config.embedding_dim)
    else:
        raise ValueError(f"Vector DB غير مدعوم: {config.vec_db_type}")
```

## Dimension Matching

**قاعدة:** `config.embedding_dim` يُشتق تلقائيًا من الموديل (384 أو 768). عند إنشاء الـ DB:

```python
# في EmbeddingService عند التهيئة
if model.dim != vec_db.dim:
    raise DimensionMismatchError(
        f"موديل dim={model.dim} لا يتطابق مع DB dim={vec_db.dim}"
    )
```

كل Adapter يتحقق من dim عند `store()`:

```python
def store(self, key: str, vector: list[float], metadata: dict | None = None):
    if len(vector) != self._dim:
        raise DimensionMismatchError(
            f"متجه بطول {len(vector)}، المتوقع {self._dim}"
        )
```

## Diagram — Service → VectorDB

```
┌─────────────────────┐
│  EmbeddingService   │
│  (لا يعرف نوع DB)   │
└──────────┬──────────┘
           │ store / search / delete
           ▼
┌──────────────────────┐
│   VectorDB (ABC)     │
│  store  store_batch  │
│  search  delete      │
│  count  clear        │
└──────────┬───────────┘
           │ implements
     ┌─────┴──────┬──────────┬──────────┬──────────┐
     ▼            ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  FAISS  │ │PgVector │ │FalkorDB│ │Ladybug │ │ KuzuDB │
│Adapter  │ │Adapter  │ │Adapter │ │Adapter │ │Adapter │
├─────────┤ ├─────────┤ ├────────┤ ├────────┤ ├────────┤
│In-Memory│ │Postgres │ │GraphDB │ │lbug.exe│ │Kùzu    │
│+Disk    │ │+pgvector│ │+Vector │ │        │ │Embedded│
└─────────┘ └─────────┘ └────────┘ └────────┘ └────────┘
```
