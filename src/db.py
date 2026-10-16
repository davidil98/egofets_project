"""SQLite database layer for EGOFET memory system.

Location: data/memories.db
Schema: src/schema.yaml
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "memories.db"
SCHEMA_PATH = PROJECT_ROOT / "src" / "schema.yaml"


def _load_schema() -> dict:
    """Load schema definition from YAML."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_db():
    """Initialize database with schema from schema.yaml."""
    schema = _load_schema()
    
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with _conn() as conn:
        # WAL lets readers and writers coexist and makes small writes much cheaper.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")

        # Create tables
        for table_name, table_def in schema["tables"].items():
            columns = []
            for col_name, col_type in table_def["columns"].items():
                columns.append(f"{col_name} {col_type}")
            
            cols_str = ", ".join(columns)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_str})")


@contextmanager
def _conn():
    """Database connection context manager."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ===== Memory CRUD =====

def create_memory(
    title: str,
    type: str,
    date: str,
    subtype: str = None,
    description: str = "",
    substrate: str = "",
    process: str = "",
    custom_fields: dict = None,
    references: dict = None,
) -> int:
    """Create a new memory (experiment or comparison).
    
    Args:
        title: Memory title
        type: 'experiment' or 'comparison'
        date: Date string (YYYY-MM-DD)
        subtype: 'device', 'batch', 'wafer', 'session' (for experiments)
        description: Free text description
        substrate: Substrate type (Kapton, Si/SiO2, etc.)
        process: Fabrication process (BAMS, spin-coating, etc.)
        custom_fields: Dict of field name -> value
        references: Dict of ref_type -> list of paths
    
    Returns:
        memory_id
    """
    created_at = datetime.now().isoformat()
    
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO memories 
               (title, type, subtype, date, description, substrate, process, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, type, subtype, date, description, substrate, process, created_at),
        )
        memory_id = cur.lastrowid
        
        if custom_fields:
            for field_name, field_value in custom_fields.items():
                conn.execute(
                    "INSERT INTO memory_fields (memory_id, field_name, field_value, field_type) VALUES (?, ?, ?, ?)",
                    (memory_id, field_name, str(field_value), "custom"),
                )
        
        # Add references
        if references:
            for ref_type, paths in references.items():
                if isinstance(paths, str):
                    paths = [paths]
                for ref_path in paths:
                    conn.execute(
                        "INSERT INTO memory_references (memory_id, ref_type, ref_path, metadata_json) VALUES (?, ?, ?, ?)",
                        (memory_id, ref_type, ref_path, "{}"),
                    )
        
        return memory_id


def get_memory(
    memory_id: int,
    with_runs: bool = True,
    with_items: bool = True,
) -> Optional[dict]:
    """Get memory by ID with its related data.

    ``with_runs=False`` skips tool runs entirely (used for light edits that touch
    no run-dependent card). ``with_items=False`` loads the runs but not their
    (potentially large) figure/table payloads.
    """
    with _conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            return None

        memory = dict(row)

        # Load fields
        memory["fields"] = [
            dict(r) for r in conn.execute(
                "SELECT * FROM memory_fields WHERE memory_id = ?", (memory_id,)
            ).fetchall()
        ]

        # Load references
        memory["references"] = [
            dict(r) for r in conn.execute(
                "SELECT * FROM memory_references WHERE memory_id = ?", (memory_id,)
            ).fetchall()
        ]

        # Load analysis results
        memory["analysis_results"] = [
            dict(r) for r in conn.execute(
                "SELECT * FROM analysis_results WHERE memory_id = ?", (memory_id,)
            ).fetchall()
        ]

        # Load tool runs (with their items) in a single round-trip
        memory["tool_runs"] = (
            _load_runs_with_items(conn, memory_id, with_items=with_items)
            if with_runs
            else []
        )

        return memory


def _load_runs_with_items(conn, memory_id: int, with_items: bool = True) -> list[dict]:
    """Load a memory's tool runs and attach their items without an N+1 query."""
    rows = conn.execute(
        "SELECT * FROM tool_runs WHERE memory_id = ? ORDER BY created_at DESC, id DESC",
        (memory_id,),
    ).fetchall()
    runs = [dict(row) for row in rows]
    for run in runs:
        run["items"] = []
    if not runs or not with_items:
        return runs

    ids = [run["id"] for run in runs]
    placeholders = ", ".join("?" for _ in ids)
    item_rows = conn.execute(
        f"""SELECT * FROM tool_run_items WHERE run_id IN ({placeholders})
            ORDER BY position, id""",
        ids,
    ).fetchall()

    by_run: dict[int, list[dict]] = {}
    for item in item_rows:
        record = dict(item)
        by_run.setdefault(record["run_id"], []).append(record)
    for run in runs:
        run["items"] = by_run.get(run["id"], [])
    return runs


def list_memories(
    type: str = None,
    subtype: str = None,
    substrate: str = None,
    date_from: str = None,
    date_to: str = None,
    search: str = None,
) -> list[dict]:
    """List memories with optional filters."""
    query = "SELECT * FROM memories WHERE 1=1"
    params = []
    
    if type:
        query += " AND type = ?"
        params.append(type)
    if subtype:
        query += " AND subtype = ?"
        params.append(subtype)
    if substrate:
        query += " AND substrate = ?"
        params.append(substrate)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    query += " ORDER BY date DESC, created_at DESC"
    
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_memory(memory_id: int, **kwargs):
    """Update memory fields."""
    allowed = {"title", "type", "subtype", "date", "description", "substrate", "process"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    
    if not updates:
        return
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [memory_id]
    
    with _conn() as conn:
        conn.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)


def delete_memory(memory_id: int):
    """Delete memory and all related data."""
    with _conn() as conn:
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))


# ===== Fields =====

def add_field(memory_id: int, field_name: str, field_value: str, field_type: str = "custom") -> int:
    """Add a field to a memory."""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO memory_fields (memory_id, field_name, field_value, field_type) VALUES (?, ?, ?, ?)",
            (memory_id, field_name, field_value, field_type),
        )
        return cur.lastrowid


def update_field(field_id: int, field_name: str = None, field_value: str = None):
    """Update a field."""
    with _conn() as conn:
        if field_name is not None:
            conn.execute("UPDATE memory_fields SET field_name = ? WHERE id = ?", (field_name, field_id))
        if field_value is not None:
            conn.execute("UPDATE memory_fields SET field_value = ? WHERE id = ?", (field_value, field_id))


def delete_field(field_id: int):
    """Delete a field."""
    with _conn() as conn:
        conn.execute("DELETE FROM memory_fields WHERE id = ?", (field_id,))


# ===== References =====

def add_reference(memory_id: int, ref_type: str, ref_path: str, metadata: dict = None) -> int:
    """Add a file reference to a memory."""
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO memory_references (memory_id, ref_type, ref_path, metadata_json) VALUES (?, ?, ?, ?)",
            (memory_id, ref_type, ref_path, json.dumps(metadata or {})),
        )
        return cur.lastrowid


def delete_reference(ref_id: int):
    """Delete a reference."""
    with _conn() as conn:
        conn.execute("DELETE FROM memory_references WHERE id = ?", (ref_id,))


# ===== Analysis Results =====

def save_analysis_result(
    memory_id: int,
    function_name: str,
    params: dict,
    results_csv_path: str = None,
) -> int:
    """Save analysis result to a memory."""
    created_at = datetime.now().isoformat()
    
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO analysis_results 
               (memory_id, function_name, params_json, results_csv_path, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (memory_id, function_name, json.dumps(params), results_csv_path, created_at),
        )
        return cur.lastrowid


def list_analysis_results(memory_id: int) -> list[dict]:
    """List all analysis results for a memory."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM analysis_results WHERE memory_id = ?", (memory_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ===== Tool Runs =====

def _with_items(conn, run: dict) -> dict:
    """Attach the items (figures, tables, images) to a tool run dict."""
    run["items"] = [
        dict(r) for r in conn.execute(
            "SELECT * FROM tool_run_items WHERE run_id = ? ORDER BY position, id",
            (run["id"],),
        ).fetchall()
    ]
    return run


def create_tool_run(
    memory_id: int,
    ref_path: str,
    tool_name: str,
    params: dict,
    summary: dict = None,
    description: str = "",
) -> int:
    """Insert a tool run (the recipe and its summary) and return its id."""
    created_at = datetime.now().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO tool_runs
               (memory_id, ref_path, tool_name, params_json, summary_json, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (memory_id, ref_path, tool_name, json.dumps(params),
             json.dumps(summary or {}), description or "", created_at),
        )
        return cur.lastrowid


def add_tool_run_item(run_id: int, kind: str, position: int, label: str, content: dict) -> int:
    """Attach one figure, table or image to a run."""
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO tool_run_items (run_id, kind, position, label, content_json)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, kind, position, label or "", json.dumps(content)),
        )
        return cur.lastrowid


def get_tool_run(run_id: int) -> Optional[dict]:
    """Return a tool run with its items, or None."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM tool_runs WHERE id = ?", (run_id,)).fetchone()
        return _with_items(conn, dict(row)) if row else None


def list_tool_runs(memory_id: int, ref_path: str = None) -> list[dict]:
    """List tool runs of a memory, optionally filtered by source reference."""
    with _conn() as conn:
        if ref_path is None:
            return _load_runs_with_items(conn, memory_id)
        rows = conn.execute(
            """SELECT * FROM tool_runs WHERE memory_id = ? AND ref_path = ?
               ORDER BY created_at DESC, id DESC""",
            (memory_id, ref_path),
        ).fetchall()
        runs = [dict(r) for r in rows]
        for run in runs:
            run["items"] = []
        if not runs:
            return runs
        ids = [run["id"] for run in runs]
        placeholders = ", ".join("?" for _ in ids)
        item_rows = conn.execute(
            f"""SELECT * FROM tool_run_items WHERE run_id IN ({placeholders})
                ORDER BY position, id""",
            ids,
        ).fetchall()
        by_run: dict[int, list[dict]] = {}
        for item in item_rows:
            record = dict(item)
            by_run.setdefault(record["run_id"], []).append(record)
        for run in runs:
            run["items"] = by_run.get(run["id"], [])
        return runs


def delete_tool_run(run_id: int):
    """Delete a tool run and (via cascade) all its items."""
    with _conn() as conn:
        conn.execute("DELETE FROM tool_runs WHERE id = ?", (run_id,))


def delete_tool_runs_for(memory_id: int, ref_path: str, tool_name: str) -> list[int]:
    """Delete every run matching a (memory, reference, tool) triple. Returns their ids."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id FROM tool_runs WHERE memory_id = ? AND ref_path = ? AND tool_name = ?",
            (memory_id, ref_path, tool_name),
        ).fetchall()
        ids = [r["id"] for r in rows]
        for run_id in ids:
            conn.execute("DELETE FROM tool_runs WHERE id = ?", (run_id,))
        return ids
