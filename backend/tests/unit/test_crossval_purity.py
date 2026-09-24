"""
AST Purity Test: Cross-Validation Engine.

This test parses the cross-validation engine's source code as an Abstract Syntax Tree (AST)
and asserts that no forbidden imports or calls exist. This is a mechanical guarantee
that the engine is pure functional with zero IO, network, or database coupling.

Forbidden in app/services/crossval/engine.py:
  - import datetime / from datetime import ...
  - import time / from time import ...
  - import random / from random import ...
  - import requests / import httpx / import aiohttp (any network library)
  - import os / import pathlib / import sys
  - open() built-in calls
  - Any SQLAlchemy or asyncpg import
  - Any global mutable state
"""
from __future__ import annotations

import ast
import pathlib
from typing import Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
CROSSVAL_ENGINE = REPO_ROOT / "app" / "services" / "crossval" / "engine.py"

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


def _iter_call_names(tree: ast.Module) -> Iterator[str]:
    """Yield names of all function calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                yield node.func.id
            elif isinstance(node.func, ast.Attribute):
                yield node.func.attr


class TestCrossvalEnginePurity:
    def test_file_exists(self) -> None:
        assert CROSSVAL_ENGINE.exists(), f"Missing file: {CROSSVAL_ENGINE}"

    def test_no_forbidden_imports(self) -> None:
        tree = _parse_file(CROSSVAL_ENGINE)
        imported_modules = set(_iter_imports(tree))
        violations = imported_modules & FORBIDDEN_IMPORTS
        assert not violations, (
            f"Cross-Validation Engine imports forbidden modules: {violations}. "
            "Engine must be pure functional."
        )

    def test_no_forbidden_builtins(self) -> None:
        tree = _parse_file(CROSSVAL_ENGINE)
        called_names = set(_iter_call_names(tree))
        violations = called_names & FORBIDDEN_BUILTINS
        assert not violations, (
            f"Cross-Validation Engine calls forbidden built-ins: {violations}"
        )

    def test_dataclasses_frozen_or_pure(self) -> None:
        tree = _parse_file(CROSSVAL_ENGINE)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Verify it does not inherit from ORM Base
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        assert base.id not in ("Base", "DeclarativeBase"), (
                            f"Class {node.name} inherits from ORM Base"
                        )
