from abc import abstractmethod, ABC
from typing import Optional

from nicegui import ui
from nicegui.events import KeyEventArguments
from fastapi import Request

from dashboard.components.pageconf import globalpageconf
from dashboard.components.pageinfo import PageInfo
from dashboard.header import create_menu, reload_modules


class PageTemplate(ABC):

    def __init__(self, **kwargs):
        self.pageinfo: PageInfo = kwargs.get('pageinfo')
        self.request: Request = kwargs.get('request')
        self.query_params = dict(self.request.query_params) if self.request else {}

        self.pageconf = globalpageconf.load(self.pageinfo.route)

        self.ui_left_drawer: Optional[ui.left_drawer] = None
        self.ui_keyboard: Optional[ui.keyboard] = None

        self.has_sidebar = self.check_sidebar()

        self.render()

    def render(self):
        self._add_resources()
        self._setup_keyboard()
        self.header()
        if self.has_sidebar:
            self._create_sidebar()
        self.main()
        self.events()

    def _add_resources(self):
        ui.add_head_html('''
            <link rel="stylesheet" href="/static/styles.css">
            <link rel="stylesheet" href="/static/header.css">
        ''')

        if self.has_sidebar:
            ui.add_head_html('''
                <script src="/static/drawer.js"></script>
            ''')

    def _setup_keyboard(self):
        def handle_key(e: KeyEventArguments):
            if (e.modifiers.ctrl and e.key == 'q' and e.action.keydown and not e.action.repeat and self.ui_left_drawer):
                self.ui_left_drawer.toggle()

        self.ui_keyboard = ui.keyboard(on_key=handle_key)
        self.ui_keyboard.active = True

    def check_sidebar(self) -> bool:
        sidebar_method = getattr(self.__class__, 'sidebar', None)
        return sidebar_method is not None and sidebar_method.__qualname__.split('.')[0] != 'PageTemplate'

    def header(self) -> None:
        with ui.header():
            with ui.row().classes('items-center'):
                ui.label(self.pageinfo.route).classes('text-white text-xl font-bold').style('width: 350px;')
                if self.has_sidebar:
                    ui.button(icon='menu', on_click=lambda: self.ui_left_drawer.toggle()).props('flat color=white')

                ui.button(icon='settings',
                          on_click=lambda: globalpageconf.open_settings_dialog(self.pageinfo)).props('flat color=white')
                ui.html(create_menu())

            with ui.row().classes('gap-2'):
                ui.button(icon='sync', on_click=reload_modules).props('flat color=white')

    def _create_sidebar(self) -> None:
        width = self.pageconf.get('sidebar_width', 350)
        with ui.left_drawer().props(f'width={width}') as self.ui_left_drawer:
            self.sidebar()

    def sidebar(self) -> None:
        pass

    @abstractmethod
    def main(self) -> None:
        pass

    def events(self) -> None:
        pass
