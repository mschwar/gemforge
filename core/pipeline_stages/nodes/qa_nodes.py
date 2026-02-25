from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from tools.executor_tools import run_tests
from state import PipelineState
from .utils import _index_files, parse_and_save_docs

def qa_generator_node(state: PipelineState):
    """19_qa_generator.md — generates platform-appropriate tests"""
    print("🧪 19. QA Generator running...")
    prompt = load_prompt("19_qa_generator.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project at: {repo_path}\nPlatform: {state['selected_platform']}\nGenerate tests now.")]
    response = cost_aware_invoke(messages)
    try:
        saved, saved_paths = parse_and_save_docs(response.content, sandbox)
        _index_files(state["run_id"], gem_name, saved_paths, "test")
    except PermissionError as e:
        return handle_io_error(state, e, "qa generator")
    return {
        "tests_generated": True,
        "test_report": "Tests generated — see TESTS_SUMMARY.md",
        "progress_log": [f"🧪 Generated tests for {state['selected_platform']}"]
    }

def qa_node(state: PipelineState):
    """Executes the tests via run_tests and decides pass/fail"""
    print("🧪 20. QA Executor running...")
    if not state.get("repo_path"):
        return {"tests_passed": False, "test_report": "No repo_path — skipping tests", "progress_log": ["⚠️ QA skipped (no repo)"]}
    test_result = run_tests(state["repo_path"], state["selected_platform"])
    return {
        "tests_passed": test_result["success"],
        "test_report": test_result["report"],
        "test_details": test_result.get("details", ""),
        "progress_log": [f"🧪 QA Result: {test_result['report']} ({test_result['failures']} failures)"]
    }

def director_node(state: PipelineState):
    print("🎬 20b. Director Review running...")
    prompt = load_prompt("13_director.md")
    repo_path = state.get("repo_path", "")
    sandbox = ProjectSandbox(repo_path)
    
    def _safe_read(filename):
        try:
            return sandbox.safe_read(filename)
        except Exception:
            return f"[{filename} not yet available]"

    context = (
        f"POLISHED_VISION:\n{state['polished_vision']}\n\n"
        f"ARCHITECTURE:\n{_safe_read('ARCHITECTURE.md')}\n\n"
        f"FRONTEND_SPEC:\n{_safe_read('FRONTEND_SPEC.md')}\n\n"
        f"BACKEND_SPEC:\n{_safe_read('BACKEND_SPEC.md')}\n\n"
        f"DATA_SPEC:\n{_safe_read('DATA_SPEC.md')}\n\n"
        f"QA_REPORT:\n{state.get('test_report', 'N/A')}"
    )
    
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    
    if repo_path:
        try:
            sandbox.safe_write("DIRECTOR_REVIEW.md", response.content)
            print("   → DIRECTOR_REVIEW.md saved")
        except PermissionError as e:
            handle_io_error(state, e, "director (review save)", critical=False)
        
    is_green = "GREEN LIGHT" in response.content.upper()
    rejection_count = state.get("director_rejection_count", 0)
    tests_passed = bool(state.get("tests_passed", False))

    if not tests_passed:
        is_green = False
        print("   ⚠️  QA gate failed — director approval blocked.")

    if not is_green:
        rejection_count += 1
        if rejection_count >= 3:
            print(f"   ⚠️  Director rejected {rejection_count} times — manual intervention required.")

    return {
        "director_approved": is_green,
        "director_rejection_count": rejection_count,
        "progress_log": [f"🎬 Director Verdict: {'✅ GREEN LIGHT' if is_green else '⚠️ CORRECTION REQUESTED'}"]
    }
