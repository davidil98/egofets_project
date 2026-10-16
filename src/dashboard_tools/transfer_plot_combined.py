"""Plot transfer curves combined: all selected measurements in one subplot grid."""

from pathlib import Path

from ._common import grid_figure, plot_transfer_plotly, render_plotly_curves, resolve_measurements
from .base import ParameterSchema, Tool, ToolResult


class TransferPlotCombinedTool(Tool):
    name = "transfer_plot_combined"
    display_name = "Plot transfer curves (combined)"
    description = "I_DS vs V_GS for all selected transfer measurements in a single subplot grid."
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
        ParameterSchema(
            "ncols", "Grid columns", "int", 3,
            help="Number of columns in the combined figure.",
        ),
    )

    def run(self, ref_path: Path, params: dict, workdir: Path) -> ToolResult:
        p = self.coerce(params)
        ref_path = Path(ref_path)
        names = resolve_measurements(ref_path, p["measurements"], "transfer")

        figures = render_plotly_curves(plot_transfer_plotly, ref_path, names, loop=p["loop"])
        combined = grid_figure(figures, titles=names, ncols=p["ncols"])

        return ToolResult(
            figures=[combined],
            summary={"measurements": names, "n_measurements": len(names), "ncols": p["ncols"]},
            description=f"Combined {len(names)} transfer curves into a grid ({p['ncols']} cols)",
        )
