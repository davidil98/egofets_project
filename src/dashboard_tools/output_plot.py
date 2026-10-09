"""Plot output curves: an overview grid plus one image per measurement."""

from pathlib import Path

from src.plotting import plot_output

from ._common import render_curve_figures, resolve_measurements, safe_stem
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

        figures = render_curve_figures(
            plot_output, ref_path, names, output_dir,
            stem=f"output_{safe_stem(ref_path.stem)}",
        )
        return ToolResult(
            figures=figures,
            figure_roles=["overview"] + ["curve"] * (len(figures) - 1),
            summary={"measurements": names, "n_measurements": len(names)},
            description=f"Output curves plotted for {len(names)} measurements",
        )
