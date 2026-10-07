import os
from pathlib import Path
from typing import Dict

from dashboard.components.pageinfo import PageInfo
from dashboard.components.registry import Registry

CURRENT_DIR = Path(__file__).parent.parent
PAGES = "pages"


class PageManager:
    def __init__(self):
        self.pages_dir = CURRENT_DIR / PAGES
        Registry.clear()

    def _create_page_info(self, route: str, modulepath: str) -> PageInfo:
        classname = modulepath.split('.')[-1].replace('_page', '').title().replace('_', '') + 'Page'
        display = modulepath.split('.')[-1].replace('_page', '').replace('_', ' ').title()

        return PageInfo(
            route=route,
            modulepath=modulepath,
            classname=classname,
            display=display
        )

    def _scan_pages(self) -> Dict[str, PageInfo]:
        pages = {}
        priority_folders = ['memories']

        for root, dirs, files in os.walk(self.pages_dir):
            relative_path = Path(root).relative_to(self.pages_dir)

            for file in files:
                if not file.endswith('.py') or file.startswith('_'):
                    continue

                file_path = Path(root) / file
                modulename = file_path.stem
                modulepath = str(file_path.relative_to(CURRENT_DIR.parent)).replace(os.sep, '.').replace('.py', '')

                base_name = modulename.replace('_page', '')
                if str(relative_path) == '.':
                    route = f"/{base_name}"
                else:
                    route = f"/{relative_path}/{base_name}"

                pages[route] = self._create_page_info(route, modulepath)

        return dict(
            sorted(pages.items(), key=lambda x: (
                x[1].folder not in priority_folders,
                x[1].folder == 'pages_root',
                x[1].folder,
                x[0]
            ))
        )

    def get_pages(self):
        pages = Registry.get_pages()
        if not pages:
            Registry.set_pages(self._scan_pages())
            pages = Registry.get_pages()

        return pages


pagemanager = PageManager()
