"""Plot transfer curves interactively with plotly. Select measurements to plot all in one figure."""

from pathlib import Path

from ._common import plot_transfer_plotly, render_plotly_curves, resolve_measurements
from .base import ParameterSchema, Tool, ToolResult


class TransferPlotCombinedTool(Tool):
    name = "transfer_plot_combined"
    display_name = "Plot transfer curves (combined)"
    description = "I_DS vs V_GS for all transfer measurements in one figure, with optional reverse sweep."
    input_ref_type = "hdf5"
    measurement_mode = "transfer"
    parameters = (
        ParameterSchema(
            "measurements", "Transfer measurements", "measurements", (),
            help="Empty means every transfer measurement in the file.",
        ),
        ParameterSchema(
            "loop", "Show reverse sweep", "bool", True,
            help="Draw the return sweep dashed when the curve has hysteresis.",
        ),
    )

    def run(self, ref_path: Path, params: dict, workdir: Path) -> ToolResult:
        p = self.coerce(params)
        ref_path = Path(ref_path)
        names = resolve_measurements(ref_path, p["measurements"], "transfer")

        figures = render_plotly_curves(plot_transfer_plotly, ref_path, names, loop=p["loop"], combined=True)

        return ToolResult(
            figures=figures,
            summary={"measurements": names, "n_measurements": len(names), "loop": p["loop"]},
            description=f"Transfer curves plotted for {len(names)} measurements",
        )