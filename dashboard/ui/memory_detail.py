"""Memory detail page — view/edit a single memory."""

from nicegui import ui
from src import db
from dashboard.file_picker import pick_file, picker_start_directory
import json


PROJECT_ROOT = None


def render_memory_detail(memory_id: int, on_back):
    """Render the memory detail page."""
    import sys
    from pathlib import Path
    global PROJECT_ROOT
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    memory = db.get_memory(memory_id)
    if not memory:
        ui.label("Memory not found").classes("text-red-500 text-xl")
        ui.button("Back", icon="arrow_back", on_click=on_back)
        return

    container = ui.column().classes("w-full gap-4")

    def refresh():
        container.clear()
        mem = db.get_memory(memory_id)
        with container:
            _render_header(mem, on_back)
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.column().classes("flex-1 gap-4"):
                    _render_metadata_card(mem, refresh)
                    _render_fields_card(mem, refresh)
                    _render_references_card(mem, refresh)
                with ui.column().classes("flex-1 gap-4"):
                    _render_analysis_card(mem)
                    _render_figures_card(mem)
                    _render_photos_card(mem)

    refresh()


def _render_header(memory: dict, on_back):
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.button(icon="arrow_back", on_click=on_back).props("flat round")
            with ui.column().classes("flex-1"):
                ui.label(memory["title"]).classes("text-2xl font-bold")
                with ui.row().classes("gap-2 items-center"):
                    ui.badge(memory["type"]).props("color=blue outline")
                    if memory.get("subtype"):
                        ui.badge(memory["subtype"]).props("color=gray outline")
                    ui.label(memory.get("date", "")).classes("text-sm text-gray-500")


def _render_metadata_card(memory: dict, refresh):
    with ui.card().classes("w-full"):
        ui.label("Metadata").classes("text-lg font-semibold mb-2")

        title_input = ui.input("Title", value=memory["title"]).classes("w-full").props("outlined dense")
        desc_input = ui.textarea("Description", value=memory.get("description", "")).classes("w-full").props("outlined dense")
        date_input = ui.input("Date", value=memory.get("date", "")).classes("w-full").props("outlined dense")
        substrate_input = ui.input("Substrate", value=memory.get("substrate", "")).classes("w-full").props("outlined dense")
        process_input = ui.input("Process", value=memory.get("process", "")).classes("w-full").props("outlined dense")

        with ui.row().classes("gap-2 mt-2"):
            ui.button("Save", icon="save", on_click=lambda: (
                db.update_memory(
                    memory["id"],
                    title=title_input.value,
                    description=desc_input.value,
                    date=date_input.value,
                    substrate=substrate_input.value,
                    process=process_input.value,
                ),
                ui.notify("Saved", color="positive"),
                refresh(),
            )).props("color=primary")


def _render_fields_card(memory: dict, refresh):
    custom_fields = [f for f in memory.get("fields", []) if f["field_type"] == "custom"]

    with ui.card().classes("w-full"):
        ui.label(f"Custom Fields ({len(custom_fields)})").classes("text-lg font-semibold mb-2")

        for field in custom_fields:
            with ui.row().classes("w-full items-center gap-2"):
                name_input = ui.input(value=field["field_name"]).classes("flex-1").props("dense outlined")
                value_input = ui.input(value=field["field_value"]).classes("flex-1").props("dense outlined")
                ui.button(icon="delete", on_click=lambda f=field: (
                    db.delete_field(f["id"]),
                    refresh(),
                )).props("flat color=negative size=sm")

                name_input.on_value_change(lambda e, f=field: db.update_field(f["id"], field_name=e.value))
                value_input.on_value_change(lambda e, f=field: db.update_field(f["id"], field_value=e.value))

        with ui.row().classes("mt-2 gap-2"):
            new_name = ui.input("Name").props("dense outlined").classes("flex-1")
            new_value = ui.input("Value").props("dense outlined").classes("flex-1")
            ui.button("Add", icon="add", on_click=lambda: (
                db.add_field(memory["id"], new_name.value, new_value.value, "custom"),
                new_name.set_value(""),
                new_value.set_value(""),
                refresh(),
            )).props("color=primary")


def _render_references_card(memory: dict, refresh):
    with ui.card().classes("w-full"):
        ui.label("References").classes("text-lg font-semibold mb-2")

        for ref in memory.get("references", []):
            with ui.row().classes("w-full items-center gap-2"):
                ui.badge(ref["ref_type"]).props("outline")
                ui.label(ref["ref_path"]).classes("flex-1 text-sm font-mono truncate")
                ui.button(icon="delete", on_click=lambda r=ref: (
                    db.delete_reference(r["id"]),
                    refresh(),
                )).props("flat color=negative size=sm")

        with ui.row().classes("mt-2 gap-2 items-end"):
            ref_type_select = ui.select(
                ["hdf5", "photo", "csv", "figure"],
                value="csv",
                label="Type",
            ).props("outlined dense").classes("w-28")

            async def pick_and_add():
                project_dir = str(PROJECT_ROOT)
                extensions_map = {
                    "hdf5": (".hdf5",),
                    "photo": (".jpg", ".jpeg", ".png"),
                    "csv": (".csv",),
                    "figure": (".png", ".pdf", ".svg"),
                }
                exts = extensions_map.get(ref_type_select.value, ())
                paths = await pick_file(directory=project_dir, multiple=True, extensions=exts)
                for p in paths:
                    import os
                    rel_path = os.path.relpath(p, str(PROJECT_ROOT))
                    db.add_reference(memory["id"], ref_type_select.value, rel_path)
                refresh()

            ui.button("Add Files", icon="attach_file", on_click=lambda: ui.timer(0.0, pick_and_add, once=True)).props("color=primary")


def _render_analysis_card(memory: dict):
    results = memory.get("analysis_results", [])

    with ui.card().classes("w-full"):
        ui.label(f"Analysis Results ({len(results)})").classes("text-lg font-semibold mb-2")

        if not results:
            ui.label("No analysis results yet").classes("text-gray-400 italic")
        else:
            for result in results:
                with ui.expansion(f"{result['function_name']} ({result.get('created_at', '')[:10]})").classes("w-full"):
                    params = json.loads(result.get("params_json", "{}"))
                    if params:
                        ui.label("Parameters:").classes("font-medium text-sm")
                        for k, v in params.items():
                            ui.label(f"  {k}: {v}").classes("text-sm")
                    if result.get("results_csv_path"):
                        ui.label(f"CSV: {result['results_csv_path']}").classes("text-sm text-blue-600")


def _render_figures_card(memory: dict):
    from dashboard.ui.viewers import create_csv_viewer
    import pandas as pd

    csv_refs = [r for r in memory.get("references", []) if r["ref_type"] == "csv"]

    with ui.card().classes("w-full"):
        ui.label(f"Figures ({len(csv_refs)})").classes("text-lg font-semibold mb-2")

        if not csv_refs:
            ui.label("No CSV references").classes("text-gray-400 italic")
        else:
            for ref in csv_refs:
                create_csv_viewer(PROJECT_ROOT / ref["ref_path"])


def _render_photos_card(memory: dict):
    from dashboard.ui.viewers import create_photo_viewer

    photo_refs = [r for r in memory.get("references", []) if r["ref_type"] == "photo"]

    with ui.card().classes("w-full"):
        ui.label(f"Photos ({len(photo_refs)})").classes("text-lg font-semibold mb-2")

        if not photo_refs:
            ui.label("No photo references").classes("text-gray-400 italic")
        else:
            for ref in photo_refs:
                create_photo_viewer(PROJECT_ROOT / ref["ref_path"])
