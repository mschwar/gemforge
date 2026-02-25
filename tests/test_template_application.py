import tempfile
import unittest
from pathlib import Path

from tools.project_tools import apply_template, parse_platform_manifest


class TemplateApplicationTests(unittest.TestCase):
    def _create_repo(self, name: str) -> Path:
        base_dir = Path(tempfile.mkdtemp(prefix=f"gemforge-{name}-"))
        (base_dir / "README.md").write_text("# Temp Repo\n", encoding="utf-8")
        return base_dir

    def _apply_from_manifest(self, platform: str, template: str) -> tuple[dict, Path]:
        manifest = f"""# PLATFORM_MANIFEST.md

## Selected Platform
{platform}

## Project Template
{template}

## Generator Flags
ui_generator: template
logic_generator: template
platform_generator: template
structure_generator: template
orchestration_mode: template-only
"""
        parsed = parse_platform_manifest(manifest)
        repo = self._create_repo(template)
        result = apply_template(str(repo), parsed["template"])
        self.assertTrue(
            result["validation"]["valid"],
            f"Missing files for {template}: {result['validation']['missing_files']}",
        )
        return result, repo

    def test_ios_swiftui_template(self):
        result, repo = self._apply_from_manifest("ios-swiftui", "ios-swiftui")
        self.assertTrue((repo / "project.yml").exists())
        self.assertTrue((repo / "Sources" / "ContentView.swift").exists())
        self.assertIn("APP_NAME_SAFE", result["context"])

    def test_nextjs_template(self):
        _, repo = self._apply_from_manifest("nextjs", "nextjs")
        self.assertTrue((repo / "package.json").exists())
        self.assertTrue((repo / "app" / "page.tsx").exists())
        self.assertTrue((repo / "app" / "components" / "CoreFeatureCounter.tsx").exists())

    def test_flutter_template(self):
        _, repo = self._apply_from_manifest("flutter", "flutter")
        self.assertTrue((repo / "pubspec.yaml").exists())
        self.assertTrue((repo / "lib" / "main.dart").exists())


if __name__ == "__main__":
    unittest.main()
