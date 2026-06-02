# 13. CLI Layer — لكل Pipeline CLI خاص به

## Principle: `PipelineCLI` — argparse Wrapper حول `CapabilityRouter`

كل capability في النظام لها واجهة CLI مخصصة. الـ `PipelineCLI` class هو class واحد يدير argparse subcommands ويرسل كل أمر إلى `CapabilityRouter.route()` — لا يوجد duplication ولا custom parsing لكل pipeline.

```
embedding-mcp pipeline run document-ingestion --key doc1 --text "..." --metadata '{"type":"doc"}'
embedding-mcp pipeline run semantic-search --query "AI" --top-k 5 --response-fields key,score
embedding-mcp pipeline list
embedding-mcp pipeline show document-ingestion
embedding-mcp pipeline validate document-ingestion
embedding-mcp pipeline run embed < input.txt          # STDIN pipe
```

## `PipelineCLI` Class

```python
# pipelines/cli.py
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .router import CapabilityRouter
from .base import StageContext, StageError


class PipelineCLI:
    """argparse-based CLI for pipeline operations.

    Delegates to CapabilityRouter — no business logic here.
    """

    def __init__(self, router: CapabilityRouter, program_name: str = "embedding-mcp"):
        self._router = router
        self._program_name = program_name

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog=self._program_name,
            description="Embedding MCP Pipeline CLI",
        )
        subparsers = parser.add_subparsers(dest="command", required=True)

        # pipeline subcommand group
        pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline operations")
        psub = pipeline_parser.add_subparsers(dest="pipeline_action", required=True)

        # pipeline list
        list_parser = psub.add_parser("list", help="List registered capabilities")
        list_parser.add_argument("--output", choices=["json", "text"], default="json")

        # pipeline show <capability>
        show_parser = psub.add_parser("show", help="Show pipeline details")
        show_parser.add_argument("capability", help="Capability name")
        show_parser.add_argument("--output", choices=["json", "text"], default="json")

        # pipeline validate <capability>
        validate_parser = psub.add_parser("validate", help="Validate pipeline config")
        validate_parser.add_argument("capability", help="Capability name")
        validate_parser.add_argument("--params", type=str, default="{}",
                                     help="JSON test params to validate against schema")
        validate_parser.add_argument("--output", choices=["json", "text"], default="json")

        # pipeline run <capability> [args...]
        run_parser = psub.add_parser("run", help="Execute a pipeline")
        run_parser.add_argument("capability", help="Capability to run")
        run_parser.add_argument("--output", choices=["json", "text"], default="json",
                                help="Output format")
        run_parser.add_argument("--response-fields", type=str, default=None,
                                help="Comma-separated response field projection")
        # Catch-all for pipeline-specific params: --key, --text, --query, --top-k, etc.
        run_parser.add_argument("--key", type=str, default=None, help="Document key")
        run_parser.add_argument("--text", type=str, default=None, help="Document text")
        run_parser.add_argument("--query", type=str, default=None, help="Search query")
        run_parser.add_argument("--top-k", type=int, default=None, help="Top-K results")
        run_parser.add_argument("--metadata", type=str, default=None,
                                help="JSON metadata string")
        run_parser.add_argument("--filters", type=str, default=None,
                                help="JSON filters string")
        run_parser.add_argument("--boost-factor", type=float, default=None,
                                help="Hybrid search boost factor")
        run_parser.add_argument("--prefix", type=str, default=None,
                                choices=["passage", "query", "none"],
                                help="Embedding prefix")
        run_parser.add_argument("--items", type=str, default=None,
                                help="JSON array for batch operations")
        # Extra kwargs — any additional --key=value pairs not explicitly listed
        run_parser.add_argument("extra", nargs="*",
                                help="Extra key=value pairs (advanced)")

        return parser

    def run(self, argv: list[str] | None = None) -> str:
        """Parse args and dispatch."""
        parser = self.build_parser()
        args = parser.parse_args(argv)

        if args.command == "pipeline":
            return self._handle_pipeline(args, parser)
        return parser.format_help()

    def _handle_pipeline(self, args: argparse.Namespace,
                         parser: argparse.ArgumentParser) -> str:
        action = args.pipeline_action

        if action == "list":
            return self._cmd_list(args)
        elif action == "show":
            return self._cmd_show(args)
        elif action == "validate":
            return self._cmd_validate(args)
        elif action == "run":
            return self._cmd_run(args)
        return parser.format_help()

    def _cmd_list(self, args: argparse.Namespace) -> str:
        capabilities = self._router.list_capabilities()
        if args.output == "text":
            lines = ["Registered capabilities:"]
            for cap in sorted(capabilities):
                lines.append(f"  - {cap}")
            return "\n".join(lines)
        return json.dumps({"capabilities": sorted(capabilities)})

    def _cmd_show(self, args: argparse.Namespace) -> str:
        info = self._router.describe(args.capability)
        if args.output == "text":
            lines = [
                f"Capability: {info.get('capability', args.capability)}",
                f"Version:    {info.get('version', 'N/A')}",
                f"Stages:",
            ]
            for stage in info.get("stages", []):
                lines.append(f"  - {stage}")
            schema = info.get("schema")
            if schema:
                lines.append(f"Input Schema: {json.dumps(schema, indent=2)}")
            return "\n".join(lines)
        return json.dumps(info)

    def _cmd_validate(self, args: argparse.Namespace) -> str:
        params = json.loads(args.params) if args.params else {}
        errors = self._router.validate(args.capability, **params)
        if args.output == "text":
            if errors:
                lines = [f"Validation errors for '{args.capability}':"]
                for e in errors:
                    lines.append(f"  - [{e.get('code')}] {e.get('message')}")
                return "\n".join(lines)
            return f"'{args.capability}' config is valid"
        return json.dumps({"valid": len(errors) == 0, "errors": errors})

    def _cmd_run(self, args: argparse.Namespace) -> str:
        # Build params from explicit args + extra key=value pairs
        params = self._build_params(args)

        # Support STDIN pipe: if --text not provided but stdin available, read it
        if not params.get("text") and not sys.stdin.isatty():
            params["text"] = sys.stdin.read().strip()

        # Response field projection
        if args.response_fields:
            params["response_fields"] = [
                f.strip() for f in args.response_fields.split(",")
            ]

        # Use StageContext-style input
        result = self._router.route(args.capability, **params)

        if args.output == "text":
            return self._format_as_text(args.capability, result)
        return json.dumps(result, ensure_ascii=False)

    def _build_params(self, args: argparse.Namespace) -> dict[str, Any]:
        params: dict[str, Any] = {}
        explicit_args = ["key", "text", "query", "top_k", "metadata",
                         "filters", "boost_factor", "prefix", "items"]
        for arg_name in explicit_args:
            py_name = arg_name.replace("-", "_")
            value = getattr(args, py_name, None)
            if value is not None:
                # Deserialize JSON strings
                if arg_name in ("metadata", "filters", "items"):
                    params[py_name] = json.loads(value)
                else:
                    params[py_name] = value

        # Parse extra key=value pairs
        for extra in getattr(args, "extra", []) or []:
            if "=" in extra:
                k, v = extra.split("=", 1)
                params[k.replace("-", "_")] = v

        return params

    def _format_as_text(self, capability: str, result: Any) -> str:
        """Human-readable output formatting."""
        if isinstance(result, list):
            if not result:
                return "No results"
            # Assume list of dicts (search results)
            lines = []
            for i, item in enumerate(result, 1):
                if isinstance(item, dict):
                    parts = [f"{i}. {item.get('key', item.get('id', f'result-{i}'))}"]
                    if "score" in item:
                        parts.append(f"    score={item['score']:.4f}")
                    if "text" in item:
                        text = item["text"][:100].replace("\n", " ")
                        parts.append(f"    text={text}...")
                    lines.append("\n".join(parts))
                else:
                    lines.append(f"{i}. {item}")
            return "\n".join(lines)

        if isinstance(result, dict):
            lines = [f"{k}: {v}" for k, v in result.items()]
            return "\n".join(lines)

        return str(result)
```

## STDIN Pipe Support

```bash
# STDIN pipe — النص يُقرأ من pipe بدلاً من --text
echo "Attention mechanism" | embedding-mcp pipeline run embed
cat document.txt | embedding-mcp pipeline run document-ingestion --key doc1

# الخوارزمية:
# 1. sys.stdin.isatty() → False (pipe)
# 2. اقرأ sys.stdin.read()
# 3. ضع النص في params["text"]
# 4. ارسل إلى router.route()
```

الـ handler يكتشف إذا كان stdin غير تفاعلي (`not isatty()`) ويقرأ المحتوى تلقائياً. هذا يسمح بـ UNIX pipe chaining:

```bash
curl -s https://example.com/doc.txt | embedding-mcp pipeline run document-ingestion --key web-doc-1
```

## Integration with `__main__.py`

```python
# __main__.py — إضافة pipeline subcommand
def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding MCP Server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Existing: local, network
    local_parser = subparsers.add_parser("local", ...)
    net_parser = subparsers.add_parser("network", ...)

    # NEW: pipeline subcommand
    pipeline_parser = subparsers.add_parser("pipeline", help="Pipeline operations")
    # لا نضيف args هنا — PipelineCLI يدير subparsers الداخلية

    args = parser.parse_args()

    if args.command == "pipeline":
        # ازالة "pipeline" من argv وتمرير الباقي إلى PipelineCLI
        pipeline_argv = sys.argv[sys.argv.index("pipeline"):]
        from pipelines.cli import PipelineCLI
        from pipelines import create_router  # factory function

        router = create_router()  # بناء CapabilityRouter مع discovery
        cli = PipelineCLI(router)
        output = cli.run(pipeline_argv)
        print(output)  # نص أو JSON
        return

    # ... existing local/network logic ...
```

## Pipeline Discovery درجات

`PipelineCLI` يعتمد على `CapabilityRouter` الذي يسجل الـ pipelines أثناء التجميع (`PipelineAssembler.assemble()`). مصادر البيانات:

| Source | Description |
|--------|-------------|
| `CapabilityRouter.list_capabilities()` | Returns all registered capability names |
| `CapabilityRouter.describe(capability)` | Returns dict with `name`, `version`, `stages`, `schema` |
| `CapabilityRouter.validate(capability, **params)` | Returns list of validation errors (empty = valid) |
| `CapabilityRouter.route(capability, **params)` | Executes pipeline and returns result |

## Output Format: JSON (default) vs Text

```bash
# JSON — machine-readable (default)
embedding-mcp pipeline run semantic-search --query "AI" --top-k 2
# → [{"key": "doc1", "score": 0.92, "text": "..."}, {"key": "doc2", "score": 0.87, "text": "..."}]

# Text — human-readable
embedding-mcp pipeline run semantic-search --query "AI" --top-k 2 --output text
# → 1. doc1
#      score=0.9200
#      text=Attention mechanism revolutionized...
# → 2. doc2
#      score=0.8700
#      text=Transformer architecture enables...
```

## Error Handling

```python
# إذا فشل pipeline، يرمي StageError
# PipelineCLI يمسكه ويعرض رسالة مناسبة
try:
    result = cli.run(sys.argv[1:])
    print(result)
except StageError as e:
    print(f"Pipeline error [{e.code}]: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(2)
```

## Summary: CLI Layer Architecture

```
User (terminal / script)
    │
    ├─ embedding-mcp pipeline run document-ingestion ...
    │
    ▼
PipelineCLI.run()
    │
    ├─ build_parser() → argparse → Namespace
    ├─ _cmd_run() → _build_params() → dict
    │
    ▼
CapabilityRouter.route(capability, **params)
    │
    ├─ SchemaValidationMiddleware.validate(params)
    ├─ Pipeline.execute(**params)
    │      ├─ Stage 1: validate → execute (pre_process)
    │      ├─ Stage 2: validate → execute (embed)
    │      ├─ Stage 3: validate → execute (store/search)
    │      └─ Stage 4: validate → execute (post_process)
    └─ ErrorHandlingMiddleware.catch()
    │
    ▼
Result (dict / list)
    │
    ▼
PipelineCLI → json.dumps() or _format_as_text()
    │
    ▼
STDOUT
```

## CLI Design Rules

1. **Thin CLI layer** — `PipelineCLI` يحتوي فقط على argparse logic وتحويل params. لا business logic.
2. **No per-pipeline argparse** — parser واحد يدير كل الـ capabilities عبر catch-all parameters (`--key`, `--text`, `--query`, إلخ).
3. **STDIN pipe** مدعوم لأي pipeline يقبل `text` parameter.
4. **`--output text`** يحول JSON إلى نص readable (للتجربة اليدوية).
5. **Error code** غير صفري للـ pipeline errors (`exit 1`) و unexpected errors (`exit 2`).
