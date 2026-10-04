"""EGOFET Memory Dashboard — main entry point.

Run with: python dashboard/app.py
Or: python -m dashboard.app
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from nicegui import ui, app
from src import db
from dashboard.templates.memory import sync_templates, list_templates


def _init():
    db.init_db()
    sync_templates()


class AppState:
    current_view: str = "home"
    selected_memory_id: int | None = None
    selected_memory_ids: list[int] = []


state = AppState()


@ui.page("/")
def main_page():
    _init()
    _build_layout()


def _build_layout():
    ui.colors(primary="#1a56db", secondary="#059669")

    with ui.header().classes("bg-[#1a56db] text-white items-center"):
        with ui.row().classes("items-center gap-4 w-full max-w-7xl mx-auto"):
            ui.label("EGOFET Memory").classes("text-xl font-bold")
            ui.space()
            with ui.row().classes("gap-1"):
                ui.button("Home", icon="home", on_click=_go_home).props("flat color=white size=sm")
                ui.button("Compare", icon="compare_arrows", on_click=_go_compare).props("flat color=white size=sm")
                ui.button("Settings", icon="settings", on_click=_go_settings).props("flat color=white size=sm")

    with ui.column().classes("w-full max-w-7xl mx-auto p-4"):
        if state.current_view == "home":
            _render_home()
        elif state.current_view == "memory_detail":
            _render_memory_detail()
        elif state.current_view == "compare":
            _render_compare()
        elif state.current_view == "settings":
            _render_settings()


def _go_home():
    state.current_view = "home"
    state.selected_memory_id = None
    state.selected_memory_ids = []
    ui.navigate.to("/")


def _go_memory(memory_id: int):
    state.current_view = "memory_detail"
    state.selected_memory_id = memory_id
    ui.navigate.to("/")


def _go_compare():
    state.current_view = "compare"
    ui.navigate.to("/")


def _go_settings():
    state.current_view = "settings"
    ui.navigate.to("/")


def _render_home():
    from dashboard.ui.home import render_home
    render_home(
        on_open_memory=_go_memory,
        on_create_memory=_show_create_dialog,
    )


def _render_memory_detail():
    from dashboard.ui.memory_detail import render_memory_detail
    render_memory_detail(
        memory_id=state.selected_memory_id,
        on_back=_go_home,
    )


def _render_compare():
    from dashboard.ui.compare import render_compare
    render_compare(on_back=_go_home)


def _render_settings():
    from dashboard.ui.settings import render_settings
    render_settings(on_back=_go_home)


def _show_create_dialog():
    from dashboard.ui.memory_create import show_create_dialog
    show_create_dialog(on_created=_go_memory)


_native_available = False
try:
    import webview
    _native_available = True
except ImportError:
    pass

ui.run(
    title="EGOFET Memory Dashboard",
    port=8080,
    native=_native_available,
    reload=True,
    window_size=(1280, 800) if _native_available else None,
    fullscreen=False,
)
