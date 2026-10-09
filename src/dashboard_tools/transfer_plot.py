"""Plot transfer curves: an overview grid plus one image per measurement."""

from pathlib import Path

from src.plotting import plot_transfer

from ._common import render_curve_figures, resolve_measurements, safe_stem
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

        figures = render_curve_figures(
            plot_transfer, ref_path, names, output_dir,
            stem=f"transfer_{safe_stem(ref_path.stem)}", loop=p["loop"],
        )
        return ToolResult(
            figures=figures,
            figure_roles=["overview"] + ["curve"] * (len(figures) - 1),
            summary={"measurements": names, "n_measurements": len(names), "loop": p["loop"]},
            description=f"Transfer curves plotted for {len(names)} measurements",
        )
