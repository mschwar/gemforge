# Horizon 2: Semantic Immune System

**Status**: Prototype Phase  

Whenever the automated repair loop fixes a failing build, GemForge indexes the verified patch under `doc_type="repair"`, queries matching repairs automatically before future model calls for the same stage, and appends those prior bug fixes to the outgoing `SystemMessage` prompt.

## Architecture
- **Semantic Memory ([`core/memory/semantic_index.py`](../../../core/memory/semantic_index.py) and [`core/memory/retriever.py`](../../../core/memory/retriever.py))**: Stores verified repair patches in ChromaDB when installed, or falls back to local metadata storage in `memory/semantic/semantic_metadata.db`.
- **Context Injection ([`core/llm.py`](../../../core/llm.py))**: The `cost_aware_invoke` wrapper reads `current_node_id` from a `ContextVar` and queries semantic memory for prior `repair` entries matching that stage.
- **Node Execution ([`pipeline.py`](../../../pipeline.py))**: The `logged_node` decorator sets `current_node_id` around each stage invocation so individual node modules require no manual retrieval boilerplate.

## Prototype Notes
- `cost_aware_invoke` appends a `GLOBAL SEMANTIC IMMUNE SYSTEM (PAST LESSONS)` section to the active `SystemMessage` when matching repairs exist.
- Because [`core/repair/agentic_loop.py`](../../../core/repair/agentic_loop.py) calls `semantic_indexer.index_file(..., doc_type="repair")` after tests pass, the repair index grows only from verified fixes.

## How to Test the Prototype
1. Run a project build where `qa_node` triggers `repair_node`.
2. Confirm `repair_node` passes the test suite and indexes the patch with `doc_type="repair"`.
3. Start a second project run that executes the same stage so [`core/llm.py`](../../../core/llm.py) retrieves and injects the stored repair guidance.
4. Inspect `logs/gemforge.json.log` to verify the injected prompt context.
