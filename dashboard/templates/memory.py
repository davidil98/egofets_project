"""Memory templates stored as YAML files.

A template is a mold used to pre-fill the fields of a new memory. It is never
stored in the database and a memory keeps no link to the template it came from.
Editing or deleting a YAML file never affects memories that were already created.

Files: dashboard/templates/<name>.yaml
"""

import re
from pathlib import Path

import yaml

TEMPLATES_DIR = Path(__file__).parent

VALID_FIELD_TYPES = {"text", "integer", "float"}

_INVALID_NAME_CHARS = re.compile(r"[^a-z0-9_]")


def _sanitize_name(name: str) -> str:
    """Return the template name, rejecting anything that is not [a-z0-9_]."""
    raw = str(name or "").strip().lower()
    clean = _INVALID_NAME_CHARS.sub("", raw)
    if not clean or clean != raw:
        raise ValueError(
            f"Invalid template name {name!r}: only lowercase letters, digits and '_' are allowed"
        )
    return clean


def template_yaml_path(name: str) -> Path:
    """Return the YAML file path for a template name."""
    return TEMPLATES_DIR / f"{_sanitize_name(name)}.yaml"


def template_yaml_exists(name: str) -> bool:
    """Return True when the YAML file of a template exists."""
    try:
        return template_yaml_path(name).exists()
    except ValueError:
        return False


def load_template_yaml(name: str) -> dict | None:
    """Return the parsed YAML of a template, or None if missing or unreadable."""
    try:
        path = template_yaml_path(name)
    except ValueError:
        return None
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Failed to read {path.name}: {e}")
        return None
    return data if isinstance(data, dict) else None


def load_templates() -> list[dict]:
    """Return every valid template found in dashboard/templates/*.yaml, sorted by name."""
    templates = []
    for yaml_file in TEMPLATES_DIR.glob("*.yaml"):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to load {yaml_file.name}: {e}")
            continue

        if data is None:
            continue

        is_valid, error = validate_template(data)
        if not is_valid:
            print(f"Warning: {yaml_file.name} is invalid: {error}")
            continue

        templates.append(data)

    return sorted(templates, key=lambda t: t["name"])


def validate_template(yaml_data: dict) -> tuple[bool, str]:
    """Validate the structure of a template definition.

    Required: name (str), description (str), fields (list). Each field needs
    name (str), type ("text" | "integer" | "float"), default (matching the type)
    and required (bool).
    """
    if not isinstance(yaml_data, dict):
        return False, "Template must be a mapping"

    if "name" not in yaml_data:
        return False, "Missing 'name' field"
    if not isinstance(yaml_data["name"], str):
        return False, "'name' must be a string"

    if "description" not in yaml_data:
        return False, "Missing 'description' field"
    if not isinstance(yaml_data["description"], str):
        return False, "'description' must be a string"

    if "fields" not in yaml_data:
        return False, "Missing 'fields' list"
    if not isinstance(yaml_data["fields"], list):
        return False, "'fields' must be a list"

    for i, field in enumerate(yaml_data["fields"]):
        if not isinstance(field, dict):
            return False, f"Field {i} must be a dict"

        if "name" not in field:
            return False, f"Field {i} missing 'name'"
        if not isinstance(field["name"], str):
            return False, f"Field {i} 'name' must be string"

        if "type" not in field:
            return False, f"Field {i} missing 'type'"
        if field["type"] not in VALID_FIELD_TYPES:
            return False, f"Field {i} 'type' must be one of {VALID_FIELD_TYPES}"

        if "default" not in field:
            return False, f"Field {i} missing 'default'"

        default_val = field["default"]
        field_type = field["type"]
        if field_type == "text" and not isinstance(default_val, str):
            return False, f"Field {i} 'default' must be string for type 'text'"
        if field_type == "integer" and (not isinstance(default_val, int) or isinstance(default_val, bool)):
            return False, f"Field {i} 'default' must be int for type 'integer'"
        if field_type == "float" and (not isinstance(default_val, (int, float)) or isinstance(default_val, bool)):
            return False, f"Field {i} 'default' must be number for type 'float'"

        if "required" not in field:
            return False, f"Field {i} missing 'required'"
        if not isinstance(field["required"], bool):
            return False, f"Field {i} 'required' must be boolean"

    return True, ""


def save_template_yaml(name: str, description: str, fields: list[dict]) -> Path:
    """Validate and write a template YAML file, returning its path."""
    path = template_yaml_path(name)
    data = {
        "name": path.stem,
        "description": description or "",
        "fields": list(fields or []),
    }

    is_valid, error = validate_template(data)
    if not is_valid:
        raise ValueError(error)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return path


def delete_template_yaml(name: str) -> bool:
    """Delete the YAML file of a template; True when a file was removed."""
    path = template_yaml_path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def apply_template_defaults(name: str) -> dict:
    """Return {field_name: default} for a template, or {} if it does not exist."""
    data = load_template_yaml(name)
    if not data:
        return {}
    return {field["name"]: field["default"] for field in data.get("fields", [])}
