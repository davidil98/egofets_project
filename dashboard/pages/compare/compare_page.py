from nicegui import ui
from src import db

from dashboard.pagetemplate import PageTemplate


class ComparePage(PageTemplate):
    def __init__(self, **kwargs):
        self.selected_ids = []
        self.memories_list = []
        self.list_container = None
        super().__init__(**kwargs)

    def sidebar(self):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('Select Memories').classes('text-lg font-semibold')

            self.list_container = ui.column().classes('w-full gap-2')

            ui.separator()

            ui.button('Compare Selected', icon='compare_arrows', on_click=self.compare_selected).props('color=primary').classes('w-full')

    def main(self):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('Compare View').classes('text-3xl font-bold')
            ui.label('Select multiple memories to compare their results side by side.').classes('text-gray-500')

            self.comparison_container = ui.column().classes('w-full gap-4')

        self.refresh_list()

    def refresh_list(self):
        self.list_container.clear()
        self.memories_list = db.list_memories()

        with self.list_container:
            for memory in self.memories_list:
                with ui.row().classes('w-full items-center gap-2'):
                    checkbox = ui.checkbox(
                        value=memory['id'] in self.selected_ids,
                        on_change=lambda e, mid=memory['id']: self.toggle_selection(mid, e.value)
                    )
                    ui.label(memory['title']).classes('flex-1 text-sm')

    def toggle_selection(self, memory_id, selected):
        if selected and memory_id not in self.selected_ids:
            self.selected_ids.append(memory_id)
        elif not selected and memory_id in self.selected_ids:
            self.selected_ids.remove(memory_id)

    def compare_selected(self):
        if len(self.selected_ids) < 2:
            ui.notify('Please select at least 2 memories to compare', type='warning')
            return

        self.comparison_container.clear()

        with self.comparison_container:
            ui.label(f'Comparing {len(self.selected_ids)} memories').classes('text-xl font-semibold')

            with ui.row().classes('w-full gap-4'):
                for memory_id in self.selected_ids:
                    memory = db.get_memory(memory_id)
                    if memory:
                        with ui.card().classes('flex-1'):
                            ui.label(memory['title']).classes('text-lg font-semibold')
                            ui.label(f"Type: {memory['type']}").classes('text-sm text-gray-600')
                            ui.label(f"Date: {memory.get('date', '')}").classes('text-sm text-gray-600')
                            if memory.get('substrate'):
                                ui.label(f"Substrate: {memory['substrate']}").classes('text-sm text-gray-600')

                            csv_refs = [r for r in memory.get('references', []) if r['ref_type'] == 'csv']
                            if csv_refs:
                                ui.label(f"CSV files: {len(csv_refs)}").classes('text-sm text-blue-600 mt-2')
