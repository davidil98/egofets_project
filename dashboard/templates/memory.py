"""Template system for memory creation.

Loads YAML templates from dashboard/templates/*.yaml and syncs them to the database.
Templates are only used when creating new memories - existing memories are not affected by changes.
"""

import yaml
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).parent


def load_templates() -> list[dict]:
    """Load all YAML templates from dashboard/templates/*.yaml.
    
    Returns:
        List of template dictionaries with validated structure
    """
    templates = []
    
    for yaml_file in TEMPLATES_DIR.glob("*.yaml"):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if data is None:
                continue
            
            is_valid, error = validate_template(data)
            if not is_valid:
                print(f"Warning: {yaml_file.name} is invalid: {error}")
                continue
            
            templates.append(data)
        except Exception as e:
            print(f"Warning: Failed to load {yaml_file.name}: {e}")
    
    return templates


def validate_template(yaml_data: dict) -> tuple[bool, str]:
    """Validate template structure and data types.
    
    Required structure:
    - name: str
    - description: str
    - fields: list of field dicts
    
    Each field must have:
    - name: str
    - type: "text" | "integer" | "float"
    - default: any (must match type)
    - required: bool
    
    Args:
        yaml_data: Dictionary loaded from YAML
        
    Returns:
        (is_valid, error_message)
    """
    # Check required top-level keys
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
    
    # Validate each field
    valid_types = {"text", "integer", "float"}
    
    for i, field in enumerate(yaml_data["fields"]):
        if not isinstance(field, dict):
            return False, f"Field {i} must be a dict"
        
        if "name" not in field:
            return False, f"Field {i} missing 'name'"
        if not isinstance(field["name"], str):
            return False, f"Field {i} 'name' must be string"
        
        if "type" not in field:
            return False, f"Field {i} missing 'type'"
        if field["type"] not in valid_types:
            return False, f"Field {i} 'type' must be one of {valid_types}"
        
        if "default" not in field:
            return False, f"Field {i} missing 'default'"
        
        # Validate default matches type
        default_val = field["default"]
        field_type = field["type"]
        
        if field_type == "text" and not isinstance(default_val, str):
            return False, f"Field {i} 'default' must be string for type 'text'"
        elif field_type == "integer" and not isinstance(default_val, int):
            return False, f"Field {i} 'default' must be int for type 'integer'"
        elif field_type == "float" and not isinstance(default_val, (int, float)):
            return False, f"Field {i} 'default' must be number for type 'float'"
        
        if "required" not in field:
            return False, f"Field {i} missing 'required'"
        if not isinstance(field["required"], bool):
            return False, f"Field {i} 'required' must be boolean"
    
    return True, ""


def sync_templates():
    """Synchronize YAML templates with database.
    
    - Creates new templates if they don't exist
    - Updates existing templates if YAML changed
    - Does not affect existing memories
    """
    from src import db
    
    templates = load_templates()
    
    for template_data in templates:
        name = template_data["name"]
        description = template_data["description"]
        fields_json = template_data["fields"]
        
        # Check if template exists
        existing = db.get_template_by_name(name)
        
        if existing is None:
            # Create new template
            db.create_template(name, description, fields_json)
            print(f"Created template: {name}")
        else:
            # Update existing template (idempotent)
            db.update_template(existing["id"], name, description, fields_json)


def get_template(template_id: int) -> dict | None:
    """Get template by ID from database.
    
    Returns:
        Template dict with fields, or None if not found
    """
    from src import db
    return db.get_template(template_id)


def apply_template_defaults(template_id: int) -> dict:
    """Get default values from template.
    
    Returns:
        Dictionary of {field_name: default_value}
    """
    template = get_template(template_id)
    if template is None:
        return {}
    
    defaults = {}
    for field in template["fields"]:
        defaults[field["name"]] = field["default"]
    
    return defaults


def validate_memory_with_template(memory_fields: dict, template_id: int) -> tuple[bool, list[str]]:
    """Validate memory fields against template requirements.
    
    Args:
        memory_fields: Dictionary of {field_name: value}
        template_id: Template ID to validate against
        
    Returns:
        (is_valid, list_of_error_messages)
    """
    template = get_template(template_id)
    if template is None:
        return True, []  # No template, no validation
    
    errors = []
    
    for field in template["fields"]:
        field_name = field["name"]
        required = field["required"]
        field_type = field["type"]
        
        # Check if required field is present
        if required and field_name not in memory_fields:
            errors.append(f"Missing required field: {field_name}")
            continue
        
        # Skip validation if field not present and not required
        if field_name not in memory_fields:
            continue
        
        # Validate type
        value = memory_fields[field_name]
        
        if field_type == "text" and not isinstance(value, str):
            errors.append(f"Field {field_name} must be text")
        elif field_type == "integer" and not isinstance(value, int):
            errors.append(f"Field {field_name} must be integer")
        elif field_type == "float" and not isinstance(value, (int, float)):
            errors.append(f"Field {field_name} must be number")
    
    return len(errors) == 0, errors


def list_templates() -> list[dict]:
    """List all templates from database.
    
    Returns:
        List of template dictionaries
    """
    from src import db
    return db.list_templates()
