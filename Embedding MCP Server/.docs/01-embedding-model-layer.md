# طبقة نماذج التضمين — Embedding Model Layer

## مبدأ Pluggable Model

جميع نماذج التضمين تقدم نفس الواجهة المجردة (ABC). الـ Service لا يعرف أي موديل يُستخدم — يتعامل مع `EmbeddingModel` فقط. اختيار الموديل يتم من config عبر `EmbeddingModelFactory`.

## EmbeddingModel ABC

```python
from abc import ABC, abstractmethod

class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def dim(self) -> int: ...
```

| Method | الغرض |
|--------|-------|
| `embed(text)` | تضمين نص مفرد (document) |
| `embed_batch(texts)` | تضمين مجموعة نصوص معًا (تحسين أداء) |
| `embed_query(text)` | تضمين استعلام بحث — يطبق query prefix |
| `dim` | بُعد المتجه (384 أو 768) |

## E5SmallONNX — تنفيذ multilingual-e5-small

```
المواصفات:
  - Architecture: BERT (via config.json)
  - dim: 384
  - max_seq_length: 512
  - vocab_size: 250037
  - Tokenizer: XLMRobertaTokenizer
  - Inference: ONNX Runtime (بدون torch)
```

```python
class E5SmallONNX(EmbeddingModel):
    def __init__(self, model_path: str, device: str = "cpu"):
        import onnxruntime as ort
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] \
                     if device == "cuda" else ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(
            f"{model_path}/model.onnx", providers=providers
        )
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._max_length = 512

    def embed(self, text: str) -> list[float]:
        return self._encode(text, prefix="passage: ")

    def embed_query(self, text: str) -> list[float]:
        return self._encode(text, prefix="query: ")

    def _encode(self, text: str, prefix: str = "") -> list[float]:
        # Tokenize → ONNX infer → Mean Pooling → Normalize
        inputs = self._tokenizer(
            prefix + text,
            max_length=self._max_length,
            padding="max_length", truncation=True,
            return_tensors="np"
        )
        outputs = self._session.run(None, {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        })[0]  # (1, seq_len, 384)
        # Mean pooling — تجاه padding tokens
        mask = inputs["attention_mask"][:, :, np.newaxis]
        embedding = (outputs * mask).sum(axis=1) / mask.sum(axis=1)
        # L2 Normalize
        norm = np.linalg.norm(embedding)
        return (embedding / norm).tolist()[0]

    @property
    def dim(self) -> int:
        return 384
```

### Pipeline — ONNX Inference

```
Input Text
    │
    ▼
Tokenizer (XLMRobertaTokenizer)
    │  truncation + padding → max_seq_length
    ▼
ONNX Runtime Session
    │  Transformer encoder forward pass
    ▼
Raw Embedding (1, seq_len, 384)
    │
    ▼
Mean Pooling ─── Attention Mask (تجاهل [PAD])
    │
    ▼
L2 Normalize
    │
    ▼
Unit Vector (384-dim)
```

## E5BaseONNX — تنفيذ multilingual-e5-base

```python
class E5BaseONNX(EmbeddingModel):
    def __init__(self, model_path: str, device: str = "cpu"):
        # نفس pattern لكن مع XLM-RoBERTa
        self._session = ort.InferenceSession(
            f"{model_path}/model.onnx",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
            if device == "cuda" else ["CPUExecutionProvider"]
        )
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._max_length = 514

    @property
    def dim(self) -> int:
        return 768
```

| الخاصية | E5Small | E5Base |
|---------|---------|--------|
| Model type | BERT | XLM-RoBERTa |
| dim | 384 | 768 |
| max_seq_length | 512 | 514 |
| vocab_size | 250,037 | 250,002 |
| ONNX opset | حسب التصدير | حسب التصدير |

## Prefix Management — معيار E5

موديلات E5 تفرّق بين queries و documents عبر prefix:

| الدور | prefix | يُستخدم في |
|-------|--------|-----------|
| Document (تخزين) | `"passage: "` | `embed()`, `embed_batch()` |
| Query (بحث) | `"query: "` | `embed_query()` |

**لماذا؟** الموديل يُدرّب بهذه الطريقة: نصوص الـ queries تأتي بعد "query:" ونصوص الوثائق بعد "passage:"، مما يحسّن جودة البحث الدلالي.

## EmbeddingModelFactory

```python
def create_embedding_model(config: Settings) -> EmbeddingModel:
    if config.embedding_model == "e5-small":
        return E5SmallONNX(config.embedding_model_path, config.embedding_device)
    elif config.embedding_model == "e5-base":
        return E5BaseONNX(config.embedding_model_path, config.embedding_device)
    else:
        raise ValueError(f"موديل غير مدعوم: {config.embedding_model}")
```

## Device Support

| الجهاز | ONNX Provider | الشرط |
|--------|---------------|-------|
| CPU | `CPUExecutionProvider` | افتراضي — لا حاجة لمكتبات إضافية |
| CUDA | `CUDAExecutionProvider` | يتطلب `onnxruntime-gpu` + CUDA toolkit |

## Batching Strategy

```python
def embed_batch(self, texts: list[str]) -> list[list[float]]:
    results = []
    for i in range(0, len(texts), self._max_batch_size):
        batch = texts[i:i + self._max_batch_size]
        batch_results = self._encode_batch(batch)
        results.extend(batch_results)
    return results
```

- `max_batch_size`: من config (افتراضي 32)
- الحماية: إذا تجاوز عدد النصوص الحد، يُقسّم إلى batches أصغر
- كل batch يُعالج دفعة واحدة عبر ONNX (tensor shape: [batch_size, seq_len, dim])

## Diagram — Model Layer

```
┌─────────────────────────────────────┐
│         EmbeddingModel (ABC)         │
│  embed()  embed_batch()  embed_query │
│  dim (property)                      │
└──────────────────┬──────────────────┘
                   │ implements
         ┌─────────┴──────────┐
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│  E5SmallONNX    │  │   E5BaseONNX    │
│  (384 dim)      │  │   (768 dim)     │
│  BERT + ONNX    │  │  XLM-R + ONNX   │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│   onnxruntime   │  │   onnxruntime   │
│  (CPU / CUDA)   │  │  (CPU / CUDA)   │
└─────────────────┘  └─────────────────┘
```
