"""Memory detail page with a configuration drawer and section cards."""

from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from dashboard.config import SECTION_DEFAULTS, dashboard_conf
from dashboard.ui.cards import (
    RUN_DEPENDENT_KEYS,
    SECTION_CARDS,
    SECTION_META,
    CardContainer,
    build_section_card,
)
from src import db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCOPE = "memory_detail"

#: Change event emitted by a card -> the cards (and the header) it invalidates.
CHANGE_TARGETS: dict[str, tuple[str, ...]] = {
    "memory": ("header", "metadata"),
    "metadata": ("header", "metadata"),
    "description": ("description",),
    "fields": ("fields",),
    "references": ("references", "photos", "figures"),
    "runs": ("references", "analysis", "figures"),
}


def render_memory_detail(memory_id: int, on_back: Callable[[], None]) -> None:
    """Render the memory detail view, opening in read-only mode."""
    state = {"editing": False, "visible": dashboard_conf.sections(SCOPE)}
    checkboxes: dict[str, ui.checkbox] = {}
    cards: dict[str, object] = {}
    refs: dict[str, object] = {"container": None}

    def set_visible(key: str, value: bool) -> bool:
        if state["visible"].get(key) == value:
            return False
        state["visible"][key] = value
        dashboard_conf.set_section_visible(key, value, SCOPE)
        return True

    @ui.refreshable
    def render_header() -> None:
        mem = db.get_memory(memory_id, with_runs=False)
        if mem:
            _render_header(mem, state["editing"])

    def fetch_memory(*keys: str) -> dict | None:
        """Fetch the memory, loading tool runs only when a target card needs them."""
        needs_runs = any(key in RUN_DEPENDENT_KEYS for key in keys)
        return db.get_memory(memory_id, with_runs=needs_runs, with_items=needs_runs)

    def on_card_changed(event: str) -> None:
        """Reload only the header and cards affected by `event`."""
        targets = CHANGE_TARGETS.get(event, (event,))
        card_keys = [key for key in targets if key in SECTION_CARDS]
        if "header" in targets:
            render_header.refresh()
        if not card_keys:
            return
        mem = fetch_memory(*card_keys)
        if mem is None:
            return
        for key in card_keys:
            card = cards.get(key)
            if card is not None:
                card.reload(mem)

    def remove_card(key: str) -> None:
        card = cards.pop(key, None)
        if card is not None:
            card.delete()

    def show_section(key: str) -> None:
        if key in cards or refs["container"] is None:
            return
        mem = fetch_memory(key)
        if mem is None:
            return
        card = build_section_card(
            container=refs["container"],
            key=key,
            memory=mem,
            project_root=PROJECT_ROOT,
            editing=state["editing"],
            conf=state["conf"],
            on_close=hide_section,
            on_changed=on_card_changed,
        )
        if card is not None:
            cards[key] = card

    def hide_section(key: str) -> None:
        set_visible(key, False)
        if key in checkboxes:
            checkboxes[key].value = False
        remove_card(key)

    def on_section_toggled(key: str, value: bool) -> None:
        if not set_visible(key, value):
            return
        if value:
            show_section(key)
        else:
            remove_card(key)

    def toggle_mode() -> None:
        state["editing"] = not state["editing"]
        mode_button.set_text("Done" if state["editing"] else "Edit")
        mode_button.set_icon("check" if state["editing"] else "edit")
        render_header.refresh()
        for key, card in list(cards.items()):
            card_class = SECTION_CARDS.get(key)
            if card_class is not None and card_class.depends_on_editing:
                card.set_editing(state["editing"])
                card.reload()

    def reset_sections() -> None:
        for key, value in SECTION_DEFAULTS.items():
            state["visible"][key] = value
            dashboard_conf.set_section_visible(key, value, SCOPE)
            if key in checkboxes:
                checkboxes[key].value = value
        for key in list(cards):
            if not state["visible"].get(key):
                remove_card(key)
        for key in dashboard_conf.card_order(SCOPE):
            if state["visible"].get(key) and key not in cards:
                show_section(key)

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

    with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        mem = db.get_memory(memory_id)
        if not mem:
            ui.label("Memory not found").classes("text-red-500 text-xl")
            ui.button("Back", icon="arrow_back", on_click=on_back)
            return

        state["conf"] = dashboard_conf.load(SCOPE)
        render_header()
        container = CardContainer(columns=state["conf"]["cards_per_row"])
        refs["container"] = container
        for key in dashboard_conf.card_order(SCOPE):
            if not state["visible"].get(key):
                continue
            card = build_section_card(
                container=container,
                key=key,
                memory=mem,
                project_root=PROJECT_ROOT,
                editing=state["editing"],
                conf=state["conf"],
                on_close=hide_section,
                on_changed=on_card_changed,
            )
            if card is not None:
                cards[key] = card


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
