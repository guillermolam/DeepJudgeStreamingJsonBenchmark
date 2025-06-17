"""Utility helpers for serializer test execution."""

from __future__ import annotations

import inspect
from types import ModuleType
from typing import Callable, Iterable, List, Optional


def _collect_tests(module: ModuleType) -> List[Callable[[], None]]:
    """Return zero-argument callables whose names start with ``test_``."""
    tests: List[Callable[[], None]] = []
    for name, obj in inspect.getmembers(module):
        if name.startswith("test_") and callable(obj):
            try:
                if not inspect.signature(obj).parameters:
                    tests.append(obj)
            except (TypeError, ValueError):
                # Builtins or callables without a signature
                continue
    return tests


def run_module_tests(module: ModuleType, tests: Optional[Iterable[Callable[[], None]]] = None) -> bool:
    """Execute test callables and raise ``RuntimeError`` on failure."""
    selected_tests = list(tests) if tests is not None else _collect_tests(module)
    failures: List[str] = []
    for test in selected_tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{test.__name__}: {exc}")
    if failures:
        summary = "\n".join(failures)
        raise RuntimeError(f"Failing tests:\n{summary}")
    return True
