from __future__ import annotations

from sqlalchemy.exc import DatabaseError


class ObjectCreationError(DatabaseError):
    pass


class QueryFilterError(DatabaseError):
    pass
