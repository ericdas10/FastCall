# app/persistence/exceptions.py
class PersistenceError(Exception):
    """Generic persistence error (wrap DB errors)."""

class EntityNotFound(PersistenceError):
    """Raised when an entity is not found."""

class UniqueConstraintViolation(PersistenceError):
    """Raised when a uniqueness constraint is violated."""