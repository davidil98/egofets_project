"""Dialog that applies a dashboard tool to an attached HDF5 reference.

The form is generated from each tool's parameter schema, so new tools appear here
without UI changes.
"""

from pathlib import Path
from typing import Callable

from nicegui import ui

from dashboard.tool_runs import run_tool_on_memory
from src.dashboard_tools import get_tool, list_tools
from src.dashboard_tools.base import ParameterSchema, Tool
from src.readers.keithley_dean import list_measurements


def show_tool_dialog(memory_id: int, ref_path: str, project_root: Path,
                     on_done: Callable[[], None]) -> None:
    """Open the dialog to run a tool on `ref_path`; `on_done` runs after a successful run."""
    tools = list_tools("hdf5")
    if not tools:
        ui.notify("No tools available for HDF5 files", color="negative")
        return

    source = Path(project_root) / ref_path
    readers: dict[str, Callable[[], object]] = {}

    with ui.dialog() as dlg, ui.card().classes("w-[640px] max-h-[90vh] overflow-auto"):
        ui.label("Apply tool").classes("text-xl font-bold")
        ui.label(ref_path).classes("font-mono text-xs text-gray-500 break-all")

        tool_select = ui.select(
            {tool.name: tool.display_name for tool in tools},
            value=tools[0].name,
            label="Tool",
        ).props("outlined dense").classes("w-full")
        tool_help = ui.label().classes("text-sm text-gray-600")
        form = ui.column().classes("w-full gap-3")

        def render_form() -> None:
            tool = get_tool(tool_select.value)
            tool_help.text = tool.description
            form.clear()
            readers.clear()
            with form:
                try:
                    names = _measurement_names(source, tool)
                except Exception as exc:
                    ui.label(f"Cannot read the file: {exc}").classes("text-red-600 text-sm")
                    return
                for parameter in tool.parameters:
                    readers[parameter.name] = _build_widget(parameter, names)

        def run() -> None:
            tool = get_tool(tool_select.value)
            params = {name: read() for name, read in readers.items()}
            try:
                analysis_id = run_tool_on_memory(memory_id, ref_path, tool.name, params)
            except Exception as exc:
                ui.notify(f"{tool.display_name} failed: {exc}", color="negative", multi_line=True, timeout=8000)
                return
            dlg.close()
            ui.notify(f"{tool.display_name} finished (analysis {analysis_id})", color="positive")
            on_done()

        tool_select.on_value_change(lambda _: render_form())
        render_form()

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dlg.close).props("flat")
            ui.button("Run", icon="play_arrow", on_click=run).props("color=primary")

    dlg.open()


def _measurement_names(source: Path, tool: Tool) -> list[str]:
    """Names of the measurements of the mode this tool works on."""
    if tool.measurement_mode is None:
        return []
    return [m["name"] for m in list_measurements(source) if m["mode"] == tool.measurement_mode]


def _build_widget(parameter: ParameterSchema, measurement_names: list[str]) -> Callable[[], object]:
    """Create the input for one parameter and return a function that reads its value."""
    kind = parameter.type
    default = parameter.default

    if kind == "float_pair":
        low = ui.number(f"{parameter.label} — min", value=default[0], format="%.3f").props("outlined dense")
        high = ui.number(f"{parameter.label} — max", value=default[1], format="%.3f").props("outlined dense")
        _help(parameter)
        return lambda: (low.value, high.value)

    if kind in ("float", "int"):
        fmt = "%.3f" if kind == "float" else "%.0f"
        widget = ui.number(parameter.label, value=default, format=fmt).props("outlined dense").classes("w-full")
        _help(parameter)
        return lambda: widget.value

    if kind == "bool":
        widget = ui.switch(parameter.label, value=default)
        _help(parameter)
        return lambda: widget.value

    if kind == "str":
        widget = ui.input(parameter.label, value=default).props("outlined dense").classes("w-full")
        _help(parameter)
        return lambda: widget.value

    if kind == "choice":
        widget = ui.select(list(parameter.choices), value=default, label=parameter.label).props(
            "outlined dense"
        ).classes("w-full")
        _help(parameter)
        return lambda: widget.value

    if kind == "measurements":
        ui.label(parameter.label).classes("text-sm font-medium text-gray-700")
        if not measurement_names:
            ui.label("No measurements of this kind in the file").classes("text-sm text-red-600")
            return lambda: []
        hint = parameter.help or "Nothing selected means all measurements."
        ui.label(hint).classes("text-xs text-gray-500")
        with ui.scroll_area().classes("w-full h-44 border rounded p-2"):
            boxes = {name: ui.checkbox(name, value=False) for name in measurement_names}
        return lambda: [name for name, box in boxes.items() if box.value]

    raise ValueError(f"Unsupported parameter type {kind!r}")


def _help(parameter: ParameterSchema) -> None:
    if parameter.help:
        ui.label(parameter.help).classes("text-xs text-gray-500 -mt-2")
