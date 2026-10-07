import json
from nicegui import ui
from src import db
from dashboard.templates.memory import list_templates, sync_templates

from dashboard.pagetemplate import PageTemplate


class SettingsPage(PageTemplate):
    def __init__(self, **kwargs):
        self.container = None
        super().__init__(**kwargs)

    def main(self):
        with ui.column().classes('w-full p-4 gap-4'):
            with ui.row().classes('w-full items-center'):
                ui.label('Settings').classes('text-3xl font-bold')
                ui.space()
                ui.button('Sync Templates', icon='sync', on_click=self.sync_and_refresh).props('color=primary')

            self.container = ui.column().classes('w-full gap-2')

        self.refresh_templates()

    def sync_and_refresh(self):
        sync_templates()
        ui.notify('Templates synced', color='positive')
        self.refresh_templates()

    def refresh_templates(self):
        self.container.clear()
        templates = list_templates()

        with self.container:
            if not templates:
                ui.label('No templates found. Run sync to load YAML templates.').classes('text-gray-400 italic')
            else:
                for tmpl in templates:
                    self._render_template_card(tmpl)

    def _render_template_card(self, template: dict):
        fields = json.loads(template.get('fields_json', '[]'))

        with ui.card().classes('w-full'):
            with ui.row().classes('w-full items-center'):
                ui.label(template['name']).classes('text-lg font-semibold flex-1')
                ui.badge(f'{len(fields)} fields').props('outline')

            if template.get('description'):
                ui.label(template['description']).classes('text-sm text-gray-600')

            if fields:
                with ui.expansion('View fields').classes('w-full mt-2'):
                    for field in fields:
                        with ui.row().classes('gap-3 items-center'):
                            ui.label(field.get('name', '?')).classes('font-medium w-40')
                            ui.badge(field.get('type', '?')).props('outline')
                            ui.label(f"default: {field.get('default', '')}").classes('text-sm text-gray-500')
                            if field.get('required'):
                                ui.badge('required').props('color=red outline')
