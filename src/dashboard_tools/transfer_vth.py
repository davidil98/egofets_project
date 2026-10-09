"""Extract V_th from transfer curves (sqrt(|I_DS|) linear fit, global window search)."""

from pathlib import Path

import matplotlib.pyplot as plt

from src.analysis import extract_vth_for_transfers

from ._common import resolve_measurements, safe_stem, stats_of
from .base import ParameterSchema, Tool, ToolResult


class TransferVthTool(Tool):
    name = "transfer_vth"
    display_name = "Extract V_th from transfers"
    description = (
        "Linear fit of sqrt(|I_DS|) vs V_GS on the saturation curve of each transfer. "
        "V_th = -intercept / slope, with the fit window chosen to maximise R^2."
    )
    input_ref_type = "hdf5"
    measurement_mode = "transfer"
    parameters = (
        ParameterSchema(
            "measurements", "Transfer measurements", "measurements", (),
            help="Empty means every transfer measurement in the file.",
        ),
        ParameterSchema(
            "v_min_range", "v_min search range (V)", "float_pair", (-0.40, -0.38),
            help="Lower and upper bound of the window start.",
        ),
        ParameterSchema(
            "v_max_range", "v_max search range (V)", "float_pair", (-0.06, 0.00),
            help="Lower and upper bound of the window end.",
        ),
    )

    def run(self, ref_path: Path, params: dict, output_dir: Path) -> ToolResult:
        p = self.coerce(params)
        ref_path = Path(ref_path)
        names = resolve_measurements(ref_path, p["measurements"], "transfer")

        df = extract_vth_for_transfers(
            ref_path, names, v_min_range=p["v_min_range"], v_max_range=p["v_max_range"],
        )
        if df.empty:
            raise ValueError("No V_th could be extracted from the selected transfers")

        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"vth_{safe_stem(ref_path.stem)}"
        table_path = output_dir / f"{stem}.csv"
        df.to_csv(table_path, index=False)

        figure_path = output_dir / f"{stem}_bars.png"
        fig, ax = plt.subplots(figsize=(max(6, 0.4 * len(df)), 4.5))
        ax.bar(range(len(df)), df["V_th (V)"], color="steelblue")
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df["measurement"], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("V_th (V)")
        ax.set_title(f"V_th — {ref_path.stem}")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(figure_path, dpi=120)
        plt.close(fig)

        vth_stats = stats_of(df["V_th (V)"].to_numpy())
        summary = {
            "measurements": list(df["measurement"]),
            "n_measurements": len(df),
            "v_min_range": list(p["v_min_range"]),
            "v_max_range": list(p["v_max_range"]),
            "V_th (V)": vth_stats,
            "R^2_min": float(df["R^2"].min()),
        }
        description = (
            f"V_th for {len(df)} transfer curves: median {vth_stats['median']:.3f} V, "
            f"IQR {vth_stats['iqr']:.3f} V"
        )
        return ToolResult(
            figures=[figure_path],
            figure_roles=["overview"],
            tables=[table_path],
            summary=summary,
            description=description,
        )
