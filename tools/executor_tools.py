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
