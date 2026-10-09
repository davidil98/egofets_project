"""Helpers shared by the HDF5 tools. Not a tool itself (the registry skips it)."""

import re
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.readers.keithley_dean import list_measurements


def safe_stem(text: str) -> str:
    """Make a measurement or file name safe for the file system."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_") or "item"


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


def render_curve_figures(
    plot_func: Callable,
    hdf5_path: Path,
    measurements: list[str],
    output_dir: Path,
    stem: str,
    ncols: int = 3,
    **plot_kwargs,
) -> list[Path]:
    """Save one overview grid plus one image per measurement.

    The overview is what the dashboard shows as a thumbnail; the individual
    images are opened when the user expands it.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    individual_dir = output_dir / "curves"
    individual_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    n = len(measurements)
    nrows = (n + ncols - 1) // ncols
    grid, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)
    axes_flat = axes.ravel()

    for ax, name in zip(axes_flat, measurements):
        _draw_safely(plot_func, hdf5_path, name, ax, plot_kwargs)
    for ax in axes_flat[n:]:
        ax.set_visible(False)
    grid.tight_layout()
    grid_path = output_dir / f"{stem}_overview.png"
    grid.savefig(grid_path, dpi=120)
    plt.close(grid)
    paths.append(grid_path)

    for name in measurements:
        fig, ax = plt.subplots(figsize=(6, 4.5))
        _draw_safely(plot_func, hdf5_path, name, ax, plot_kwargs)
        fig.tight_layout()
        path = individual_dir / f"{stem}_{safe_stem(name)}.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        paths.append(path)

    return paths


def _draw_safely(plot_func, hdf5_path, name, ax, plot_kwargs) -> None:
    try:
        plot_func(hdf5_path, name, ax=ax, **plot_kwargs)
    except Exception as exc:  # noqa: BLE001 - shown inside the figure instead of aborting
        ax.text(0.5, 0.5, f"Error: {exc}", transform=ax.transAxes, ha="center", wrap=True)
        ax.set_title(name, fontsize=9)


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
