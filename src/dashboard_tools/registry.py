"""Discovers the tools in this package.

Every module in src/dashboard_tools/ (except base, registry and modules that
start with an underscore) is imported, and each Tool subclass defined there is
registered under its `name`.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

from .base import Tool

_SKIPPED_MODULES = {"base", "registry"}
_cache: dict[str, Tool] | None = None


def _discover() -> dict[str, Tool]:
    package = __name__.rsplit(".", 1)[0]
    found: dict[str, Tool] = {}

    for info in pkgutil.iter_modules([str(Path(__file__).parent)]):
        if info.ispkg or info.name.startswith("_") or info.name in _SKIPPED_MODULES:
            continue
        module = importlib.import_module(f"{package}.{info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or not issubclass(cls, Tool) or inspect.isabstract(cls):
                continue
            if cls.name in found:
                raise RuntimeError(f"Duplicate tool name {cls.name!r} in {module.__name__}")
            found[cls.name] = cls()

    return dict(sorted(found.items()))


def list_tools(input_ref_type: str | None = None, refresh: bool = False) -> list[Tool]:
    """Return the tools, optionally filtered by the reference type they accept."""
    global _cache
    if _cache is None or refresh:
        _cache = _discover()
    tools = list(_cache.values())
    if input_ref_type is not None:
        tools = [t for t in tools if t.input_ref_type == input_ref_type]
    return tools


def get_tool(name: str) -> Tool | None:
    """Return the tool registered under `name`, or None."""
    list_tools()
    return _cache.get(name)
