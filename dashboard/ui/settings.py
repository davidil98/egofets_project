"""Settings page — template management."""

import json
from nicegui import ui
from src import db
from dashboard.templates.memory import list_templates, sync_templates


def render_settings(on_back):
    """Render the settings page with template management."""
    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("w-full items-center"):
            ui.button("Back", icon="arrow_back", on_click=on_back).props("flat")
            ui.label("Settings").classes("text-2xl font-bold ml-2")
            ui.space()
            ui.button("Sync Templates", icon="sync", on_click=lambda: (
                sync_templates(),
                ui.notify("Templates synced", color="positive"),
                refresh(),
            )).props("color=primary")

        container = ui.column().classes("w-full gap-2")

        def refresh():
            container.clear()
            templates = list_templates()

            with container:
                if not templates:
                    ui.label("No templates found. Run sync to load YAML templates.").classes(
                        "text-gray-400 italic"
                    )
                else:
                    for tmpl in templates:
                        _render_template_card(tmpl)

        refresh()


def _render_template_card(template: dict):
    fields = json.loads(template.get("fields_json", "[]"))

    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center"):
            ui.label(template["name"]).classes("text-lg font-semibold flex-1")
            ui.badge(f"{len(fields)} fields").props("outline")

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
