import os
import json
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from tools.project_tools import apply_template, parse_platform_manifest
from state import PipelineState
from .utils import _index_files

def code_orchestrator_node(state: PipelineState):
    print("🔨 6. Code Generation Orchestrator — launching real generators...")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    from tools.executor_tools import build_and_verify_xcode, parse_and_save_generated_code

    manifest_path = f"{repo_path}/PLATFORM_MANIFEST.md"
    manifest_content = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as manifest_file:
            manifest_content = manifest_file.read()
    manifest_data = parse_platform_manifest(manifest_content)

    template_hint = (
        manifest_data.get("template")
        or manifest_data.get("selected_platform")
        or state.get("selected_template")
    )
    
    if not template_hint:
        raise ValueError("CRITICAL: Platform Decision Agent failed to produce a valid template selection.")

    template_result = apply_template(repo_path, template_hint)
    template_metadata = template_result.get("metadata", {})
    selected_platform = template_result.get("platform", template_hint)
    supports_llm_generators = bool(template_metadata.get("supports_llm_generators", False))

    progress = [f"✅ Template applied: {template_result.get('name')} ({selected_platform})"]

    def _safe_read(path: str) -> str:
        try:
            return sandbox.safe_read(path)
        except Exception:
            return ""

    generator_context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"STAFF_AUDIT:\n{state.get('audited_context', 'N/A')}\n\n"
        f"UIUX_SPEC:\n{_safe_read('UIUX_SPEC.md')}\n\n"
        f"ARCHITECTURE:\n{_safe_read('ARCHITECTURE.md')}\n\n"
        f"PLATFORM_MANIFEST:\n{manifest_content}"
    )

    if supports_llm_generators:
        min_generator_writes = max(1, int(os.getenv("GEMFORGE_MIN_GENERATOR_WRITES", "1")))
        generator_write_counts = {}

        # 1. UI Code Generator
        prompt = load_prompt("16_ui_code_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        ui_response = cost_aware_invoke(messages)
        ui_paths = parse_and_save_generated_code(
            sandbox,
            ui_response.content,
        )
        generator_write_counts["ui_code_generator"] = len(ui_paths)
        _index_files(state["run_id"], gem_name, ui_paths, "source")

        # 2. Core Logic Generator
        prompt = load_prompt("17_core_logic_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        logic_response = cost_aware_invoke(messages)
        logic_paths = parse_and_save_generated_code(
            sandbox,
            logic_response.content,
        )
        generator_write_counts["core_logic_generator"] = len(logic_paths)
        _index_files(state["run_id"], gem_name, logic_paths, "source")

        # 3. Platform-Specific Generator
        prompt = load_prompt("18_platform_specific_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        platform_response = cost_aware_invoke(messages)
        platform_paths = parse_and_save_generated_code(
            sandbox,
            platform_response.content,
        )
        generator_write_counts["platform_specific_generator"] = len(platform_paths)
        _index_files(state["run_id"], gem_name, platform_paths, "source")

        malformed_generators = [
            name for name, writes in generator_write_counts.items() if writes < min_generator_writes
        ]
        if malformed_generators:
            error_payload = {
                "error_code": "GENERATOR_OUTPUT_MALFORMED",
                "min_generator_writes": min_generator_writes,
                "generator_write_counts": generator_write_counts,
                "malformed_generators": malformed_generators,
            }
            try:
                sandbox.safe_write(
                    "GENERATOR_FAILURE.json",
                    json.dumps(error_payload, indent=2, sort_keys=True),
                )
            except PermissionError as e:
                # Non-critical, just log warning
                handle_io_error(state, e, "code orchestrator (failure log)", critical=False)
            print(f"   ❌ GENERATOR_OUTPUT_MALFORMED: {json.dumps(error_payload, sort_keys=True)}")
            raise ValueError(f"GENERATOR_OUTPUT_MALFORMED::{json.dumps(error_payload, sort_keys=True)}")

        progress.append(f"✅ LLM code generators completed ({generator_write_counts})")
    else:
        progress.append("✅ Template-only code path selected (no LLM generators)")

    # 4. Project structure / build verification
    if selected_platform == "ios-swiftui":
        app_name = template_result.get("context", {}).get("APP_NAME_SAFE", "GemForgeApp")
        generate_xcode_project(repo_path, app_name)
        build_and_verify_xcode(repo_path)
        progress.append("✅ iOS project structure + build verification complete")
    else:
        validation = template_result.get("validation", {})
        if validation.get("valid", False):
            progress.append("✅ Template validation complete")
        else:
            progress.append(
                f"⚠️ Template validation missing files: {validation.get('missing_files', [])}"
            )

    return {
        "selected_platform": selected_platform,
        "selected_template": template_result.get("name"),
        "platform_manifest": manifest_data,
        "progress_log": progress,
    }
