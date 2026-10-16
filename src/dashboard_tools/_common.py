"""Helpers shared by the HDF5 tools. Not a tool itself (the registry skips it)."""

import re
from pathlib import Path
from typing import Callable

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.readers.keithley_dean import list_measurements, read_all_curves, _has_hysteresis


def safe_stem(text: str) -> str:
    """Make a measurement or file name safe for the file system."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "item"


def records_of(df) -> list[dict]:
    """Turn a DataFrame into JSON-safe row dicts (native scalars, NaN -> None)."""
    out = []
    for record in df.to_dict("records"):
        clean = {}
        for key, value in record.items():
            if isinstance(value, float) and value != value:  # NaN
                clean[key] = None
            elif hasattr(value, "item"):  # numpy scalar
                clean[key] = value.item()
            else:
                clean[key] = value
        out.append(clean)
    return out


def resolve_measurements(hdf5_path: Path, requested: list[str], mode: str) -> list[str]:
    """Return the measurements of a given mode, checking any explicit selection.

    An empty request means every measurement of that mode in the file.
    """
    available = [m["name"] for m in list_measurements(hdf5_path) if m["mode"] == mode]
    if not available:
        raise ValueError(f"No {mode} measurements in {Path(hdf5_path).name}")
    if not requested:
        return available

    unknown = [name for name in requested if name not in available]
    if unknown:
        raise ValueError(f"Measurements not found in {Path(hdf5_path).name}: {unknown}")
    return [name for name in available if name in requested]


def plot_transfer_plotly(hdf5_path: Path, measurement_name: str, loop: bool = True) -> go.Figure:
    """Return a plotly figure with all transfer curves for one measurement."""
    fig = go.Figure()
    curves = read_all_curves(hdf5_path, measurement_name)

    for i, c in enumerate(curves):
        v_gs = c["v_gs"]
        i_ds = c["i_ds"]
        v_ds = c["v_ds"]
        curve_name = c["curve_name"]
        curve_idx = curve_name.split("_")[-1]
        label = f"{float(v_ds[0]):.2f} V (#{curve_idx})"

        split = _has_hysteresis(v_gs)

        if loop and split is not None:
            # Forward: línea sólida
            fig.add_trace(go.Scatter(
                x=v_gs[:split + 1],
                y=i_ds[:split + 1],
                mode="lines+markers",
                marker=dict(size=3),
                line=dict(width=1.5),
                name=label,
                legendgroup=label,
                showlegend=True,
            ))
            # Reverse: línea discontinua
            fig.add_trace(go.Scatter(
                x=v_gs[split + 1:],
                y=i_ds[split + 1:],
                mode="lines+markers",
                marker=dict(size=3),
                line=dict(width=1.5, dash="dash"),
                name=f"{label} (rev)",
                legendgroup=label,
                showlegend=False,
                hoverinfo="skip",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=v_gs,
                y=i_ds,
                mode="lines+markers",
                marker=dict(size=3),
                line=dict(width=1.5),
                name=label,
                legendgroup=label,
            ))

    fig.update_layout(
        title=f"Transfer — {measurement_name}",
        xaxis_title="V_GS (V)",
        yaxis_title="I_DS (A)",
        legend=dict(font=dict(size=8), itemsizing="constant"),
        hovermode="closest",
        height=500,
    )
    return fig


def plot_output_plotly(hdf5_path: Path, measurement_name: str) -> go.Figure:
    """Return a plotly figure with all output curves for one measurement."""
    fig = go.Figure()
    curves = read_all_curves(hdf5_path, measurement_name)

    for i, c in enumerate(curves):
        v_gs = c["v_gs"]
        i_ds = c["i_ds"]
        v_ds = c["v_ds"]
        curve_name = c["curve_name"]
        curve_idx = curve_name.split("_")[-1]
        label = f"{float(v_gs[0]):.2f} V (#{curve_idx})"

        fig.add_trace(go.Scatter(
            x=v_ds,
            y=i_ds,
            mode="lines+markers",
            marker=dict(size=3),
            line=dict(width=1.5),
            name=label,
            legendgroup=label,
        ))

    fig.update_layout(
        title=f"Output — {measurement_name}",
        xaxis_title="V_DS (V)",
        yaxis_title="I_DS (A)",
        legend=dict(font=dict(size=8), itemsizing="constant"),
        hovermode="closest",
        height=500,
    )
    return fig


def render_plotly_curves(
    plot_func: Callable,
    hdf5_path: Path,
    measurements: list[str],
    **plot_kwargs,
) -> list[go.Figure]:
    """Return a list of plotly figures: one per measurement.

    Each figure is fully interactive (hover, legend toggle, zoom, pan).
    """
    figures = []
    for name in measurements:
        try:
            fig = plot_func(hdf5_path, name, **plot_kwargs)
            figures.append(fig)
        except Exception as exc:
            # Figura de error en lugar de abortar
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {exc}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="red"),
            )
            fig.update_layout(title=name, height=400)
            figures.append(fig)
    return figures


def grid_figure(
    figures: list[go.Figure],
    titles: list[str] | None = None,
    ncols: int = 3,
    row_height: int = 320,
    showlegend: bool = False,
) -> go.Figure:
    """Merge a list of plotly figures into a single subplot grid.

    Figures with no traces (e.g. an error placeholder) render their annotation
    text inside the corresponding cell instead of leaving it empty.
    """
    n = len(figures)
    if n == 0:
        raise ValueError("No figures to combine")
    ncols = max(1, int(ncols))
    nrows = (n + ncols - 1) // ncols

    x_title = figures[0].layout.xaxis.title.text or ""
    y_title = figures[0].layout.yaxis.title.text or ""

    fig = make_subplots(
        rows=nrows,
        cols=ncols,
        subplot_titles=titles or [f"Fig {i + 1}" for i in range(n)],
        horizontal_spacing=0.06,
        vertical_spacing=0.06,
    )

    for i, source in enumerate(figures):
        row, col = divmod(i, ncols)
        if source.data:
            for trace in source.data:
                fig.add_trace(trace, row=row + 1, col=col + 1)
        else:
            text = source.layout.annotations[0].text if source.layout.annotations else "No data"
            idx = i + 1
            xref = "x domain" if idx == 1 else f"x{idx} domain"
            yref = "y domain" if idx == 1 else f"y{idx} domain"
            fig.add_annotation(text=text, x=0.5, y=0.5, xref=xref, yref=yref,
                               showarrow=False, font=dict(color="red"))

    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text=y_title)
    fig.update_layout(
        height=row_height * nrows,
        showlegend=showlegend,
        margin=dict(l=60, r=20, t=40, b=40),
    )
    return fig


def stats_of(values: np.ndarray) -> dict:
    """Mean, std, median, IQR, min and max (NaN ignored) as plain floats.

    Median and IQR are included because a single outlier can dominate mean and std.
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"mean": None, "std": None, "median": None, "iqr": None, "min": None, "max": None}
    q1, q3 = np.percentile(values, [25, 75])
    return {
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "median": float(np.median(values)),
        "iqr": float(q3 - q1),
        "min": float(values.min()),
        "max": float(values.max()),
    }
