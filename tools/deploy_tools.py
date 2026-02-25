import subprocess
import os
from pathlib import Path


def deploy_to_vercel(repo_path: str) -> str | None:
    """
    Attempt a real Vercel deployment from repo_path.
    Returns the live URL on success, None on failure.
    Requires: npm install -g vercel && vercel login (one-time setup).
    """
    abs_path = str(Path(repo_path).resolve())

    # Create minimal vercel.json if missing
    vercel_config = Path(abs_path) / "vercel.json"
    if not vercel_config.exists():
        vercel_config.write_text(
            '{"buildCommand": "echo no build needed", "outputDirectory": "."}'
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
        # Some vercel versions print URL on stderr
        for line in result.stderr.splitlines():
            line = line.strip()
            if line.startswith("https://") and ".vercel.app" in line:
                return line

    print(f"⚠️  Vercel deploy failed (exit {result.returncode})")
    if result.stderr:
        print(result.stderr[:400])
    return None
