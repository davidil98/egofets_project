from pathlib import Path
from nicegui import ui
from typing import Callable
import yaml

PAGECONF_FILENAME = Path(__file__).parent.parent / "pageconf.yaml"

PAGECONF_DEFAULT = {
    "sidebar_width": 350,
    "sidebar_height": 500,
    "cards_per_row": 3,
    "card_height": 450,
}


class GlobalPageConf:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.initialize_pageconf()
        self._conf = self._load_pageconf()
        self._conf_default = self._conf.get("default", PAGECONF_DEFAULT)

    def _load_pageconf(self):
        if not PAGECONF_FILENAME.exists():
            return {"default": PAGECONF_DEFAULT}
        with open(PAGECONF_FILENAME, "r") as f:
            return yaml.safe_load(f) or {"default": PAGECONF_DEFAULT}

    def _save_pageconf(self):
        with open(PAGECONF_FILENAME, "w") as f:
            yaml.dump(self._conf, f, default_flow_style=False)

    def show_notification(self, message: str, type: str = 'positive', duration: int = 5000):
        ui.notify(
            message,
            position='bottom-right',
            type=type,
            close_button='Dismiss',
            timeout=duration,
        )

    def initialize_pageconf(self):
        if not PAGECONF_FILENAME.exists():
            default_conf = {"default": PAGECONF_DEFAULT}
            with open(PAGECONF_FILENAME, "w") as f:
                yaml.dump(default_conf, f, default_flow_style=False)

    def load(self, route):
        return self._conf.get(route, self._conf_default)

    def save(self, route, yaml_str):
        try:
            if not yaml_str.strip():
                self.delete(route)
            else:
                conf = yaml.safe_load(yaml_str)
                self._conf[route] = conf
                self._save_pageconf()
        except Exception as e:
            self.show_notification(f"Error saving config: {e}", 'negative', 8000)
            raise

    def delete(self, route):
        if route in self._conf:
            del self._conf[route]
            self._save_pageconf()

    def get(self, route, key):
        conf = self.load(route)
        value = conf.get(key, self._conf_default.get(key))
        if value is None:
            raise KeyError(f"Setting '{key}' for '{route}' is None")
        return value

    def to_yaml(self, route):
        return yaml.dump(self.load(route), default_flow_style=False)

    def open_settings_dialog(self, pageinfo, on_save: Callable = None):
        with ui.dialog() as dialog, ui.card().style('min-width: 800px; max-width: 800px; height: 500px;'):
            with ui.column().classes('w-full').style('height: 100%; display: flex; flex-direction: column;'):
                with ui.row().classes('w-full').style('flex: 1; gap: 2rem; padding: 1.5rem; overflow: hidden;'):
                    with ui.column().style('flex: 0 0 auto; padding-top: 0.5rem;'):
                        ui.label('PageInfo').classes('text-subtitle text-weight-medium')
                        with ui.grid(columns=2).style('display: grid; grid-template-columns: auto 1fr; margin-top: 1rem;'):
                            for key, value in vars(pageinfo).items():
                                ui.label(f"{key}:").classes('text-grey-5 text-left whitespace-nowrap')
                                ui.label(f"{value}").classes('text-white')

                    with ui.column().style('flex: 1 1 0; padding-top: 0.5rem; height: 100%; overflow: hidden;'):
                        ui.label('YAML Configuration').classes('text-subtitle text-weight-medium')
                        yaml_content = self.to_yaml(pageinfo.route)

                        editor = ui.textarea(value=yaml_content).classes('w-full').style('''
                            margin-top: 0;
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 4px;
                            height: calc(100% - 2rem);
                            overflow-y: auto;
                            font-family: monospace;
                        ''')

                with ui.row().classes('w-full justify-center'):
                    ui.button('SAVE', on_click=lambda: save_and_close(), color='primary').props('icon-right="save"').classes('w-48')

        def save_and_close():
            try:
                self.save(pageinfo.route, editor.value)
                self.show_notification('Configuration saved', 'positive')
                if on_save:
                    on_save()
                dialog.close()
            except Exception as e:
                self.show_notification(f'Error: {e}', 'negative', 8000)

        dialog.open()


globalpageconf = GlobalPageConf()
