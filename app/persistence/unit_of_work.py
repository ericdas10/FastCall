from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends
from app.persistence.db import create_session  # if you used create_session helper
from app.persistence.repositories.call_center import CallCentersRepository
from app.persistence.repositories.client import ClientRepository
from app.persistence.repositories.messages import MessagesRepository
from app.persistence.exceptions import PersistenceError
from app.persistence.repositories.revoked_tokens import RevokedTokensRepository
from app.persistence.repositories.tickets import TicketsRepository


class UnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.call_centers = CallCentersRepository(session)
        self.clients = ClientRepository(session)
        self.messages = MessagesRepository(session)
        self.revoked_tokens = RevokedTokensRepository(session)
        self.tickets = TicketsRepository(session)

    def commit(self) -> None:
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise PersistenceError(str(exc)) from exc

    def rollback(self) -> None:
        self.session.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc:
            self.rollback()
        else:
            try:
                self.commit()
            finally:
                self.session.close()

def get_uow() -> Generator[UnitOfWork, None, None]:
    session = create_session()
    try:
        uow = UnitOfWork(session)
        yield uow
    finally:
        try:
            session.close()
        except Exception:
            pass