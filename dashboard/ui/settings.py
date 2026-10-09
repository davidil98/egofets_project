"""Settings page — display configuration and template management."""

from nicegui import ui

from dashboard.config import DEFAULT_SCOPE, dashboard_conf
from dashboard.templates.memory import (
    delete_template_yaml,
    load_template_yaml,
    load_templates,
    save_template_yaml,
    template_yaml_exists,
)

MEMORY_DETAIL_SCOPE = "memory_detail"

SCOPE_OPTIONS = [DEFAULT_SCOPE, MEMORY_DETAIL_SCOPE]

FIELD_TYPES = {"text": "text", "integer": "integer", "float": "float"}

CONFIG_HELP = """cards_per_row      number of cards per row in the memory detail grid
card_height        default height of a card in pixels
card_fullscreen    allow cards to expand to full screen
sections.<key>     show or hide a card (metadata, description, fields,
                   references, analysis, figures, photos)
card_order         order of the cards, list of section keys
figures.max_height maximum height of a rendered plot in pixels
figures.show_table show the data table below a plot
photos.thumb_size  photo thumbnail size in pixels
photos.columns     number of columns in the photo grid"""


def render_settings(on_back):
    """Render the settings page with the display and templates tabs."""
    view_state: dict = {"scope": MEMORY_DETAIL_SCOPE}

    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("w-full items-center"):
            ui.button("Back", icon="arrow_back", on_click=on_back).props("flat")
            ui.label("Settings").classes("text-2xl font-bold ml-2")

        with ui.tabs() as tabs:
            ui.tab("display", label="Display", icon="dashboard")
            ui.tab("templates", label="Templates", icon="view_module")

        with ui.tab_panels(tabs, value="display").classes("w-full bg-transparent"):
            with ui.tab_panel("display"):
                display_container = ui.column().classes("w-full gap-3")
            with ui.tab_panel("templates"):
                templates_container = ui.column().classes("w-full gap-3")

        def refresh_display():
            _render_display_tab(display_container, refresh_all, view_state)

        def refresh_templates():
            _render_templates_tab(templates_container, refresh_all)

        def refresh_all():
            refresh_display()
            refresh_templates()

        refresh_all()


def _render_display_tab(container, refresh_all, view_state: dict):
    """Rebuild the display tab with the YAML editor of a config scope."""
    container.clear()

    scope = view_state.get("scope") or MEMORY_DETAIL_SCOPE
    if scope not in SCOPE_OPTIONS:
        scope = MEMORY_DETAIL_SCOPE

    with container:
        with ui.row().classes("w-full items-end gap-2"):
            scope_select = ui.select(
                SCOPE_OPTIONS, value=scope, label="Scope"
            ).props("outlined dense").classes("w-56")
            ui.space()
            ui.button("Reload", icon="refresh", on_click=lambda: do_reload()).props("flat")
            ui.button("Save", icon="save", on_click=lambda: do_save()).props("color=primary")

        editor = ui.codemirror(
            value=dashboard_conf.to_yaml(scope),
            language="YAML",
            theme="basicLight",
        ).classes("w-full").style(
            "height: 420px; border: 1px solid #cbd5e1; border-radius: 4px;"
        )

        def load_scope(selected: str):
            view_state["scope"] = selected
            try:
                editor.set_value(dashboard_conf.to_yaml(selected))
            except Exception as exc:
                dashboard_conf.notify(f"Error reading scope '{selected}': {exc}", "negative", 8000)

        scope_select.on_value_change(lambda e: load_scope(e.value))

        def do_save():
            scope = scope_select.value or DEFAULT_SCOPE
            try:
                dashboard_conf.save_yaml(scope, editor.value)
            except Exception as exc:
                dashboard_conf.notify(f"Invalid YAML for scope '{scope}': {exc}", "negative", 8000)
                return
            dashboard_conf.notify(f"Configuration saved for scope '{scope}'")
            refresh_all()

        def do_reload():
            try:
                dashboard_conf.reload()
            except Exception as exc:
                dashboard_conf.notify(f"Error reloading configuration: {exc}", "negative", 8000)
                return
            dashboard_conf.notify("Configuration reloaded from disk")
            refresh_all()

        with ui.card().classes("w-full"):
            ui.label("Configuration keys").classes("text-sm font-semibold text-gray-700")
            ui.label(CONFIG_HELP).classes("text-xs text-gray-600 whitespace-pre-line")


def _render_templates_tab(container, refresh_all):
    """Rebuild the template list with create, edit and delete actions."""
    container.clear()

    templates = load_templates()

    with container:
        with ui.row().classes("w-full items-center gap-2"):
            ui.button(
                "New Template",
                icon="add",
                on_click=lambda: _show_template_dialog(None, refresh_all),
            ).props("color=primary")
            ui.space()
            ui.label(f"{len(templates)} templates").classes("text-sm text-gray-500")

        if not templates:
            ui.label("No templates yet. Create one with New Template.").classes("text-gray-400 italic")
        else:
            for tmpl in templates:
                _render_template_card(tmpl, refresh_all)


def _render_template_card(template: dict, refresh_all):
    """Render one template card with edit and delete buttons."""
    fields = template.get("fields") or []
    name = template["name"]

    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center gap-2"):
            ui.label(name).classes("text-lg font-semibold flex-1")
            ui.badge(f"{len(fields)} fields").props("outline")
            ui.button(
                icon="edit", on_click=lambda n=name: _show_template_dialog(n, refresh_all)
            ).props("flat color=primary size=sm").tooltip("Edit template")
            ui.button(
                icon="delete", on_click=lambda n=name: _confirm_delete_template(n, refresh_all)
            ).props("flat color=negative size=sm").tooltip("Delete template")

        if template.get("description"):
            ui.label(template["description"]).classes("text-sm text-gray-600")

        if fields:
            with ui.expansion("View fields").classes("w-full mt-2"):
                for field in fields:
                    with ui.row().classes("gap-3 items-center"):
                        ui.label(field.get("name", "?")).classes("font-medium w-40")
                        ui.badge(field.get("type", "?")).props("outline")
                        ui.label(f"default: {field.get('default', '')}").classes("text-sm text-gray-500")
                        if field.get("required"):
                            ui.badge("required").props("color=red outline")


def _template_source(name: str) -> dict:
    """Return the YAML definition used to prefill the edit dialog."""
    data = load_template_yaml(name)
    if isinstance(data, dict):
        return data
    return {"name": name, "description": "", "fields": []}


def _convert_default(raw, field_type: str) -> str | int | float:
    """Convert a default value entered as text into its declared type."""
    if field_type == "text":
        return "" if raw is None else str(raw)

    text = "" if raw is None else str(raw).strip()
    if field_type == "integer":
        return int(text) if text else 0
    if field_type == "float":
        return float(text) if text else 0.0
    raise ValueError(f"Unknown field type '{field_type}'")


def _show_template_dialog(name: str | None, refresh_all):
    """Open the create/edit dialog for a template."""
    editing = name is not None
    source = _template_source(name) if editing else {"name": "", "description": "", "fields": []}

    field_data: list[dict] = [
        {
            "name": str(field.get("name", "")),
            "type": field.get("type") if field.get("type") in FIELD_TYPES else "text",
            "default": "" if field.get("default") is None else str(field.get("default")),
            "required": bool(field.get("required", False)),
        }
        for field in (source.get("fields") or [])
        if isinstance(field, dict)
    ]
    row_widgets: list[dict] = []

    with ui.dialog() as dlg, ui.card().classes("w-[880px] max-h-[90vh] overflow-auto"):
        ui.label("Edit Template" if editing else "New Template").classes("text-xl font-bold")

        name_input = ui.input("Name", value=source.get("name") or "").props("outlined dense").classes("w-full")
        if editing:
            name_input.props("readonly")
        else:
            name_input.props('hint="lowercase letters, digits and underscores"')

        description_input = ui.textarea(
            "Description", value=source.get("description") or ""
        ).props("outlined dense").classes("w-full")

        ui.label("Fields").classes("text-sm font-semibold text-gray-700 mt-2")
        fields_box = ui.column().classes("w-full gap-2")

        def collect():
            for index, widgets in enumerate(row_widgets):
                if index >= len(field_data):
                    continue
                field_data[index] = {
                    "name": widgets["name"].value or "",
                    "type": widgets["type"].value or "text",
                    "default": widgets["default"].value or "",
                    "required": bool(widgets["required"].value),
                }

        def render_rows():
            fields_box.clear()
            row_widgets.clear()
            with fields_box:
                if not field_data:
                    ui.label("No fields defined yet.").classes("text-gray-400 italic text-sm")
                for index, item in enumerate(field_data):
                    with ui.row().classes("w-full items-end gap-2"):
                        widgets = {
                            "name": ui.input("Field name", value=item["name"]).props(
                                "outlined dense"
                            ).classes("flex-1"),
                            "type": ui.select(
                                FIELD_TYPES, value=item["type"], label="Type"
                            ).props("outlined dense").classes("w-32"),
                            "default": ui.input("Default", value=item["default"]).props(
                                "outlined dense"
                            ).classes("w-40"),
                            "required": ui.switch("Required", value=item["required"]).props("dense"),
                        }
                        ui.button(
                            icon="delete", on_click=lambda i=index: remove_row(i)
                        ).props("flat color=negative size=sm")
                    row_widgets.append(widgets)

        def add_row():
            collect()
            field_data.append({"name": "", "type": "text", "default": "", "required": False})
            render_rows()

        def remove_row(index: int):
            collect()
            del field_data[index]
            render_rows()

        render_rows()

        with ui.row().classes("w-full justify-between items-center gap-2 mt-2"):
            ui.button("Add field", icon="add", on_click=lambda: add_row()).props("flat color=primary")
            with ui.row().classes("gap-2"):
                ui.button("Cancel", on_click=dlg.close).props("flat")
                ui.button("Save", icon="save", on_click=lambda: do_save()).props("color=primary")

        def do_save():
            collect()

            template_name = (name_input.value or "").strip()
            if not template_name:
                dashboard_conf.notify("Template name is required", "negative", 6000)
                return

            if not editing and template_yaml_exists(template_name):
                dashboard_conf.notify(f"Template '{template_name}' already exists", "negative", 6000)
                return

            fields: list[dict] = []
            for index, item in enumerate(field_data):
                field_name = (item["name"] or "").strip()
                if not field_name:
                    dashboard_conf.notify(f"Field {index + 1}: name is required", "negative", 6000)
                    return
                field_type = item["type"] or "text"
                try:
                    default = _convert_default(item["default"], field_type)
                except (TypeError, ValueError) as exc:
                    dashboard_conf.notify(
                        f"Field '{field_name}': invalid {field_type} default "
                        f"'{item['default']}' ({exc})",
                        "negative",
                        8000,
                    )
                    return
                fields.append(
                    {
                        "name": field_name,
                        "type": field_type,
                        "default": default,
                        "required": bool(item["required"]),
                    }
                )

            try:
                path = save_template_yaml(
                    template_name, (description_input.value or "").strip(), fields
                )
            except Exception as exc:
                dashboard_conf.notify(f"Error saving template: {exc}", "negative", 8000)
                return

            dashboard_conf.notify(f"Template '{path.stem}' saved")
            dlg.close()
            refresh_all()

    dlg.open()


def _confirm_delete_template(name: str, refresh_all):
    """Ask for confirmation before deleting a template file."""
    with ui.dialog() as dlg, ui.card().classes("w-96"):
        ui.label(f"Delete template '{name}'?").classes("text-lg font-bold")
        ui.label(
            "Only the template file is removed. Memories already created from it keep their fields."
        ).classes("text-sm text-gray-600")

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dlg.close).props("flat")

            def do_delete():
                dlg.close()
                _delete_template(name, refresh_all)

            ui.button("Delete", icon="delete", on_click=do_delete).props("color=negative")

    dlg.open()


def _delete_template(name: str, refresh_all):
    """Delete the YAML file of a template."""
    try:
        removed = delete_template_yaml(name)
    except Exception as exc:
        dashboard_conf.notify(f"Could not delete '{name}': {exc}", "negative", 8000)
        return

    if not removed:
        dashboard_conf.notify(f"Template '{name}' was already gone", "warning")
    else:
        dashboard_conf.notify(f"Template '{name}' deleted")
    refresh_all()
