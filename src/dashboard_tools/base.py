"""Base classes shared by every dashboard tool.

A tool is a Python script that the dashboard runs on an attached file with a
set of user-chosen parameters. It produces one of three things: a figure, a
table or an image. The dashboard stores the outputs as memory references and
the parameters as an analysis result.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

PARAMETER_TYPES = ("float", "int", "bool", "str", "float_pair", "choice", "measurements")


@dataclass(frozen=True)
class ParameterSchema:
    """Description of one parameter; the dashboard builds its form from this."""

    name: str
    label: str
    type: str
    default: Any
    choices: tuple = ()
    help: str = ""

    def __post_init__(self):
        if self.type not in PARAMETER_TYPES:
            raise ValueError(f"Unknown parameter type {self.type!r} for {self.name!r}")


@dataclass
class ToolResult:
    """Outputs of one tool run. All paths are absolute."""

    plotly_figures: list = field(default_factory=list)
    tables: list[Path] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    description: str = ""


class Tool(ABC):
    """Base class. Subclasses set the class attributes and implement run()."""

    name: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str] = ""
    input_ref_type: ClassVar[str] = "hdf5"
    measurement_mode: ClassVar[str | None] = None
    parameters: ClassVar[tuple[ParameterSchema, ...]] = ()

    def defaults(self) -> dict:
        return {p.name: p.default for p in self.parameters}

    def coerce(self, params: dict | None) -> dict:
        """Merge user values over the defaults and convert them to the declared types.

        Raises ValueError with a message the UI can show directly.
        """
        merged = self.defaults()
        merged.update(params or {})
        known = {p.name for p in self.parameters}
        unknown = set(merged) - known
        if unknown:
            raise ValueError(f"Unknown parameters for {self.name}: {sorted(unknown)}")

        result: dict = {}
        for schema in self.parameters:
            result[schema.name] = _coerce_value(schema, merged[schema.name])
        return result

    @abstractmethod
    def run(self, ref_path: Path, params: dict, output_dir: Path) -> ToolResult:
        """Process ref_path with validated params, writing files into output_dir."""


def _coerce_value(schema: ParameterSchema, value: Any) -> Any:
    try:
        if schema.type == "float":
            return float(value)
        if schema.type == "int":
            return int(value)
        if schema.type == "bool":
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if schema.type == "str":
            return "" if value is None else str(value)
        if schema.type == "float_pair":
            low, high = (float(v) for v in value)
            if low >= high:
                raise ValueError(f"{schema.label}: the first value must be lower than the second")
            return (low, high)
        if schema.type == "choice":
            if value not in schema.choices:
                raise ValueError(f"{schema.label}: {value!r} is not one of {list(schema.choices)}")
            return value
        if schema.type == "measurements":
            if value is None or value == "":
                return []
            return [str(v) for v in value]
    except TypeError as exc:
        raise ValueError(f"{schema.label}: invalid value {value!r} ({exc})") from exc
    except ValueError as exc:
        if str(exc).startswith(schema.label):
            raise
        raise ValueError(f"{schema.label}: invalid value {value!r} ({exc})") from exc
    raise ValueError(f"Unsupported parameter type {schema.type!r}")
