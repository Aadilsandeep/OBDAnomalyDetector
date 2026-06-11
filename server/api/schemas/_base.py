"""
api/schemas/_base.py
====================
Shared Pydantic v2 base model with camelCase alias generation.

All API response models inherit from :class:`CamelModel` to ensure
that FastAPI automatically serialises field names in **camelCase** —
the convention expected by the React/TypeScript frontend.

Usage
-----
::

    from server.api.schemas._base import CamelModel

    class MyResponse(CamelModel):
        session_id: str
        total_records: int

    # Serialised as: {"sessionId": "...", "totalRecords": ...}
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that serialises all fields as camelCase.

    ``populate_by_name=True`` allows construction using either the
    Python attribute name (``session_id``) or the camelCase alias
    (``sessionId``), which is convenient for testing and internal use.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
