"""Memory creation dialog."""

import json
from nicegui import ui
from src import db
from dashboard.templates.memory import list_templates, apply_template_defaults


def show_create_dialog(on_created):
    """Show dialog for creating a new memory."""

    templates = list_templates()
    template_options = {"none": "No template"} | {str(t["id"]): t["name"] for t in templates}

    with ui.dialog() as dlg, ui.card().classes("w-[600px]"):
        ui.label("Create New Memory").classes("text-xl font-bold mb-4")

        template_select = ui.select(
            template_options,
            value="none",
            label="Template",
        ).props("outlined dense").classes("w-full")

        ui.separator().classes("my-2")
        ui.label("Base Fields").classes("text-sm font-medium text-gray-600")

        title_input = ui.input("Title *").props("outlined dense").classes("w-full")
        type_select = ui.select(
            {"experiment": "Experiment", "comparison": "Comparison"},
            value="experiment",
            label="Type",
        ).props("outlined dense").classes("w-full")
        subtype_select = ui.select(
            {"": "None", "device": "Device", "batch": "Batch",
             "wafer": "Wafer", "session": "Session"},
            value="",
            label="Subtype (for experiments)",
        ).props("outlined dense").classes("w-full")
        date_input = ui.input("Date (YYYY-MM-DD)").props("outlined dense").classes("w-full")
        desc_input = ui.textarea("Description").props("outlined dense").classes("w-full")
        substrate_input = ui.input("Substrate").props("outlined dense").classes("w-full")
        process_input = ui.input("Process").props("outlined dense").classes("w-full")

        ui.separator().classes("my-2")
        ui.label("Custom Fields (from template)").classes("text-sm font-medium text-gray-600")

        custom_fields_container = ui.column().classes("w-full gap-2")

        def apply_template():
            custom_fields_container.clear()
            tmpl_id = template_select.value
            if tmpl_id == "none":
                return

            defaults = apply_template_defaults(int(tmpl_id))
            with custom_fields_container:
                for name, value in defaults.items():
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(name).classes("w-40 text-sm font-medium")
                        ui.input(value=str(value)).props("outlined dense").classes("flex-1").mark(f"field_{name}")

        template_select.on_value_change(lambda _: apply_template())

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Create", icon="check", on_click=lambda: _do_create(
                dlg, title_input, type_select, subtype_select, date_input,
                desc_input, substrate_input, process_input, custom_fields_container,
                on_created,
            )).props("color=primary")

    dlg.open()


def _do_create(dlg, title_input, type_select, subtype_select, date_input,
               desc_input, substrate_input, process_input, custom_fields_container,
               on_created):
    if not title_input.value:
        ui.notify("Title is required", color="negative")
        return
    if not date_input.value:
        ui.notify("Date is required", color="negative")
        return

    custom_fields = {}
    for child in custom_fields_container:
        if hasattr(child, "content"):
            for sub in child.content:
                if hasattr(sub, "_markers"):
                    for marker in sub._markers:
                        if marker.startswith("field_"):
                            field_name = marker[6:]
                            custom_fields[field_name] = sub.value

    memory_id = db.create_memory(
        title=title_input.value,
        type=type_select.value,
        subtype=subtype_select.value or None,
        date=date_input.value,
        description=desc_input.value,
        substrate=substrate_input.value,
        process=process_input.value,
        custom_fields=custom_fields,
    )

    dlg.close()
    ui.notify(f"Memory '{title_input.value}' created", color="positive")
    on_created(memory_id)
