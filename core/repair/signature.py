import re
from typing import Dict, Any

def build_failure_signature(platform: str, runner: str, raw_output: str) -> str:
    """
    Normalizes raw CLI/Test output into a stable signature string.
    Example: platform=nextjs|runner=jest|error=module-not-found|path=app/components/Foo.tsx
    """
    normalized = raw_output.lower()
    
    # 1. Categorize the Error
    if "module not found" in normalized or "cannot find module" in normalized:
        kind = "module-not-found"
    elif "typeerror" in normalized or "type error" in normalized:
        kind = "type-error"
    elif "cannot find name" in normalized or "is not defined" in normalized:
        kind = "symbol-not-found"
    elif "syntaxerror" in normalized or "syntax error" in normalized:
        kind = "syntax-error"
    elif "assertionerror" in normalized or "assert" in normalized:
        kind = "assertion-failure"
    elif "timeout" in normalized:
        kind = "timeout"
    else:
        kind = "unknown-runtime-error"

    # 2. Extract failing path/file if possible
    # Looks for patterns like /path/to/file.ext or ./file.ext
    path_match = re.search(r"([A-Za-z0-9_./-]+\.(ts|tsx|js|jsx|py|swift|kt|dart))", raw_output)
    path = path_match.group(1) if path_match else "n/a"
    
    # Ensure platform and runner are normalized
    platform = platform.lower().strip()
    runner = runner.lower().strip()

    return f"platform={platform}|runner={runner}|error={kind}|path={path}"
