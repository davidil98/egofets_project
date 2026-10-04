"""Home page — memory list with filters."""

from nicegui import ui
from src import db


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


def render_home(on_open_memory, on_create_memory):
    """Render the home page with memory list and filters."""

    with ui.column().classes("w-full gap-4"):
        ui.label("Memories").classes("text-3xl font-bold")

        _render_filter_bar(on_create_memory, on_open_memory)


def _render_filter_bar(on_create_memory, on_open_memory):
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-end gap-3 flex-wrap"):
            search_input = ui.input("Search").props("outlined dense").classes("min-w-48")
            type_select = ui.select(
                {"all": "All types", "experiment": "Experiment", "comparison": "Comparison"},
                value="all",
                label="Type",
            ).props("outlined dense").classes("w-36")
            subtype_select = ui.select(
                {"all": "All subtypes", "device": "Device", "batch": "Batch",
                 "wafer": "Wafer", "session": "Session"},
                value="all",
                label="Subtype",
            ).props("outlined dense").classes("w-36")
            substrate_select = ui.select(
                {"all": "All substrates", "Kapton": "Kapton", "Si/SiO2": "Si/SiO2",
                 "Glass": "Glass"},
                value="all",
                label="Substrate",
            ).props("outlined dense").classes("w-36")

            ui.space()
            ui.button("New Memory", icon="add", on_click=on_create_memory).props("color=primary")

    list_container = ui.column().classes("w-full gap-2")

    def refresh():
        list_container.clear()
        search = search_input.value or None
        mtype = type_select.value if type_select.value != "all" else None
        subtype = subtype_select.value if subtype_select.value != "all" else None
        substrate = substrate_select.value if substrate_select.value != "all" else None

        memories = db.list_memories(
            type=mtype, subtype=subtype, substrate=substrate, search=search
        )

        with list_container:
            if not memories:
                ui.label("No memories found").classes("text-gray-400 italic p-8")
            else:
                for memory in memories:
                    _render_memory_card(memory, on_open_memory)

    search_input.on_value_change(lambda _: refresh())
    type_select.on_value_change(lambda _: refresh())
    subtype_select.on_value_change(lambda _: refresh())
    substrate_select.on_value_change(lambda _: refresh())
    refresh()


def _render_memory_card(memory: dict, on_open_memory):
    memory_id = memory["id"]
    mtype = memory["type"]
    subtype = memory.get("subtype") or ""
    color = TYPE_COLORS.get(mtype, "gray")
    icon = SUBTYPE_ICONS.get(subtype, "folder")

    with ui.card().classes("w-full cursor-pointer hover:shadow-md transition-shadow") as card:
        card.on("click", lambda _, mid=memory_id: on_open_memory(mid))

        with ui.row().classes("w-full items-center gap-3 p-2"):
            ui.icon(icon).classes(f"text-{color}-500 text-2xl")
            with ui.column().classes("flex-1 gap-0"):
                ui.label(memory["title"]).classes("text-lg font-semibold")
                with ui.row().classes("gap-2 items-center"):
                    ui.badge(mtype).props(f"color={color} outline")
                    if subtype:
                        ui.badge(subtype).props("color=gray outline")
                    ui.label(memory.get("date", "")).classes("text-xs text-gray-500")
                    if memory.get("substrate"):
                        ui.label(f"{memory['substrate']}").classes("text-xs text-gray-500")
            ui.icon("chevron_right").classes("text-gray-400")
