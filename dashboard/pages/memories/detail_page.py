import json
from pathlib import Path
from nicegui import ui
from src import db
from dashboard.file_picker import pick_file

from dashboard.pagetemplate import PageTemplate


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class DetailPage(PageTemplate):
    def __init__(self, **kwargs):
        self.memory_id = None
        self.memory = None
        self.edit_mode = False
        self.content_container = None
        super().__init__(**kwargs)

    def sidebar(self):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.button('Back to List', icon='arrow_back', on_click=lambda: ui.navigate.to('/memories/home')).props('flat').classes('w-full')

            ui.separator()

            ui.label('Actions').classes('text-lg font-semibold')

            with ui.row().classes('w-full gap-2'):
                edit_btn = ui.button(
                    'Edit' if not self.edit_mode else 'View',
                    icon='edit' if not self.edit_mode else 'visibility',
                    on_click=self.toggle_edit_mode
                ).props('color=primary').classes('flex-1')

                ui.button('Export', icon='download', on_click=self.show_export_dialog).props('color=secondary')

            ui.separator()

            ui.label('Info').classes('text-lg font-semibold')
            if self.memory:
                ui.badge(self.memory['type']).props('color=blue outline')
                if self.memory.get('subtype'):
                    ui.badge(self.memory['subtype']).props('color=gray outline')
                ui.label(f"Date: {self.memory.get('date', '')}").classes('text-sm text-gray-500')
                if self.memory.get('substrate'):
                    ui.label(f"Substrate: {self.memory['substrate']}").classes('text-sm text-gray-500')

    def main(self):
        memory_id_str = self.query_params.get('id')
        if not memory_id_str:
            with ui.column().classes('w-full p-4'):
                ui.label('No memory ID provided').classes('text-red-500 text-xl')
                ui.button('Back to List', icon='arrow_back', on_click=lambda: ui.navigate.to('/memories/home'))
            return

        self.memory_id = int(memory_id_str)
        self.memory = db.get_memory(self.memory_id)

        if not self.memory:
            with ui.column().classes('w-full p-4'):
                ui.label('Memory not found').classes('text-red-500 text-xl')
                ui.button('Back to List', icon='arrow_back', on_click=lambda: ui.navigate.to('/memories/home'))
            return

        with ui.column().classes('w-full p-4 gap-4'):
            ui.label(self.memory['title']).classes('text-3xl font-bold')

            with ui.tabs().classes('w-full') as tabs:
                metadata_tab = ui.tab('Metadata')
                fields_tab = ui.tab('Custom Fields')
                references_tab = ui.tab('References')
                analysis_tab = ui.tab('Analysis')
                figures_tab = ui.tab('Figures')
                photos_tab = ui.tab('Photos')

            self.content_container = ui.column().classes('w-full gap-4')

        def on_tab_change(e):
            self.content_container.clear()
            with self.content_container:
                if e.value == metadata_tab:
                    self._render_metadata_card()
                elif e.value == fields_tab:
                    self._render_fields_card()
                elif e.value == references_tab:
                    self._render_references_card()
                elif e.value == analysis_tab:
                    self._render_analysis_card()
                elif e.value == figures_tab:
                    self._render_figures_card()
                elif e.value == photos_tab:
                    self._render_photos_card()

        tabs.on_value_change(on_tab_change)

        with self.content_container:
            self._render_metadata_card()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        ui.navigate.reload()

    def _render_metadata_card(self):
        with ui.card().classes('w-full'):
            ui.label('Metadata').classes('text-lg font-semibold mb-2')

            if self.edit_mode:
                title_input = ui.input('Title', value=self.memory['title']).classes('w-full').props('outlined dense')
                desc_input = ui.textarea('Description', value=self.memory.get('description', '')).classes('w-full').props('outlined dense')
                date_input = ui.input('Date', value=self.memory.get('date', '')).classes('w-full').props('outlined dense')
                substrate_input = ui.input('Substrate', value=self.memory.get('substrate', '')).classes('w-full').props('outlined dense')
                process_input = ui.input('Process', value=self.memory.get('process', '')).classes('w-full').props('outlined dense')

                with ui.row().classes('gap-2 mt-2'):
                    ui.button('Save', icon='save', on_click=lambda: self._save_metadata(
                        title_input.value, desc_input.value, date_input.value,
                        substrate_input.value, process_input.value
                    )).props('color=primary')
            else:
                ui.label(f"Title: {self.memory['title']}").classes('text-md')
                ui.label(f"Description: {self.memory.get('description', '')}").classes('text-sm text-gray-600')
                ui.label(f"Date: {self.memory.get('date', '')}").classes('text-sm text-gray-600')
                ui.label(f"Substrate: {self.memory.get('substrate', '')}").classes('text-sm text-gray-600')
                ui.label(f"Process: {self.memory.get('process', '')}").classes('text-sm text-gray-600')

    def _save_metadata(self, title, description, date, substrate, process):
        db.update_memory(
            self.memory_id,
            title=title,
            description=description,
            date=date,
            substrate=substrate,
            process=process,
        )
        ui.notify('Saved', color='positive')
        ui.navigate.reload()

    def _render_fields_card(self):
        custom_fields = [f for f in self.memory.get('fields', []) if f['field_type'] == 'custom']

        with ui.card().classes('w-full'):
            ui.label(f'Custom Fields ({len(custom_fields)})').classes('text-lg font-semibold mb-2')

            if self.edit_mode:
                for field in custom_fields:
                    with ui.row().classes('w-full items-center gap-2'):
                        name_input = ui.input(value=field['field_name']).classes('flex-1').props('dense outlined')
                        value_input = ui.input(value=field['field_value']).classes('flex-1').props('dense outlined')
                        ui.button(icon='delete', on_click=lambda f=field: (
                            db.delete_field(f['id']),
                            ui.navigate.reload(),
                        )).props('flat color=negative size=sm')

                        name_input.on_value_change(lambda e, f=field: db.update_field(f['id'], field_name=e.value))
                        value_input.on_value_change(lambda e, f=field: db.update_field(f['id'], field_value=e.value))

                with ui.row().classes('mt-2 gap-2'):
                    new_name = ui.input('Name').props('dense outlined').classes('flex-1')
                    new_value = ui.input('Value').props('dense outlined').classes('flex-1')
                    ui.button('Add', icon='add', on_click=lambda: (
                        db.add_field(self.memory_id, new_name.value, new_value.value, 'custom'),
                        new_name.set_value(''),
                        new_value.set_value(''),
                        ui.navigate.reload(),
                    )).props('color=primary')
            else:
                if not custom_fields:
                    ui.label('No custom fields').classes('text-gray-400 italic')
                else:
                    for field in custom_fields:
                        with ui.row().classes('w-full items-center gap-2'):
                            ui.label(field['field_name']).classes('font-medium w-40')
                            ui.label(field['field_value']).classes('flex-1')

    def _render_references_card(self):
        with ui.card().classes('w-full'):
            ui.label('References').classes('text-lg font-semibold mb-2')

            for ref in self.memory.get('references', []):
                with ui.row().classes('w-full items-center gap-2'):
                    ui.badge(ref['ref_type']).props('outline')
                    ui.label(ref['ref_path']).classes('flex-1 text-sm font-mono truncate')
                    if self.edit_mode:
                        ui.button(icon='delete', on_click=lambda r=ref: (
                            db.delete_reference(r['id']),
                            ui.navigate.reload(),
                        )).props('flat color=negative size=sm')

            if self.edit_mode:
                with ui.row().classes('mt-2 gap-2 items-end'):
                    ref_type_select = ui.select(
                        ['hdf5', 'photo', 'csv', 'figure'],
                        value='csv',
                        label='Type',
                    ).props('outlined dense').classes('w-28')

                    async def pick_and_add():
                        project_dir = str(PROJECT_ROOT)
                        extensions_map = {
                            'hdf5': ('.hdf5',),
                            'photo': ('.jpg', '.jpeg', '.png'),
                            'csv': ('.csv',),
                            'figure': ('.png', '.pdf', '.svg'),
                        }
                        exts = extensions_map.get(ref_type_select.value, ())
                        paths = await pick_file(directory=project_dir, multiple=True, extensions=exts)
                        for p in paths:
                            import os
                            rel_path = os.path.relpath(p, str(PROJECT_ROOT))
                            db.add_reference(self.memory_id, ref_type_select.value, rel_path)
                        ui.navigate.reload()

                    ui.button('Add Files', icon='attach_file', on_click=lambda: ui.timer(0.0, pick_and_add, once=True)).props('color=primary')

    def _render_analysis_card(self):
        results = self.memory.get('analysis_results', [])

        with ui.card().classes('w-full'):
            ui.label(f'Analysis Results ({len(results)})').classes('text-lg font-semibold mb-2')

            if not results:
                ui.label('No analysis results yet').classes('text-gray-400 italic')
            else:
                for result in results:
                    with ui.expansion(f"{result['function_name']} ({result.get('created_at', '')[:10]})").classes('w-full'):
                        params = json.loads(result.get('params_json', '{}'))
                        if params:
                            ui.label('Parameters:').classes('font-medium text-sm')
                            for k, v in params.items():
                                ui.label(f'  {k}: {v}').classes('text-sm')
                        if result.get('results_csv_path'):
                            ui.label(f"CSV: {result['results_csv_path']}").classes('text-sm text-blue-600')

    def _render_figures_card(self):
        from dashboard.ui.viewers import create_csv_viewer
        import pandas as pd

        csv_refs = [r for r in self.memory.get('references', []) if r['ref_type'] == 'csv']

        with ui.card().classes('w-full'):
            ui.label(f'Figures ({len(csv_refs)})').classes('text-lg font-semibold mb-2')

            if not csv_refs:
                ui.label('No CSV references').classes('text-gray-400 italic')
            else:
                for ref in csv_refs:
                    create_csv_viewer(PROJECT_ROOT / ref['ref_path'])

    def _render_photos_card(self):
        from dashboard.ui.viewers import create_photo_viewer

        photo_refs = [r for r in self.memory.get('references', []) if r['ref_type'] == 'photo']

        with ui.card().classes('w-full'):
            ui.label(f'Photos ({len(photo_refs)})').classes('text-lg font-semibold mb-2')

            if not photo_refs:
                ui.label('No photo references').classes('text-gray-400 italic')
            else:
                for ref in photo_refs:
                    create_photo_viewer(PROJECT_ROOT / ref['ref_path'])

    def show_export_dialog(self):
        with ui.dialog() as dlg, ui.card().classes('w-96'):
            ui.label('Export Memory').classes('text-xl font-bold mb-4')

            format_select = ui.select(
                ['HTML', 'PDF'],
                value='HTML',
                label='Format',
            ).props('outlined dense').classes('w-full')

            include_figures = ui.checkbox('Include figures', value=True)
            include_photos = ui.checkbox('Include photos', value=True)

            status_label = ui.label('').classes('text-sm text-gray-500 mt-2')

            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ui.button('Cancel', on_click=dlg.close).props('flat')

                async def do_export():
                    status_label.text = 'Exporting...'
                    try:
                        if format_select.value == 'HTML':
                            from dashboard.exporters.html import export_memory_html
                            path = export_memory_html(
                                memory_id=self.memory_id,
                                include_figures=include_figures.value,
                                include_photos=include_photos.value,
                            )
                        else:
                            from dashboard.exporters.pdf import export_memory_pdf
                            path = export_memory_pdf(
                                memory_id=self.memory_id,
                                include_figures=include_figures.value,
                                include_photos=include_photos.value,
                            )

                        if path:
                            status_label.text = f'Exported to: {path.name}'
                            status_label.classes('text-green-600')
                            ui.notify(f'Exported to {path.name}', color='positive')
                            ui.timer(2.0, dlg.close, once=True)
                        else:
                            status_label.text = 'Export failed'
                            status_label.classes('text-red-600')
                    except Exception as e:
                        status_label.text = f'Error: {e}'
                        status_label.classes('text-red-600')

                ui.button('Export', icon='check', on_click=do_export).props('color=primary')

        dlg.open()
