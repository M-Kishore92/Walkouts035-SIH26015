"""
AST Purity Test: Watershed Impact Index Engine.

This test parses the WII engine's source code as an Abstract Syntax Tree
and asserts that no forbidden imports or calls exist. This is a mechanical
guarantee — code review alone is not sufficient.

Forbidden in app/services/wii/engine.py:
  - import datetime / from datetime import ...
  - import time / from time import ...
  - import random / from random import ...
  - import requests / import httpx / import aiohttp (any network library)
  - import os / import pathlib / import sys
  - open() built-in calls
  - Any SQLAlchemy or asyncpg import
  - Any global mutable state (module-level lists/dicts that are not constants)

Permitted:
  - from .types import ... (local domain types)
  - Pure stdlib math: math, typing, dataclasses, enum, __future__
"""
from __future__ import annotations

import ast
import pathlib
from typing import Iterator

import pytest

# ── Files to inspect ──────────────────────────────────────────────────────────
REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
WII_ENGINE = REPO_ROOT / "app" / "services" / "wii" / "engine.py"
WII_TYPES = REPO_ROOT / "app" / "services" / "wii" / "types.py"

# ── Forbidden patterns ────────────────────────────────────────────────────────
FORBIDDEN_IMPORTS: frozenset[str] = frozenset({
    "datetime", "time", "random", "os", "pathlib", "sys",
    "requests", "httpx", "aiohttp", "urllib", "socket",
    "sqlalchemy", "asyncpg", "psycopg2", "databases",
    "boto3", "aioboto3", "minio",
    "celery", "redis",
    "subprocess", "shutil", "tempfile",
    "threading", "multiprocessing", "concurrent",
})

FORBIDDEN_BUILTINS: frozenset[str] = frozenset({"open", "input", "print"})


def _parse_file(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _iter_imports(tree: ast.Module) -> Iterator[str]:
    """Yield all top-level module names imported."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module.split(".")[0]


def _iter_calls(tree: ast.Module) -> Iterator[str]:
    """Yield all bare function call names (no attribute calls)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                yield node.func.id


# ── Test: WII Engine ─────────────────────────────────────────────────────────

class TestWIIEnginePurity:
    def setup_method(self) -> None:
        assert WII_ENGINE.exists(), f"WII engine file missing: {WII_ENGINE}"
        self.tree = _parse_file(WII_ENGINE)

    def test_no_forbidden_imports(self) -> None:
        """WII engine must not import any IO, network, or database modules."""
        imported = set(_iter_imports(self.tree))
        violations = imported & FORBIDDEN_IMPORTS
        assert not violations, (
            f"WII engine has forbidden imports: {violations}\n"
            f"These imports violate the pure-function contract. "
            f"Move IO to the service layer."
        )

    def test_no_open_calls(self) -> None:
        """WII engine must not call open() or any IO builtins."""
        calls = set(_iter_calls(self.tree))
        violations = calls & FORBIDDEN_BUILTINS
        assert not violations, (
            f"WII engine calls forbidden builtins: {violations}"
        )

    def test_no_global_mutable_state(self) -> None:
        """WII engine must not define module-level mutable containers."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Constants are UPPER_CASE — skip them
                        if target.id.isupper():
                            continue
                        # A module-level assignment to a non-constant is suspicious
                        if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                            pytest.fail(
                                f"WII engine has module-level mutable state: "
                                f"'{target.id}' — use frozen constants or pass as args."
                            )

    def test_compute_wii_is_defined(self) -> None:
        """Sanity: the main engine function must exist."""
        functions = {
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert "compute_wii" in functions, "compute_wii function not found in engine.py"

    def test_rank_watersheds_is_defined(self) -> None:
        """Sanity: ranking function must exist."""
        functions = {
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert "rank_watersheds" in functions


# ── Test: WII Types ───────────────────────────────────────────────────────────

class TestWIITypesPurity:
    def setup_method(self) -> None:
        assert WII_TYPES.exists(), f"WII types file missing: {WII_TYPES}"
        self.tree = _parse_file(WII_TYPES)

    def test_no_forbidden_imports_in_types(self) -> None:
        imported = set(_iter_imports(self.tree))
        violations = imported & FORBIDDEN_IMPORTS
        assert not violations, f"WII types has forbidden imports: {violations}"

    def test_all_dataclasses_are_frozen(self) -> None:
        """All @dataclass in types.py must be frozen=True."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if (
                            isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "dataclass"
                        ):
                            # Check for frozen=True keyword
                            has_frozen = any(
                                (isinstance(kw.arg, str) and kw.arg == "frozen"
                                 and isinstance(kw.value, ast.Constant)
                                 and kw.value.value is True)
                                for kw in decorator.keywords
                            )
                            assert has_frozen, (
                                f"Dataclass '{node.name}' in types.py must be frozen=True "
                                f"(immutability is required for pure function contract)"
                            )
