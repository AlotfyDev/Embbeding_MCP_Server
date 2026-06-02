# طبقة خدمات التضمين — Embedding Service Layer

## مبدأ Service Layer

نفس فلسفة SDG: الـ Service هو **قلب التطبيق**. يحتوي كل Business Logic. لا يعرف MCP ولا نوع الـ Vector DB ولا نوع الموديل. يستقبل `EmbeddingModel` و `VectorDB` عبر Dependency Injection.

## EmbeddingService

```python
class EmbeddingService:
    def __init__(self, model: EmbeddingModel, vec_db: VectorDB):
        self._model = model
        self._vec_db = vec_db
```

### 1. embed_text — تضمين نص مفرد

```python
def embed_text(self, text: str) -> list[float]:
    """تضمين نص (document) → متجه."""
    self._validate_text(text)
    return self._model.embed(text)
```

**الاستخدام:** أنظمة تحتاج المتجه مباشرة، دون تخزين في DB.

### 2. embed_document — تضمين + تخزين

```python
def embed_document(self, text: str, key: str,
                   metadata: dict | None = None) -> None:
    """embed + تخزين في vector DB."""
    self._validate_text(text)
    vector = self._model.embed(text)
    self._vec_db.store(key, vector, metadata)
```

### 3. embed_batch_documents — معالجة مجمعة

```python
def embed_batch_documents(self, items: list[dict]) -> int:
    """items: [{text, key, metadata}, ...]"""
    stored = 0
    for item in items:
        self._validate_text(item["text"])
    for i in range(0, len(items), self._max_batch_size):
        batch = items[i:i + self._max_batch_size]
        texts = [b["text"] for b in batch]
        vectors = self._model.embed_batch(texts)
        db_items = []
        for j, b in enumerate(batch):
            db_items.append((b["key"], vectors[j], b.get("metadata")))
        self._vec_db.store_batch(db_items)
        stored += len(db_items)
    return stored
```

### 4. search_similar — بحث دلالي

```python
def search_similar(self, query: str, top_k: int = 10,
                   filters: dict | None = None) -> list[SearchResult]:
    """بحث دلالي: embed الاستعلام → search في DB."""
    self._validate_text(query)
    query_vec = self._model.embed_query(query)
    return self._vec_db.search(query_vec, top_k, filters)
```

### 5. find_similar_to_doc — بحث بوثيقة موجودة

```python
def find_similar_to_doc(self, doc_key: str,
                        top_k: int = 10) -> list[SearchResult]:
    """بحث باستخدام embedding وثيقة مخزنة مسبقًا."""
    # إرجاع SearchResult مع doc_key نفسها كـ first result
    # المتصل يتجاهل first result أو يستخدمه لمعرفة التشابه
    raise NotImplementedError("يتطلب get_vector_by_key في VectorDB")
```

### 6. hybrid_search — بحث هجين

```python
def hybrid_search(self, query: str, keywords: list[str],
                  top_k: int = 10) -> list[SearchResult]:
    """دلالي + كلمات مفتاحية. يبحث دلاليًا ثم ي boost النتائج المطابقة."""
    semantic_results = self.search_similar(query, top_k * 2)

    # Boost: النتائج التي تحتوي keywords في metadata تترفع score
    for r in semantic_results:
        text_content = r.metadata.get("text", "")
        keyword_matches = sum(1 for kw in keywords if kw.lower() in text_content.lower())
        r.score += keyword_matches * 0.1  # boost factor

    return sorted(semantic_results, key=lambda r: r.score, reverse=True)[:top_k]
```

### 7. compare_docs — مقارنة وثيقتين

```python
def compare_docs(self, key_a: str, key_b: str) -> float:
    """التشابه بين وثيقتين (cosine similarity)."""
    vec_a = self._model.embed(key_a)   # أو fetch من DB
    vec_b = self._model.embed(key_b)
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a**2 for a in vec_a)**0.5
    norm_b = sum(b**2 for b in vec_b)**0.5
    return dot / (norm_a * norm_b)
```

## Business Logic في الـ Service

### Prefix Management

| الطريقة | الـ prefix | الموديل المستخدم |
|---------|-----------|-----------------|
| `embed_text(text)` | `"passage: "` → `model.embed()` | للوثائق |
| `embed_query(query)` | `"query: "` → `model.embed_query()` | للاستعلامات |

```python
class EmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return self._model.embed(text)  # prefix داخلي في الموديل

    def embed_document(self, text: str, key: str,
                       metadata: dict | None = None):
        vector = self._model.embed(text)  # passage: text
        self._vec_db.store(key, vector, metadata)
```

### Validation

```python
MAX_TEXT_LENGTH = 5000  # حماية — أطول من max_seq_length

def _validate_text(self, text: str) -> None:
    if not text or not text.strip():
        raise ValidationError("النص فارغ")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError(f"النص يتجاوز {MAX_TEXT_LENGTH} حرفًا")
```

### Error Handling

```python
class EmbeddingError(Exception):
    def __init__(self, message: str, code: str = "EMBEDDING_ERROR"):
        self.code = code
        super().__init__(message)

class ModelLoadError(EmbeddingError): ...
class VectorDBError(EmbeddingError): ...
class DimensionMismatchError(EmbeddingError): ...
class ValidationError(EmbeddingError): ...
```

## Integration مع Spec-Driven Graph

### Auto-Suggest

عند إنشاء PRD جديد، SDG يستخدم EmbeddingService لاقتراح وثائق مشابهة:

```python
# في SDG OrchestrationService
def suggest_related_docs(self, prd_text: str) -> list[dict]:
    similar = self._embedding_service.search_similar(prd_text, top_k=5)
    return [
        {"key": r.key, "score": r.score, "metadata": r.metadata}
        for r in similar if r.score > 0.6
    ]
```

### Gap Detection

capability_matrix يبحث عن capabilities مشابهة:

```python
def find_similar_capabilities(self, capability_desc: str) -> list[str]:
    results = self._embedding_service.search_similar(
        capability_desc, top_k=3, filters={"type": "capability"}
    )
    return [r.key for r in results if r.score > 0.7]
```

## Health Check

```python
def health(self) -> dict:
    """التحقق من صحة النظام."""
    status = {"status": "ok", "model": "unknown", "vector_db": "unknown"}
    try:
        test_vec = self._model.embed("health check")
        status["model"] = f"dim={len(test_vec)}"
    except Exception as e:
        status["status"] = "error"
        status["model_error"] = str(e)
    try:
        status["vector_db"] = f"count={self._vec_db.count()}"
    except Exception as e:
        status["status"] = "error"
        status["vector_db_error"] = str(e)
    return status
```

## Diagram — Service Architecture

```
┌────────────────────────────────────────────────────┐
│                 EmbeddingService                    │
│                                                     │
│  embed_text()      embed_document()                │
│  embed_batch()     search_similar()                │
│  find_similar_to_doc()  hybrid_search()            │
│  compare_docs()    health()                        │
│                                                     │
│  ┌───────────── Business Logic ─────────────────┐  │
│  │ • Prefix Management (query: / passage:)      │  │
│  │ • Text Validation (length, empty)            │  │
│  │ • Dimension Check (model vs DB)              │  │
│  │ • Error Handling (EmbeddingError hierarchy)  │  │
│  └──────────────────────────────────────────────┘  │
└────────────┬──────────────────────────┬────────────┘
             │                          │
             ▼                          ▼
    ┌─────────────────┐       ┌──────────────────┐
    │ EmbeddingModel  │       │    VectorDB      │
    │ (ABC)           │       │    (ABC)         │
    │ E5Small/E5Base  │       │ FAISS/PgVector   │
    └─────────────────┘       └──────────────────┘
```
