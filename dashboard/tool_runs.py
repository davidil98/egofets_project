"""Apply a dashboard tool to an attached file and manage the resulting tool run.

Applying a tool executes it once and stores everything in the database: the run
(recipe + summary) and its items (interactive figure specs, tables). Re-applying
the same tool on the same reference replaces the previous run. Removing a run
deletes it and its items in cascade. Nothing is written to disk, except a
throwaway workdir that tools may use for scratch files.
"""

import json
import tempfile
from pathlib import Path

from src import db
from src.dashboard_tools import get_tool

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def apply_tool(memory_id: int, ref_path: str, tool_name: str, params: dict) -> int:
    """Run a tool on `ref_path` and store the result as a tool run.

    Replaces any previous run of the same tool on the same reference.
    Returns the new run id; raises ValueError/FileNotFoundError on invalid input.
    """
    tool = get_tool(tool_name)
    if tool is None:
        raise ValueError(f"Unknown tool {tool_name!r}")
    if db.get_memory(memory_id) is None:
        raise ValueError(f"Memory {memory_id} not found")

    source = (PROJECT_ROOT / ref_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"File not found: {ref_path}")

    clean = tool.coerce(params)
    with tempfile.TemporaryDirectory() as tmp:
        result = tool.run(source, clean, Path(tmp))

    db.delete_tool_runs_for(memory_id, ref_path, tool_name)
    run_id = db.create_tool_run(
        memory_id, ref_path, tool_name, clean, result.summary, result.description
    )

    position = 0
    for figure in result.figures:
        title = (figure.layout.title.text or f"Figure {position + 1}") if figure.layout.title else f"Figure {position + 1}"
        db.add_tool_run_item(run_id, "figure", position, title, json.loads(figure.to_json()))
        position += 1
    for table in result.tables:
        db.add_tool_run_item(run_id, "table", position, table.label, {"records": table.records})
        position += 1

    return run_id


def remove_tool_run(run_id: int) -> dict | None:
    """Delete a run and return what was removed (for a summary notification)."""
    run = db.get_tool_run(run_id)
    if run is None:
        return None
    db.delete_tool_run(run_id)
    return run


def rerun_tool_run(run_id: int) -> int | None:
    """Re-apply a run using its stored parameters (replaces it).

    Returns the new run id, or None if the original run no longer exists.
    """
    run = db.get_tool_run(run_id)
    if run is None:
        return None
    params = json.loads(run.get("params_json") or "{}")
    return apply_tool(run["memory_id"], run["ref_path"], run["tool_name"], params)


def summarize_run(run: dict) -> str:
    """One-line description of a run and what it produced."""
    items = run.get("items", [])
    figures = sum(1 for i in items if i.get("kind") == "figure")
    tables = sum(1 for i in items if i.get("kind") == "table")
    counts = []
    if figures:
        counts.append(f"{figures} figura(s)")
    if tables:
        counts.append(f"{tables} tabla(s)")
    detail = ", ".join(counts) if counts else "sin resultados"
    name = run.get("tool_name", "tool")
    description = run.get("description") or ""
    return f"{name}: {description} ({detail})" if description else f"{name} ({detail})"
