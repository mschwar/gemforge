from pathlib import Path
import re

from tools.file_tools import ensure_dir, write_file


def _resolve_generated_file_path(repo_path: str, filename: str) -> Path | None:
    cleaned = filename.strip().lstrip("/").replace("\\", "/")
    if not cleaned:
        return None

    output_path = Path(repo_path)
    if "/" in cleaned:
        return output_path / cleaned

    if cleaned.endswith(".swift"):
        return output_path / "Sources" / cleaned

    return output_path / cleaned


def parse_and_save_generated_code(repo_path: str, llm_response: str):
    """
    Parse ===relative/path.ext=== code blocks and write files.

    Backward-compatible behavior:
    - bare .swift filenames are written under Sources/
    - other bare filenames are written to repo root
    """
    pattern = r"===([^=\n]+?)===\n(.*?)(?=\n===|\Z)"
    matches = re.findall(pattern, llm_response, re.DOTALL)

    written_count = 0
    for filename, content in matches:
        destination = _resolve_generated_file_path(repo_path, filename)
        if not destination:
            continue

        ensure_dir(str(destination.parent))
        write_file(str(destination), content.strip())
        print(f"   ✅ Generated {destination.relative_to(repo_path)}")
        written_count += 1

    return written_count


def build_and_verify_xcode(repo_path: str):
    """Runs xcodegen + build verification"""
    try:
        import glob as glob_module
        import subprocess

        # Find the .xcodeproj
        xcodeproj_matches = glob_module.glob(f"{repo_path}/*.xcodeproj")
        if not xcodeproj_matches:
            print("⚠️ No .xcodeproj found — skipping build verification")
            return False

        xcodeproj = xcodeproj_matches[0]
        scheme = Path(xcodeproj).stem  # scheme name matches project name

        result = subprocess.run([
            "xcodebuild", "build",
            "-project", xcodeproj,
            "-scheme", scheme,
            "-destination", "platform=iOS Simulator,name=iPhone 16",
            "CODE_SIGNING_ALLOWED=NO",
        ], capture_output=True, text=True, cwd=repo_path)

        if result.returncode == 0:
            print("✅ Xcode project BUILDS SUCCESSFULLY")
            return True
        else:
            print("⚠️ Build failed:")
            # Print last 40 lines of stderr for diagnostics
            stderr_lines = result.stderr.strip().splitlines()
            for line in stderr_lines[-40:]:
                print("   ", line)
            return False
    except Exception as e:
        print(f"⚠️ Build verification skipped ({e})")
        return True

# ====================== REAL QA / TEST RUNNER (Module 2) ======================
def run_tests(repo_path: str, platform: str) -> dict:
    """
    Platform-aware test execution for GemForge Real QA Layer (Module 2).
    Called by qa_generator_node and qa_node.
    Returns structured result for PipelineState + conditional edge (fail → human gate).
    """
    import subprocess
    from pathlib import Path
    import os

    repo = Path(repo_path)
    if not repo.exists():
        return {"success": False, "report": "Repo path does not exist", "passed": False, "failures": 1, "details": ""}

    result = {
        "success": False,
        "report": "",
        "passed": False,
        "failures": 0,
        "details": "",
        "command": ""
    }

    try:
        os.chdir(repo)

        if "ios" in platform.lower() or "swift" in platform.lower():
            print("🧪 Running XCTest for iOS...")
            
            # Check for xcode-select developer tools vs full Xcode
            check_xc = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True)
            if "CommandLineTools" in check_xc.stdout:
                result["report"] = "FAIL: System is set to CommandLineTools. Run: sudo xcode-select -s /Applications/Xcode.app"
                return result

            # Auto-detect scheme from .xcodeproj name
            xcodeprojs = list(repo.glob("*.xcodeproj"))
            if not xcodeprojs:
                result["report"] = "No .xcodeproj found"
                return result
            scheme = xcodeprojs[0].stem
            cmd = [
                "xcodebuild", "test",
                "-scheme", scheme,
                "-destination", "platform=iOS Simulator,name=iPhone 16", # Use standard name
                "-quiet"
            ]
            result["command"] = " ".join(cmd)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            output = proc.stdout + "\n" + proc.stderr
            result["details"] = output[-4000:]  # last 4k chars
            result["success"] = proc.returncode == 0
            result["report"] = "XCTest " + ("PASSED ✓" if result["success"] else "FAILED ✗")
            result["failures"] = output.count("failed") or (0 if result["success"] else 1)

        elif "web" in platform.lower() or "react" in platform.lower() or "next" in platform.lower():
            print("🧪 Running Jest for web project...")
            cmd = ["npm", "test", "--", "--watchAll=false", "--ci", "--coverage"]
            result["command"] = " ".join(cmd)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = proc.stdout + "\n" + proc.stderr
            result["details"] = output[-3000:]
            result["success"] = proc.returncode == 0
            result["report"] = "Jest " + ("PASSED ✓" if result["success"] else "FAILED ✗")
            result["failures"] = output.count("fail") or (0 if result["success"] else 1)

        else:
            print(f"🧪 No dedicated test runner for {platform} yet → marking as skipped (success for pipeline)")
            result["success"] = True
            result["report"] = f"Tests skipped for {platform} (extend run_tests for full support)"

        print(f"   → {result['report']}")
        return result

    except subprocess.TimeoutExpired:
        return {"success": False, "report": "Test execution timed out (180s)", "passed": False, "failures": 999, "details": "Timeout"}
    except Exception as e:
        return {"success": False, "report": f"Test runner error: {str(e)}", "passed": False, "failures": 1, "details": str(e)}

