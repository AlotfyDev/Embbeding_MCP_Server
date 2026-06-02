# تقييم Memgraph كبديل عن NetworkX في Graph Cache

## 1. ملخص Memgraph

| الخاصية | القيمة |
|---------|--------|
| **النوع** | In-memory graph database (client-server) |
| **الاستعلام** | Cypher (openCypher, Neo4j-compatible) |
| **النمط** | **Server منفصل فقط** — لا يوجد embedded mode |
| **Python API** | Neo4j driver (`neo4j`), GQLAlchemy (OGM), mgclient |
| **MCP** | **نعم** — MCP Server رسمي في `memgraph/ai-toolkit` |
| **التثبيت** | Docker / Linux .deb/.rpm / WSL / Build from source |
| **التخزين** | In-memory transactional (افتراضي) + on-disk transactional (تجريبي) + analytical mode |
| **Persistence** | WAL + Snapshots (تلقائية/يدوية) |
| **License** | BSL 1.1 (Community) + MEL (Enterprise) |
| **Cypher** | نعم، متوافق مع Neo4j 5.x |
| **Bolt protocol** | نعم، port 7687 |

## 2. الفروقات الحاسمة مع NetworkX

| البعد | NetworkX | Memgraph |
|-------|----------|----------|
| **نوع التشغيل** | in-process (مكتبة Python) | **client-server** (process منفصل) |
| **Latency للـ traversal** | **~0.5-2μs** (method call مباشر) | **~100-1000μs** (Bolt TCP round-trip) |
| **وقت التثبيت** | `pip install networkx` (ثوانٍ) | Docker pull + تشغيل container (دقائق) |
| **تعقيد الـ DevOps** | صفر | يحتاج Docker / systemd / monitoring |
| **استعلام** | `G.neighbors(n)` (Python) | `MATCH (n)-[r]->(m) RETURN m` (Cypher) |
| **حجم مناسب** | 1 - 10K nodes (in-process مثالي) | 100K - 1B nodes (client-server ضروري) |
| **Persistence** | لا (يفقد مع العملية) | نعم (WAL + snapshots) |
| **MCP** | لا يوجد | **نعم** — MCP Server جاهز |
| **License** | BSD (حر بالكامل) | **BSL** — قيود في الإنتاج التجاري |
| **ذاكرة (1000 عقدة)** | ~2-5 MB | ~200 MB (مع overhead الخادم) |
| **Multithreading** | GIL-bound | C++ native parallelism |

## 3. الإجابات على الأسئلة الحاسمة

### أ. هل يمكن تشغيل Memgraph كـ embedded in-process؟

**لا.** Memgraph هو **database server** منفصل. لا يوجد embedded Python mode مثل SQLite. يجب:
1. تشغيل Docker container (`memgraph/memgraph-mage` أو `memgraph/memgraph-platform`)
2. أو تثبيت حزمة Linux (Debian/Fedora)
3. أو تشغيل WSL على Windows

ثم الاتصال عبر Bolt protocol من Python.

### ب. قيمة مضافة لـ traversals في حجم مئات/آلاف العقد؟

**لا تذكر.** في هذا الحجم، NetworkX أسرع وأسهل. Memgraph يبرر وجوده في:
- **>100K عقدة**: يبدأ التفوق في الذاكرة والأداء
- **ACID transactions**: إذا كان الـ graph بحاجة لتعديلات مشاركة
- **Persistence عبر الجلسات**: NetworkX يفقد البيانات عند إعادة التشغيل

لكن Smart Task يبني الـ graph من الصفر عند بدء التشغيل ولا يحتاج persistence.

### ج. Latency Bolt protocol vs method call؟

**Bolt أبطأ بمعدل 100-1000 مرة.**
- NetworkX: 0.5-2 μs (دالة Python محلية)
- Bolt query (localhost): 100-1000 μs (TCP + serialization + deserialization)

في traversals كثيرة (مثلاً 1000 استعلام خلال session)، الفرق يصبح:
- NetworkX: ~1-2ms
- Memgraph: ~100-1000ms

### د. MCP support مباشر؟

**نعم.** Memgraph يوفر MCP Server رسمي في:
`github.com/memgraph/ai-toolkit/tree/main/integrations/mcp-memgraph`

```
docker run -p 7687:7687 memgraph/memgraph-mage --schema-info-enabled=True
```

ثم connect Claude أو أي MCP client. لكن هذا لا يلغي حاجة الـ Graph Cache layer — MCP server يوصل لـ Memgraph نفسه، لا يحل مشكلة الـ caching للـ traversals.

### هـ. هل BSL تسمح بالاستخدام التجاري المجاني؟

**للأسف لا — مع قيود.**
- BSL 1.1: يسمح بالاستخدام في **non-production** فقط مجانًا
- للإنتاج التجاري: تحتاج **Enterprise license** (MEL — مدفوع)
- بعد 4 سنوات من الإصدار، يتحول BSL تلقائيًا إلى **Apache 2.0** (حر)
- إذا كان المشروع في مرحلة التطوير/ما قبل الإنتاج، ممكن استخدام BSL مجانًا مؤقتًا

هذا خطر ترخيصي كبير مقارنة بـ **BSD** (دون أي قيود).

## 4. توصية السيناريو — هل نستبدل NetworkX بـ Memgraph؟

### الظروف الحالية لـ Smart Task:
- حجم البيانات: عشرات/مئات الوثائق (node count < 1000)
- Graph مبني عند startup، يُستخدم خلال session، يُعدم عند الخروج
- لا حاجة لـ persistence عبر الجلسات
- لا حاجة لـ ACID transactions
- الأولوية: **البساطة، السرعة، تقليل dependencies**

### التقييم الكمي (1000 عقدة، traversals متكررة):

| المعيار | Memgraph | NetworkX | الفائز |
|---------|----------|----------|--------|
| سرعة الـ traversal | ~200μs/query | ~1μs/call | **NetworkX** |
| وقت الإعداد | ~2 دقائق (Docker) | ~2 ثانية (pip install) | **NetworkX** |
| استهلاك RAM | ~200MB baseline | ~5MB | **NetworkX** |
| تعقيد الكود | Cypher queries + driver setup | Python methods | **NetworkX** |
| الـ dependencies | Docker + 1 package | package واحد | **NetworkX** |
| MCP integration | مباشر (server جاهز) | يحتاج wrapper | **Memgraph** |
| Persistence | نعم (تلقائي) | لا | **Memgraph** |
| Licensing | BSL (قيود تجارية) | BSD (حر) | **NetworkX** |

## 5. التوصية النهائية

**لا نستبدل NetworkX بـ Memgraph في هذه المرحلة.** Memgraph يضيف تعقيدًا تشغيليًا (Docker + server management)، latency أعلى بسبب Bolt protocol، وقيود ترخيصية (BSL/MEL) بدون فائدة حقيقية لحجم بيانات Smart Task الحالي.

**السيناريو الوحيد للنظر في Memgraph:** إذا نما حجم الـ doc_edges graph إلى >500K عقدة **و** أصبح persistence عبر الجلسات ضرورة، **و** أُخذ قرار بإدارة خادم إضافي في الـ stack. عندها، Memgraph يمكن أن يحل محل NetworkX بالكامل **ويوفر MCP Server جاهز** لربطه مع LLM agents.

**لحاليًا:** NetworkX + wrapper layer بسيط حوله (GraphCache class) هو الأفضل أداءً وبساطة وتكلفة.
