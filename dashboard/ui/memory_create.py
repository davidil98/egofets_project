"""Memory creation dialog."""

from nicegui import ui
from src import db
from dashboard.templates.memory import apply_template_defaults, load_templates


def show_create_dialog(on_created):
    """Show dialog for creating a new memory."""

    template_options = {"": "No template"} | {t["name"]: t["name"] for t in load_templates()}
    field_inputs: dict[str, ui.input] = {}

    with ui.dialog() as dlg, ui.card().classes("w-[600px] max-h-[90vh] overflow-auto"):
        ui.label("Create New Memory").classes("text-xl font-bold mb-4")

        template_select = ui.select(
            template_options,
            value="",
            label="Pre-fill from template",
        ).props("outlined dense").classes("w-full")

        ui.separator().classes("my-2")

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
        ui.label("Fields").classes("text-sm font-medium text-gray-600")

        fields_container = ui.column().classes("w-full gap-2")

        def apply_template():
            fields_container.clear()
            field_inputs.clear()
            defaults = apply_template_defaults(template_select.value or "")
            with fields_container:
                if not defaults:
                    ui.label("No fields yet. Pick a template to pre-fill them.").classes(
                        "text-sm text-gray-400 italic"
                    )
                for name, value in defaults.items():
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(name).classes("w-40 text-sm font-medium")
                        field_inputs[name] = ui.input(value=str(value)).props("outlined dense").classes("flex-1")

        template_select.on_value_change(lambda _: apply_template())
        apply_template()

        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Create", icon="check", on_click=lambda: _do_create(
                dlg, title_input, type_select, subtype_select, date_input,
                desc_input, substrate_input, process_input, field_inputs,
                on_created,
            )).props("color=primary")

    dlg.open()


def _do_create(dlg, title_input, type_select, subtype_select, date_input,
               desc_input, substrate_input, process_input, field_inputs,
               on_created):
    if not title_input.value:
        ui.notify("Title is required", color="negative")
        return
    if not date_input.value:
        ui.notify("Date is required", color="negative")
        return

    custom_fields = {name: (widget.value or "") for name, widget in field_inputs.items()}

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
