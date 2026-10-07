from nicegui import ui
from src import db

from dashboard.pagetemplate import PageTemplate


TYPE_COLORS = {
    "experiment": "blue",
    "comparison": "purple",
}

SUBTYPE_ICONS = {
    "device": "memory",
    "batch": "inventory_2",
    "wafer": "disk_full",
    "session": "science",
}


class HomePage(PageTemplate):
    def __init__(self, **kwargs):
        self.search_input = None
        self.type_select = None
        self.subtype_select = None
        self.substrate_select = None
        self.list_container = None
        super().__init__(**kwargs)

    def sidebar(self):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('Filters').classes('text-lg font-semibold')

            self.search_input = ui.input(
                'Search',
                on_change=lambda _: self.refresh_list()
            ).props('outlined dense').classes('w-full')

            self.type_select = ui.select(
                {'all': 'All types', 'experiment': 'Experiment', 'comparison': 'Comparison'},
                value='all',
                label='Type',
                on_change=lambda _: self.refresh_list()
            ).props('outlined dense').classes('w-full')

            self.subtype_select = ui.select(
                {'all': 'All subtypes', 'device': 'Device', 'batch': 'Batch',
                 'wafer': 'Wafer', 'session': 'Session'},
                value='all',
                label='Subtype',
                on_change=lambda _: self.refresh_list()
            ).props('outlined dense').classes('w-full')

            self.substrate_select = ui.select(
                {'all': 'All substrates', 'Kapton': 'Kapton', 'Si/SiO2': 'Si/SiO2',
                 'Glass': 'Glass'},
                value='all',
                label='Substrate',
                on_change=lambda _: self.refresh_list()
            ).props('outlined dense').classes('w-full')

            ui.separator()

            ui.button('New Memory', icon='add', on_click=self.show_create_dialog).props('color=primary').classes('w-full')

    def main(self):
        with ui.column().classes('w-full p-4 gap-4'):
            ui.label('Memories').classes('text-3xl font-bold')
            self.list_container = ui.column().classes('w-full gap-2')

        self.refresh_list()

    def refresh_list(self):
        self.list_container.clear()

        search = self.search_input.value if self.search_input else None
        mtype = self.type_select.value if self.type_select and self.type_select.value != 'all' else None
        subtype = self.subtype_select.value if self.subtype_select and self.subtype_select.value != 'all' else None
        substrate = self.substrate_select.value if self.substrate_select and self.substrate_select.value != 'all' else None

        memories = db.list_memories(
            type=mtype, subtype=subtype, substrate=substrate, search=search or None
        )

        with self.list_container:
            if not memories:
                ui.label('No memories found').classes('text-gray-400 italic p-8')
            else:
                for memory in memories:
                    self._render_memory_card(memory)

    def _render_memory_card(self, memory: dict):
        memory_id = memory['id']
        mtype = memory['type']
        subtype = memory.get('subtype') or ''
        color = TYPE_COLORS.get(mtype, 'gray')
        icon = SUBTYPE_ICONS.get(subtype, 'folder')

        with ui.card().classes('w-full cursor-pointer hover:shadow-md transition-shadow') as card:
            card.on('click', lambda _, mid=memory_id: ui.navigate.to(f'/memories/detail?id={mid}'))

            with ui.row().classes('w-full items-center gap-3 p-2'):
                ui.icon(icon).classes(f'text-{color}-500 text-2xl')
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(memory['title']).classes('text-lg font-semibold')
                    with ui.row().classes('gap-2 items-center'):
                        ui.badge(mtype).props(f'color={color} outline')
                        if subtype:
                            ui.badge(subtype).props('color=gray outline')
                        ui.label(memory.get('date', '')).classes('text-xs text-gray-500')
                        if memory.get('substrate'):
                            ui.label(f"{memory['substrate']}").classes('text-xs text-gray-500')
                ui.icon('chevron_right').classes('text-gray-400')

    def show_create_dialog(self):
        from dashboard.ui.memory_create import show_create_dialog

        def on_created(memory_id):
            ui.navigate.to(f'/memories/detail?id={memory_id}')

        show_create_dialog(on_created=on_created)
