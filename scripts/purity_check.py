"""
Standalone AST Purity Checker.
Runs AST purity inspection on both WII Engine and Cross-Validation Engine
without requiring pytest.
"""
from __future__ import annotations

import ast
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = pathlib.Path(__file__).parent.parent
WII_ENGINE = REPO_ROOT / "backend" / "app" / "services" / "wii" / "engine.py"
CROSSVAL_ENGINE = REPO_ROOT / "backend" / "app" / "services" / "crossval" / "engine.py"

FORBIDDEN_IMPORTS = frozenset({
    "datetime", "time", "random", "os", "pathlib", "sys",
    "requests", "httpx", "aiohttp", "urllib", "socket",
    "sqlalchemy", "asyncpg", "psycopg2", "databases",
    "boto3", "aioboto3", "minio",
    "celery", "redis",
    "subprocess", "shutil", "tempfile",
    "threading", "multiprocessing", "concurrent",
})

FORBIDDEN_BUILTINS = frozenset({"open", "input", "print"})


def check_file(path: pathlib.Path) -> bool:
    print(f"\nChecking AST purity for: {path.name} ...")
    tree = ast.parse(path.read_text(encoding="utf-8"))

    # Check imports
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split(".")[0])

    violations = imported_modules & FORBIDDEN_IMPORTS
    if violations:
        print(f"  ❌ Forbidden imports detected: {violations}")
        return False

    # Check built-in calls
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    builtin_violations = calls & FORBIDDEN_BUILTINS
    if builtin_violations:
        print(f"  ❌ Forbidden built-in calls detected: {builtin_violations}")
        return False

    print(f"  ✅ PURE: Zero forbidden imports and zero forbidden built-ins.")
    return True


def main() -> int:
    print("=" * 60)
    print("AST Engine Purity Verification")
    print("=" * 60)

    ok1 = check_file(WII_ENGINE)
    ok2 = check_file(CROSSVAL_ENGINE)

    if ok1 and ok2:
        print("\nAll engine modules passed mechanical purity inspection!")
        return 0
    else:
        print("\nPurity inspection failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
