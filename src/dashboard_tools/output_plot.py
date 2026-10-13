"""Plot output curves interactively with plotly."""

from pathlib import Path

from ._common import plot_output_plotly, render_plotly_curves, resolve_measurements
from .base import ParameterSchema, Tool, ToolResult


class OutputPlotTool(Tool):
    name = "output_plot"
    display_name = "Plot output curves"
    description = "I_DS vs V_DS for each output measurement, one curve per V_GS."
    input_ref_type = "hdf5"
    measurement_mode = "output"
    parameters = (
        ParameterSchema(
            "measurements", "Output measurements", "measurements", (),
            help="Empty means every output measurement in the file.",
        ),
    )

    def run(self, ref_path: Path, params: dict, output_dir: Path) -> ToolResult:
        p = self.coerce(params)
        ref_path = Path(ref_path)
        names = resolve_measurements(ref_path, p["measurements"], "output")

        figures = render_plotly_curves(plot_output_plotly, ref_path, names)

        return ToolResult(
            plotly_figures=figures,
            summary={"measurements": names, "n_measurements": len(names)},
            description=f"Output curves plotted for {len(names)} measurements",
        )
