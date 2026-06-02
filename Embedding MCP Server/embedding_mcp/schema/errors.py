"""Schema validation error exception."""
from __future__ import annotations


class SchemaValidationError(Exception):
    """Raised when input/output violates a schema.

    Attributes:
        message: Human-readable error description
        field: The field that failed validation (if applicable)
        code: Error code (default "SCHEMA_VIOLATION")
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        code: str = "SCHEMA_VIOLATION",
    ):
        self.field = field
        self.code = code
        super().__init__(message)