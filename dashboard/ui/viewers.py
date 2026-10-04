"""Figure and photo viewer components."""

from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nicegui import ui


def create_csv_viewer(csv_path: Path):
    """Render a CSV file as a plotly chart + data table."""
    if not csv_path.exists():
        ui.label(f"File not found: {csv_path.name}").classes("text-red-500 text-sm")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        ui.label(f"Error loading CSV: {e}").classes("text-red-500 text-sm")
        return

    if "V_th (V)" in df.columns and "measurement" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["measurement"],
            y=df["V_th (V)"],
            marker_color="steelblue",
        ))
        fig.update_layout(
            title=f"V_th — {csv_path.stem}",
            xaxis_title="Measurement",
            yaxis_title="V_th (V)",
            xaxis_tickangle=-45,
            height=350,
            margin=dict(l=40, r=20, t=40, b=100),
        )
        ui.plotly(fig).classes("w-full")
    else:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if len(numeric_cols) >= 2:
            fig = px.line(df, x=numeric_cols[0], y=numeric_cols[1:], title=csv_path.stem)
            fig.update_layout(height=350)
            ui.plotly(fig).classes("w-full")
        else:
            ui.label(f"CSV: {csv_path.stem} ({len(df)} rows)").classes("text-sm text-gray-600")

    with ui.expansion("Show data table").classes("w-full mt-1"):
        ui.table(
            columns=[{"name": col, "label": col, "field": col} for col in df.columns],
            rows=df.to_dict("records"),
        ).classes("w-full").props("dense flat")


def create_photo_viewer(photo_path: Path):
    """Render a photo thumbnail with click-to-zoom."""
    if not photo_path.exists():
        ui.label(f"Photo not found: {photo_path.name}").classes("text-red-500 text-sm")
        return

    ui.image(photo_path.as_posix()).classes(
        "w-40 h-40 object-cover rounded cursor-pointer hover:opacity-90 transition-opacity"
    ).on("click", lambda: _show_zoom_dialog(photo_path))


def _show_zoom_dialog(img_path: Path):
    with ui.dialog() as dlg, ui.card().classes("w-[80vw] h-[80vh]"):
        ui.image(img_path.as_posix()).classes("w-full h-full object-contain")
    dlg.open()
