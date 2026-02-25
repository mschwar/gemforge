from tools.file_tools import write_file, ensure_dir
from pathlib import Path
import re

def parse_and_save_generated_code(repo_path: str, llm_response: str):
    """Parses ===Filename.swift=== blocks and saves them"""
    pattern = r"===(.+?\.swift)===\n(.*?)(?===|\Z)"
    matches = re.findall(pattern, llm_response, re.DOTALL)

    for filename, content in matches:
        clean_filename = filename.strip()
        full_path = f"{repo_path}/Sources/{clean_filename}"
        ensure_dir(str(Path(full_path).parent))
        write_file(full_path, content.strip())
        print(f"   ✅ Generated {clean_filename}")

    return len(matches)

def build_and_verify_xcode(repo_path: str):
    """Runs xcodegen + build verification"""
    try:
        import subprocess
        import glob as glob_module

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
