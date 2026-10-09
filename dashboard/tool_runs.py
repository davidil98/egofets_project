"""Run a dashboard tool on an attached file and record what it produced.

A run creates one analysis result (function_name = tool name, parameters, summary
and the CSV table, if any) and one 'figure' reference per generated image. Each
figure reference carries the analysis id and its role in metadata_json, so the
Figures card can group the images of a run.
"""

import os
from datetime import datetime
from pathlib import Path

from src import db
from src.dashboard_tools import get_tool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "data" / "processed"


def _relative(path: Path) -> str:
    return os.path.relpath(Path(path).resolve(), PROJECT_ROOT)


def run_tool_on_memory(memory_id: int, ref_path: str, tool_name: str, params: dict) -> int:
    """Run `tool_name` on the file `ref_path` (relative to the project) and record the results.

    Returns the id of the analysis result that was created.
    Raises ValueError with a message suitable for the user on invalid input.
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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_ROOT / f"memory_{memory_id}" / f"{tool.name}_{stamp}"
    result = tool.run(source, clean, output_dir)

    table_path = _relative(result.tables[0]) if result.tables else None
    analysis_id = db.save_analysis_result(
        memory_id=memory_id,
        function_name=tool.name,
        params={
            "params": clean,
            "summary": result.summary,
            "description": result.description,
            "source": ref_path,
        },
        results_csv_path=table_path,
    )

    roles = result.figure_roles or ["figure"] * len(result.figures)
    for figure, role in zip(result.figures, roles):
        db.add_reference(
            memory_id,
            "figure",
            _relative(figure),
            {"analysis_id": analysis_id, "tool": tool.name, "role": role},
        )

    return analysis_id
