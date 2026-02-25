# Horizon 2: The Semantic Immune System

**Status**: Prototype Phase
**Impact**: 100x Quality Improvement & Token Reduction

## The Leap
Upgrade the system to develop a shared, global semantic memory. Every bug fixed by the `agentic_loop` (Surgeon) is embedded into a Vector Database. The orchestrator automatically intercepts every LLM prompt to inject context from globally resolved bugs relevant to the current node *before* code generation begins.

## Architecture
- **Semantic Memory (`core/memory/semantic_index.py` & `retriever.py`)**: Uses `chromadb` (if installed) or gracefully degrades to a no-op/local file mock to store successful repair patches.
- **Context Injection (`core/llm.py`)**: The `cost_aware_invoke` wrapper checks the active `current_node_id` via a ContextVar. If active, it autonomously queries the semantic memory for past `repair` documents related to this node's responsibility.
- **Node Execution (`pipeline.py`)**: The `logged_node` decorator sets the `current_node_id` ContextVar automatically for every node, making the injection completely transparent to the rest of the codebase.

## Implementation Details (Prototype)
- The prototype hooks directly into `cost_aware_invoke`.
- It appends a `### GLOBAL SEMANTIC IMMUNE SYSTEM (PAST LESSONS) ###` block to the existing `SystemMessage`.
- Because the `agentic_loop` already calls `semantic_indexer.index_file(..., doc_type="repair")`, the knowledge base populates itself automatically as the system fixes its own bugs!

## How to Test the Prototype
1. Run the system normally. When an agent fails, the `repair_node` will trigger.
2. If the `repair_node` fixes the issue, it will index the fix in the Vector Database with `doc_type="repair"`.
3. The next time *any* project runs a similar node, `core/llm.py` will pull that fix and inject it into the `SystemMessage` automatically.
4. You can observe the LLM context injection in the `logs/gemforge.json.log` file.
