import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"^##\s*{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_first_value(section: str) -> str:
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        return line
    return ""


def _read_template_metadata(template_dir: Path) -> dict:
    metadata_path = template_dir / "GemForgeTemplate.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Template metadata missing: {metadata_path}")

    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {metadata_path}: {exc}") from exc


def _template_aliases(template_dir: Path, metadata: dict) -> set[str]:
    aliases = {
        _normalize_identifier(template_dir.name),
        _normalize_identifier(metadata.get("platform", "")),
        _normalize_identifier(metadata.get("template_name", "")),
        _normalize_identifier(metadata.get("name", "")),
    }

    for alias in metadata.get("aliases", []):
        aliases.add(_normalize_identifier(str(alias)))

    return {alias for alias in aliases if alias}


def list_templates() -> list[dict]:
    if not TEMPLATES_ROOT.exists():
        return []

    templates = []
    for child in sorted(TEMPLATES_ROOT.iterdir()):
        if not child.is_dir():
            continue
        metadata_path = child / "GemForgeTemplate.json"
        if not metadata_path.exists():
            continue
        metadata = _read_template_metadata(child)
        templates.append(
            {
                "name": metadata.get("template_name", child.name),
                "platform": metadata.get("platform", child.name),
                "path": str(child),
                "metadata": metadata,
                "aliases": sorted(_template_aliases(child, metadata)),
            }
        )

    return templates


def load_template(platform: str) -> dict:
    """
    Load template metadata by platform/template alias.

    Args:
        platform: Selected platform or template name from PLATFORM_MANIFEST.md.

    Returns:
        Dict with name/platform/path/metadata/aliases.
    """
    normalized_query = _normalize_identifier(platform)
    templates = list_templates()

    if not templates:
        raise FileNotFoundError(f"No templates found in {TEMPLATES_ROOT}")

    for template in templates:
        if normalized_query in set(template.get("aliases", [])):
            return template

    valid_values = sorted(
        {
            alias
            for template in templates
            for alias in template.get("aliases", [])
        }
    )
    raise ValueError(
        f"Unknown template/platform '{platform}'. Available: {', '.join(valid_values)}"
    )


def parse_platform_manifest(manifest_content: str) -> dict:
    """Parse PLATFORM_MANIFEST.md into stable keys used by orchestrator routing."""
    selected_platform = _extract_first_value(_extract_section(manifest_content, "Selected Platform"))
    template_name = _extract_first_value(_extract_section(manifest_content, "Project Template"))

    # Fallback: parse key/value style lines anywhere in the manifest.
    kv_pairs: dict[str, str] = {}
    for raw_line in manifest_content.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = _normalize_identifier(key)
        kv_pairs[normalized_key] = value.strip()

    if not selected_platform:
        selected_platform = kv_pairs.get("platform") or kv_pairs.get("selected-platform", "")

    if not template_name:
        template_name = (
            kv_pairs.get("template")
            or kv_pairs.get("project-template")
            or kv_pairs.get("template-name", "")
        )

    generator_flags_section = _extract_section(manifest_content, "Generator Flags")
    generator_flags = {}
    for raw_line in generator_flags_section.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        generator_flags[_normalize_identifier(key)] = value.strip()

    if not template_name and selected_platform:
        template_name = selected_platform

    return {
        "selected_platform": selected_platform.strip(),
        "template": template_name.strip(),
        "generator_flags": generator_flags,
    }


def _derive_template_context(repo_path: str) -> dict:
    repo_name = Path(repo_path).name
    tokens = [part for part in re.split(r"[^A-Za-z0-9]+", repo_name) if part]

    app_name = " ".join(token.capitalize() for token in tokens) or "GemForge App"
    app_name_safe = "".join(token.capitalize() for token in tokens) or "GemForgeApp"
    if app_name_safe[0].isdigit():
        app_name_safe = f"Gem{app_name_safe}"

    app_name_kebab = "-".join(token.lower() for token in tokens) or "gemforge-app"
    app_name_snake = "_".join(token.lower() for token in tokens) or "gemforge_app"

    bundle_suffix = re.sub(r"[^a-z0-9.]", "", app_name_snake.replace("_", "."))
    bundle_id = f"com.gemforge.{bundle_suffix}".strip(".")

    android_suffix = re.sub(r"[^a-z0-9_]", "", app_name_snake)
    android_package = f"com.gemforge.{android_suffix}".strip(".")

    return {
        "APP_NAME": app_name,
        "APP_NAME_SAFE": app_name_safe,
        "APP_NAME_KEBAB": app_name_kebab,
        "APP_NAME_SNAKE": app_name_snake,
        "BUNDLE_ID": bundle_id,
        "ANDROID_PACKAGE": android_package,
        "YEAR": str(datetime.now().year),
    }


def _replace_tokens(content: str, context: dict) -> str:
    replaced = content
    for key, value in context.items():
        replaced = replaced.replace(f"__{key}__", value)
    return replaced


def _copy_template_files(template_dir: Path, destination_dir: Path, context: dict):
    for source_path in sorted(template_dir.rglob("*")):
        if source_path.is_dir():
            continue

        relative_path = source_path.relative_to(template_dir)
        if relative_path.name == "GemForgeTemplate.json":
            continue

        resolved_parts = [_replace_tokens(part, context) for part in relative_path.parts]
        destination_path = destination_dir.joinpath(*resolved_parts)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        raw_bytes = source_path.read_bytes()
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            shutil.copy2(source_path, destination_path)
            continue

        destination_path.write_text(_replace_tokens(content, context), encoding="utf-8")


def validate_applied_template(repo_path: str, template_metadata: dict) -> dict:
    required_files = template_metadata.get("required_files", [])
    missing_files = []

    for relative_path in required_files:
        if not (Path(repo_path) / relative_path).exists():
            missing_files.append(relative_path)

    return {
        "valid": not missing_files,
        "missing_files": missing_files,
    }


def apply_template(repo_path: str, template_name: str) -> dict:
    """
    Apply a template onto an existing repository path.

    New templates can be added by dropping a new folder into templates/
    with a GemForgeTemplate.json + starter files.
    """
    template = load_template(template_name)
    template_dir = Path(template["path"])

    context = _derive_template_context(repo_path)
    _copy_template_files(template_dir, Path(repo_path), context)

    validation = validate_applied_template(repo_path, template["metadata"])

    print(
        f"   → Applied template '{template['name']}' "
        f"({template.get('platform', template_name)})"
    )
    if validation["missing_files"]:
        print(f"   ⚠️ Missing required template files: {validation['missing_files']}")

    return {
        "name": template["name"],
        "platform": template.get("platform", template_name),
        "path": template["path"],
        "metadata": template["metadata"],
        "context": context,
        "validation": validation,
    }


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
    print("   → project.yml written")
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
