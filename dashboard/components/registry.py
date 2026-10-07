from typing import Dict


class Registry:
    _pages = {}
    _menu = None

    @classmethod
    def clear(cls):
        cls._pages = {}
        cls._menu = None

    @classmethod
    def set_pages(cls, pages):
        cls._pages = pages

    @classmethod
    def get_pages(cls):
        return cls._pages

    @classmethod
    def set_menu(cls, menu):
        cls._menu = menu

    @classmethod
    def get_menu(cls):
        return cls._menu
