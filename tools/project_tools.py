import subprocess
from pathlib import Path


def install_xcodegen():
    """One-time setup — installs xcodegen via Homebrew if not present."""
    result = subprocess.run(["which", "xcodegen"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   xcodegen already installed at {result.stdout.strip()}")
        return True
    print("   Installing xcodegen via Homebrew...")
    r = subprocess.run(["brew", "install", "xcodegen"], capture_output=True, text=True)
    if r.returncode == 0:
        print("   ✅ xcodegen installed")
        return True
    print(f"   ⚠️ xcodegen install failed: {r.stderr[:200]}")
    return False


def write_project_yml(repo_path: str, app_name: str, bundle_id: str = None) -> str:
    """Write a minimal but correct project.yml for xcodegen."""
    safe_name = "".join(c for c in app_name if c.isalnum())
    bundle = bundle_id or f"com.gemforge.{safe_name.lower()}"
    content = f"""name: {safe_name}
options:
  bundleIdPrefix: com.gemforge
  deploymentTarget:
    iOS: "17.0"
targets:
  {safe_name}:
    type: application
    platform: iOS
    sources:
      - Sources
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: {bundle}
        SWIFT_VERSION: "5.9"
        TARGETED_DEVICE_FAMILY: "1,2"
"""
    path = f"{repo_path}/project.yml"
    Path(path).write_text(content, encoding="utf-8")
    print(f"   → project.yml written")
    return path


def generate_xcode_project(repo_path: str, app_name: str = "App") -> bool:
    """
    Creates a full Xcode project from project.yml via xcodegen.
    Returns True on success.
    """
    project_yml = Path(repo_path) / "project.yml"
    if not project_yml.exists():
        write_project_yml(repo_path, app_name)

    # Ensure Sources/ dir exists so xcodegen doesn't fail
    sources = Path(repo_path) / "Sources"
    sources.mkdir(exist_ok=True)

    # Create a placeholder Swift file if Sources/ is empty
    swift_files = list(sources.glob("*.swift"))
    if not swift_files:
        safe_name = "".join(c for c in app_name if c.isalnum())
        (sources / f"{safe_name}App.swift").write_text(
            f'import SwiftUI\n\n@main\nstruct {safe_name}App: App {{\n'
            f'    var body: some Scene {{\n        WindowGroup {{ ContentView() }}\n    }}\n}}\n',
            encoding="utf-8",
        )
        (sources / "ContentView.swift").write_text(
            'import SwiftUI\n\nstruct ContentView: View {\n'
            '    var body: some View {\n        Text("Built with GemForge")\n    }\n}\n',
            encoding="utf-8",
        )

    result = subprocess.run(
        ["xcodegen", "generate"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"   ✅ Xcode project generated at {repo_path}")
        return True

    print(f"   ⚠️ xcodegen failed: {result.stderr[:300]}")
    return False
