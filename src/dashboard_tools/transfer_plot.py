"""Plot transfer curves interactively with plotly."""

from pathlib import Path

from ._common import plot_transfer_plotly, render_plotly_curves, resolve_measurements
from .base import ParameterSchema, Tool, ToolResult


class TransferPlotTool(Tool):
    name = "transfer_plot"
    display_name = "Plot transfer curves"
    description = "I_DS vs V_GS for each transfer measurement, with optional reverse sweep."
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

    def run(self, ref_path: Path, params: dict, output_dir: Path) -> ToolResult:
        p = self.coerce(params)
        ref_path = Path(ref_path)
        names = resolve_measurements(ref_path, p["measurements"], "transfer")

        figures = render_plotly_curves(
            plot_transfer_plotly, ref_path, names, loop=p["loop"],
        )

        return ToolResult(
            plotly_figures=figures,
            summary={"measurements": names, "n_measurements": len(names), "loop": p["loop"]},
            description=f"Transfer curves plotted for {len(names)} measurements",
        )
