"""Memory detail page with a configuration drawer and section cards."""

from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from dashboard.config import SECTION_DEFAULTS, dashboard_conf
from dashboard.ui.cards import SECTION_META, CardContainer, build_section_cards
from src import db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCOPE = "memory_detail"


def render_memory_detail(memory_id: int, on_back: Callable[[], None]) -> None:
    """Render the memory detail view, opening in read-only mode."""
    state = {"editing": False, "visible": dashboard_conf.sections(SCOPE)}
    checkboxes: dict[str, ui.checkbox] = {}

    def set_visible(key: str, value: bool) -> bool:
        if state["visible"].get(key) == value:
            return False
        state["visible"][key] = value
        dashboard_conf.set_section_visible(key, value, SCOPE)
        return True

    def on_section_toggled(key: str, value: bool) -> None:
        if set_visible(key, value):
            render_content.refresh()

    def hide_section(key: str) -> None:
        set_visible(key, False)
        if key in checkboxes:
            checkboxes[key].value = False
        render_content.refresh()

    def toggle_mode() -> None:
        state["editing"] = not state["editing"]
        mode_button.set_text("Done" if state["editing"] else "Edit")
        mode_button.set_icon("check" if state["editing"] else "edit")
        render_content.refresh()

    def reset_sections() -> None:
        for key, value in SECTION_DEFAULTS.items():
            state["visible"][key] = value
            dashboard_conf.set_section_visible(key, value, SCOPE)
            if key in checkboxes:
                checkboxes[key].value = value
        render_content.refresh()

    drawer = ui.left_drawer(value=True, bordered=True).props("width=300")
    with drawer:
        with ui.column().classes("w-full gap-3 p-4"):
            ui.button("Back", icon="arrow_back", on_click=on_back).props("flat align=left").classes("w-full")
            mode_button = ui.button("Edit", icon="edit", on_click=toggle_mode).props("color=primary").classes("w-full")
            ui.button("Export", icon="download", on_click=lambda: _show_export_dialog(memory_id)).props(
                "color=secondary"
            ).classes("w-full")
            ui.separator()
            ui.label("Sections").classes("text-sm font-bold text-gray-600")
            for key in dashboard_conf.card_order(SCOPE):
                checkboxes[key] = ui.checkbox(
                    SECTION_META[key][0], value=state["visible"][key]
                ).on_value_change(lambda e, k=key: on_section_toggled(k, e.value))
            ui.button("Reset sections", icon="restart_alt", on_click=reset_sections).props("flat").classes("w-full")

    ui.keyboard(on_key=lambda e: drawer.toggle() if (
        e.modifiers.ctrl and e.key == "q" and e.action.keydown and not e.action.repeat
    ) else None)

    @ui.refreshable
    def render_content() -> None:
        mem = db.get_memory(memory_id)
        if not mem:
            ui.label("Memory not found").classes("text-red-500 text-xl")
            ui.button("Back", icon="arrow_back", on_click=on_back)
            return

        conf = dashboard_conf.load(SCOPE)
        _render_header(mem, state["editing"])
        container = CardContainer(columns=conf["cards_per_row"])
        build_section_cards(
            container=container,
            memory=mem,
            project_root=PROJECT_ROOT,
            editing=state["editing"],
            conf=conf,
            visible=state["visible"],
            order=dashboard_conf.card_order(SCOPE),
            on_close=hide_section,
            on_changed=render_content.refresh,
        )

    with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        render_content()


def _render_header(memory: dict, editing: bool) -> None:
    """Render the title, type badges, date and mode indicator."""
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.label(memory.get("title", "")).classes("text-2xl font-bold")
            ui.badge(memory.get("type") or "-").props("color=blue outline")
            if memory.get("subtype"):
                ui.badge(memory["subtype"]).props("color=gray outline")
            ui.label(memory.get("date") or "").classes("text-sm text-gray-500")
            ui.space()
            if editing:
                ui.badge("Editing").props("color=orange")


def _show_export_dialog(memory_id: int):
    """Show export dialog with options."""
    with ui.dialog() as dlg, ui.card().classes("w-96"):
        ui.label("Export Memory").classes("text-xl font-bold mb-4")
        
        format_select = ui.select(
            ["HTML", "PDF"],
            value="HTML",
            label="Format",
        ).props("outlined dense").classes("w-full")
        
        include_figures = ui.checkbox("Include figures", value=True)
        include_photos = ui.checkbox("Include photos", value=True)
        
        status_label = ui.label("").classes("text-sm text-gray-500 mt-2")
        
        with ui.row().classes("w-full justify-end mt-4 gap-2"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            
            async def do_export():
                status_label.text = "Exporting..."
                try:
                    if format_select.value == "HTML":
                        from src.dashboard_tools.exporters.html import export_memory_html
                        path = export_memory_html(
                            memory_id=memory_id,
                            include_figures=include_figures.value,
                            include_photos=include_photos.value,
                        )
                    else:
                        from src.dashboard_tools.exporters.pdf import export_memory_pdf
                        path = export_memory_pdf(
                            memory_id=memory_id,
                            include_figures=include_figures.value,
                            include_photos=include_photos.value,
                        )
                    
                    if path:
                        status_label.text = f"✓ Exported to: {path.name}"
                        status_label.classes("text-green-600")
                        ui.notify(f"Exported to {path.name}", color="positive")
                        ui.timer(2.0, dlg.close, once=True)
                    else:
                        status_label.text = "✗ Export failed"
                        status_label.classes("text-red-600")
                except Exception as e:
                    status_label.text = f"✗ Error: {e}"
                    status_label.classes("text-red-600")
            
            ui.button("Export", icon="check", on_click=do_export).props("color=primary")
    
    dlg.open()
