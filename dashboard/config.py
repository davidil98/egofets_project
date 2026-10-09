"""Dashboard configuration backed by a YAML file.

Adapted from the `pageconf` concept of the nicegui_dashboard reference project,
rewritten to depend only on PyYAML and the standard library (no omegaconf, no
loguru) so it stays compatible with the project's Python 3.14 environment.

Location: dashboard/dashboard.yaml
"""

import copy
import logging
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from nicegui import ui

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "dashboard.yaml"

DEFAULT_SCOPE = "default"

CONFIG_DEFAULT: dict = {
    "theme": "light",
    "cards_per_row": 2,
    "card_height": 380,
    "card_fullscreen": True,
}

SECTION_DEFAULTS: dict = {
    "metadata": True,
    "description": True,
    "fields": True,
    "references": True,
    "analysis": True,
    "figures": True,
    "photos": True,
}

CARD_ORDER_DEFAULT: list = [
    "metadata",
    "description",
    "fields",
    "references",
    "analysis",
    "figures",
    "photos",
]


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` on top of `base`, returning a new dict."""
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


class DashboardConf:
    """Singleton manager for the dashboard YAML configuration."""

    _instance: Optional["DashboardConf"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._conf: dict = {}
        self.reload()

    # ===== persistence =====

    def reload(self) -> None:
        """(Re)read the YAML file from disk, creating it if missing."""
        if not CONFIG_PATH.exists():
            logger.warning("Config file missing, writing defaults: %s", CONFIG_PATH)
            self._conf = {
                DEFAULT_SCOPE: copy.deepcopy(CONFIG_DEFAULT),
                "memory_detail": {
                    "sections": copy.deepcopy(SECTION_DEFAULTS),
                    "card_order": list(CARD_ORDER_DEFAULT),
                },
            }
            self._write()
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            logger.error("Invalid YAML in %s: %s", CONFIG_PATH, exc)
            self.notify(f"Invalid YAML in dashboard.yaml: {exc}", "negative", 8000)
            loaded = None

        self._conf = loaded if isinstance(loaded, dict) else {}

    def _write(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self._conf, fh, default_flow_style=False, sort_keys=False)

    # ===== notification helper =====

    @staticmethod
    def notify(message: str, kind: str = "positive", timeout: int = 4000) -> None:
        ui.notify(message, type=kind, position="bottom-right", timeout=timeout)

    # ===== read =====

    def raw(self, scope: str) -> dict:
        """Return the stored (unmerged) mapping for a scope."""
        value = self._conf.get(scope)
        return value if isinstance(value, dict) else {}

    def load(self, scope: str) -> dict:
        """Return `default` deep-merged with the given scope."""
        base = copy.deepcopy(CONFIG_DEFAULT)
        base = _deep_merge(base, self.raw(DEFAULT_SCOPE))
        if scope and scope != DEFAULT_SCOPE:
            base = _deep_merge(base, self.raw(scope))
        return base

    def get(self, scope: str, key: str, default: Any = None) -> Any:
        """Read a single (possibly dotted) key, e.g. `figures.max_height`."""
        node: Any = self.load(scope)
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    # ===== write =====

    def set(self, scope: str, key: str, value: Any, persist: bool = True) -> None:
        """Set a single (possibly dotted) key inside a scope and persist."""
        self._conf.setdefault(scope, {})
        node = self._conf[scope]
        parts = key.split(".")
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
        if persist:
            self._write()

    def save_yaml(self, scope: str, yaml_str: str) -> None:
        """Replace a whole scope from a YAML string (used by the editor)."""
        if not yaml_str or not yaml_str.strip():
            self.delete(scope)
            return
        parsed = yaml.safe_load(yaml_str)
        if not isinstance(parsed, dict):
            raise ValueError("Configuration must be a YAML mapping")
        self._conf[scope] = parsed
        self._write()

    def delete(self, scope: str) -> None:
        if scope in self._conf:
            del self._conf[scope]
            self._write()
            logger.info("Deleted config scope %r", scope)

    def to_yaml(self, scope: str) -> str:
        return yaml.safe_dump(self.load(scope), default_flow_style=False, sort_keys=False)

    # ===== memory_detail section helpers =====

    def sections(self, scope: str = "memory_detail") -> dict:
        """Return the visibility mapping for every known section."""
        stored = self.get(scope, "sections", {}) or {}
        merged = copy.deepcopy(SECTION_DEFAULTS)
        merged.update({k: bool(v) for k, v in stored.items() if k in SECTION_DEFAULTS})
        return merged

    def card_order(self, scope: str = "memory_detail") -> list:
        stored = self.get(scope, "card_order", None)
        if not isinstance(stored, list) or not stored:
            return list(CARD_ORDER_DEFAULT)
        known = [k for k in stored if k in SECTION_DEFAULTS]
        known += [k for k in CARD_ORDER_DEFAULT if k not in known]
        return known

    def set_section_visible(
        self, key: str, visible: bool, scope: str = "memory_detail", persist: bool = True
    ) -> None:
        self.set(scope, f"sections.{key}", bool(visible), persist=persist)

    # ===== settings dialog =====

    def open_settings_dialog(
        self, scope: str = "memory_detail", on_save: Optional[Callable[[], None]] = None
    ) -> None:
        """Open a dialog to edit the YAML of a scope with a code editor."""
        scopes = [DEFAULT_SCOPE] + [s for s in self._conf if s != DEFAULT_SCOPE]
        if scope not in scopes:
            scopes.append(scope)

        with ui.dialog() as dialog, ui.card().classes("w-[860px]"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.label("Dashboard settings").classes("text-xl font-bold")
                ui.space()
                scope_select = ui.select(scopes, value=scope, label="Scope").props(
                    "outlined dense"
                ).classes("w-52")

            editor = ui.codemirror(
                value=self.to_yaml(scope),
                language="YAML",
                theme="basicLight",
            ).classes("w-full").style("height: 420px; border: 1px solid #cbd5e1; border-radius: 4px;")

            def load_scope():
                editor.value = self.to_yaml(scope_select.value)

            scope_select.on_value_change(lambda _: load_scope())

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Reload", icon="refresh", on_click=self.reload).props("flat")
                ui.button("Close", on_click=dialog.close).props("flat")

                def do_save():
                    try:
                        self.save_yaml(scope_select.value, editor.value)
                        self.notify("Configuration saved")
                        if on_save:
                            on_save()
                    except Exception as exc:  # noqa: BLE001 - surfaced to the user
                        logger.error("Error saving config: %s", exc)
                        self.notify(f"Error saving configuration: {exc}", "negative", 8000)

                ui.button("Save", icon="save", on_click=do_save).props("color=primary")

        dialog.open()


dashboard_conf = DashboardConf()
