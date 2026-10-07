import sys
from pathlib import Path
import importlib

from nicegui import ui, app
from fastapi import Request

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import db
from dashboard.templates.memory import sync_templates
from dashboard.components.pagemanager import pagemanager
from dashboard.components.pageinfo import PageInfo


def _init():
    db.init_db()
    sync_templates()


_native_available = False
try:
    import webview
    _native_available = True
except ImportError:
    pass


app.add_static_files('/static', str(Path(__file__).parent / 'static'))


@ui.page('/')
def root_page():
    _init()
    ui.navigate.to('/memories/home')


@ui.page('/{path:path}')
async def dynamic_page(request: Request):
    _init()

    path = request.url.path.strip('/')
    route = f'/{path}'

    pages = pagemanager.get_pages()
    pageinfo: PageInfo = pages.get(route)

    if pageinfo is not None:
        try:
            module = importlib.import_module(pageinfo.modulepath)
            if hasattr(module, pageinfo.classname):
                ModuleClass = getattr(module, pageinfo.classname)
                ModuleClass(pageinfo=pageinfo, request=request)
            else:
                error_page(route, f"Class {pageinfo.classname} not found in module")
        except Exception as e:
            error_page(route, f"Error: {str(e)}")
    else:
        error_page(route)


def error_page(route, error_message=None):
    ui.label(f"Page not found: {route}").classes('text-red-500 text-xl')
    if error_message:
        ui.label(error_message).classes('text-red-400')
    ui.button('Go to Home', on_click=lambda: ui.navigate.to('/memories/home'))


ui.run(
    title='EGOFET Memory Dashboard',
    port=8080,
    native=_native_available,
    reload=True,
    window_size=(1280, 800) if _native_available else None,
    fullscreen=False,
)
