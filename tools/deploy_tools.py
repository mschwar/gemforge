import json
import subprocess
from datetime import datetime
from pathlib import Path

# Project types that cannot be hosted on Vercel
NATIVE_KEYWORDS = [
    "ios",
    "swift",
    "swiftui",
    "iphone",
    "ipad",
    "android",
    "kotlin",
    "flutter",
    "react-native",
    "react native",
]


def is_native_mobile(idea: str) -> bool:
    lower = idea.lower()
    return any(kw in lower for kw in NATIVE_KEYWORDS)


def create_minimal_landing_page(repo_path: str, gem_name: str):
    """Creates a static landing page so Vercel always has something valid to serve."""
    index_path = Path(repo_path) / "index.html"
    if index_path.exists():
        return

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{gem_name} — Built with GemForge</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a; color: #f0f0f0;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; text-align: center; padding: 40px 20px;
        }}
        .card {{ max-width: 600px; }}
        h1 {{ font-size: 2.8rem; font-weight: 700; margin-bottom: 16px; }}
        p {{ font-size: 1.15rem; opacity: 0.7; line-height: 1.6; margin-bottom: 12px; }}
        .badge {{
            display: inline-block; margin-top: 32px;
            font-size: 0.85rem; opacity: 0.5; letter-spacing: 0.05em;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 {gem_name}</h1>
        <p>Built with GemForge on {datetime.now().strftime('%B %d, %Y')}.</p>
        <p>This is a placeholder landing page.<br>
           Full app code will appear here once the specialist agents complete their work.</p>
        <span class="badge">GEMFORGE · AI PRODUCT FACTORY</span>
    </div>
</body>
</html>"""

    index_path.write_text(content, encoding="utf-8")
    print("   → index.html landing page created")


def _is_framework_web_project(repo_path: str) -> bool:
    """Detect framework projects so we don't overwrite their deploy config."""
    root = Path(repo_path)
    package_json = root / "package.json"

    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}

        deps = {}
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))
        if any(name in deps for name in ("next", "react-scripts", "vite", "@sveltejs/kit", "nuxt")):
            return True

    return any(
        (root / marker).exists()
        for marker in (
            "next.config.mjs",
            "next.config.js",
            "vite.config.ts",
            "vite.config.js",
            "nuxt.config.ts",
            "nuxt.config.js",
        )
    )


def deploy_to_vercel(repo_path: str, idea: str = "") -> str | None:
    """
    Deploy to Vercel. Returns the live URL on success, None otherwise.
    Skips automatically for native iOS/Android projects.
    """
    if idea and is_native_mobile(idea):
        print("🛠️  Native mobile project detected — skipping Vercel (cannot host native apps)")
        print(f"   Project ready for Xcode / Android Studio at: {repo_path}")
        return None

    abs_path = str(Path(repo_path).resolve())
    print("🚀 Deploying to Vercel...")

    if _is_framework_web_project(abs_path):
        print("   → Framework project detected; preserving existing framework deploy behavior.")
    else:
        # Only use the static fallback for non-framework repos.
        create_minimal_landing_page(abs_path, idea or Path(abs_path).name)

        # Write a static vercel.json only if the project does not already define one.
        vercel_config = Path(abs_path) / "vercel.json"
        if not vercel_config.exists():
            vercel_config.write_text(
                '{"version": 2, "builds": [{"src": "index.html", "use": "@vercel/static"}], '
                '"routes": [{"src": "/(.*)", "dest": "/index.html"}]}',
                encoding="utf-8",
            )

    result = subprocess.run(
        ["npx", "vercel", "--prod", "--yes"],
        cwd=abs_path,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode == 0:
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("https://") and ".vercel.app" in line:
                return line
        for line in result.stderr.splitlines():
            line = line.strip()
            if line.startswith("https://") and ".vercel.app" in line:
                return line

    print(f"⚠️  Vercel deploy failed (exit {result.returncode})")
    if result.stderr:
        print(result.stderr[:400])
    return None
