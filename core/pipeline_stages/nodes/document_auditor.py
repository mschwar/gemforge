import os
import json
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from tools.ingestor_tools import bundle_context
from state import PipelineState

def document_auditor_node(state: PipelineState):
    path = state.get("source_docs_path")
    if not path or not os.path.exists(path):
        print("⏭️  Skipping Document Auditor (no path provided)")
        return {"audited_context": None}

    print(f"🔨 0. Document Auditor sifting through {path}...")
    context_bundle, context_stats = bundle_context(
        path,
        raw_idea=state.get("raw_idea", ""),
        include_stats=True,
    )
    print(
        "   → Context bundle: "
        f"{context_stats['included_files']} files, "
        f"{context_stats['total_chars']} chars, "
        f"~{context_stats['estimated_tokens']} tokens"
    )
    if context_stats["dropped_by_budget"] or context_stats["dropped_oversized_file"]:
        print(
            "   ⚠️ Context budget trimming: "
            f"dropped={context_stats['dropped_by_budget']}, "
            f"oversized={context_stats['dropped_oversized_file']}, "
            f"truncated={context_stats['truncated_files']}"
        )
    
    prompt = load_prompt("28_document_auditor.md")
    user_content = f"DIRECTORY_CONTEXT:\n\n{context_bundle}\n\nRAW_IDEA: {state['raw_idea']}"
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_content)]
    response = cost_aware_invoke(messages)
    
    print("   → Audit complete. Nucleus extracted.")
    return {
        "audited_context": response.content,
        "progress_log": [
            "✅ Document Audit complete",
            "📊 CONTEXT_BUDGET "
            + json.dumps(
                {
                    "included_files": context_stats["included_files"],
                    "dropped_by_budget": context_stats["dropped_by_budget"],
                    "dropped_oversized_file": context_stats["dropped_oversized_file"],
                    "truncated_files": context_stats["truncated_files"],
                    "estimated_tokens": context_stats["estimated_tokens"],
                },
                sort_keys=True,
            ),
        ],
    }
