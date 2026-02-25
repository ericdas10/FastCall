from typing import Generic, TypeVar, Type, Iterable, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.persistence.exceptions import UniqueConstraintViolation

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    def get(self, pk) -> Optional[T]:
        return self.session.get(self.model, pk)

    def list_all(self) -> Iterable[T]:
        return self.session.query(self.model).all()

    def delete(self, entity: T) -> None:
        self.session.delete(entity)

    def flush(self) -> None:
        """Flush the current session — useful to surface integrity errors early."""
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise UniqueConstraintViolation(str(exc)) from exc