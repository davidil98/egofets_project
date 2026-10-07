from nicegui import ui

from dashboard.components.pagemanager import pagemanager


def create_menu():
    grouped_pages = {}
    for route, page_info in pagemanager.get_pages().items():
        folder = page_info.folder
        if folder not in grouped_pages:
            grouped_pages[folder] = []
        grouped_pages[folder].append((route, page_info))

    menu_html = '<div class="menu-container">'

    for folder, pages in grouped_pages.items():
        if folder != 'pages_root':
            menu_html += f'''
                <div class="dropdown-container">
                    <button class="dropdown-button">{folder.title()}/</button>
                    <div class="dropdown-content">
            '''

            for route, page_info in pages:
                menu_html += f'''
                    <a href="{page_info.route}" class="dropdown-link">
                        {page_info.display}
                    </a>
                '''

            menu_html += '''
                    </div>
                </div>
            '''

    if 'pages_root' in grouped_pages:
        for route, page_info in grouped_pages['pages_root']:
            menu_html += f'''
                <button class="dropdown-button"><a href="{page_info.route}" class="menu-link">
                    {page_info.display}
                </a></button>
            '''

    menu_html += '</div>'

    return menu_html


def reload_modules():
    try:
        pagemanager._scan_pages()
        ui.notify('Pages reloaded', type='positive')
    except Exception as e:
        ui.notify(f'Error reloading: {e}', type='negative')
    finally:
        ui.navigate.reload()
