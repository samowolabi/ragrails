"""Shared chat tool types."""

from dataclasses import dataclass
from typing import Callable

ToolHandler = Callable[[dict], str]
ToolValidator = Callable[[dict], str | None]


@dataclass
class ToolSpec:
    """Provider-neutral tool definition."""

    name: str
    description: str
    input_schema: dict
    handler: ToolHandler
    validator: ToolValidator | None = None
    requires_confirmation: bool = False
    strict: bool = False

    def as_dict(self) -> dict:
        """Return a provider-neutral serializable tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "requires_confirmation": self.requires_confirmation,
            "strict": self.strict,
        }

    def validate(self, arguments: dict) -> str | None:
        if self.validator is None:
            return None
        return self.validator(arguments)

    def run(self, arguments: dict) -> str:
        return self.handler(arguments)
