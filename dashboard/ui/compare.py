"""Compare page — placeholder for multi-memory comparison."""

from nicegui import ui


def render_compare(on_back):
    """Render the compare page (placeholder)."""
    with ui.column().classes("w-full gap-4 items-center justify-center"):
        ui.button("Back", icon="arrow_back", on_click=on_back).props("flat")
        ui.icon("compare_arrows").classes("text-6xl text-gray-300")
        ui.label("Compare View").classes("text-2xl font-bold text-gray-500")
        ui.label("Select multiple memories to compare their results side by side or overlaid.").classes(
            "text-gray-400 text-center max-w-md"
        )
        ui.label("Coming soon").classes("text-gray-300 italic mt-4")
