# app/services/auth_service.py

from dataclasses import dataclass
from typing import Literal, Optional
import re

from app.persistence.unit_of_work import UnitOfWork
from app.utils.security import hash_password, verify_password
from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from .exceptions import AlreadyExists, ValidationError, NotFound, NotAllowed
from app.security.jwt import create_access_token


ActorType = Literal["call_center", "client"]

@dataclass(frozen=True)
class Actor:
    actor_type: ActorType
    actor_id: int
    call_center_id: Optional[int]


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # ---------- Registration ----------

    def register_call_center(self, *, name, username, password, email, domain, country, number):

        password = password.strip()
        if len(password.encode("utf-8")) > 72:
            raise ValidationError("Password too long (max 72 bytes)")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        email = email.strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValidationError("Invalid email")

        if self.uow.call_centers.get_by_email(email):
            raise AlreadyExists("Email already exists")

        existing_username = (
            self.uow.session.query(CallCenters)
            .filter(CallCenters.username == username)
            .one_or_none()
        )
        if existing_username:
            raise AlreadyExists("Username already exists")

        cc = CallCenters(
            name=name.strip(),
            username=username.strip(),
            password=hash_password(password),
            email=email,
            domain=domain,
            country=country,
            number=number.strip(),
        )

        self.uow.call_centers.add(cc)
        self.uow.call_centers.flush()
        self.uow.commit()

        return cc

    def register_client(self, *, call_center_id, first_name, last_name,
                        username, password, email, country, number):

        password = password.strip()
        if len(password.encode("utf-8")) > 72:
            raise ValidationError("Password too long (max 72 bytes)")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        if not self.uow.call_centers.get(call_center_id):
            raise NotFound("Call center not found")

        email = email.strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValidationError("Invalid email")

        if self.uow.clients.get_by_email(email):
            raise AlreadyExists("Email already exists")

        client = Client(
            call_center_id=call_center_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            username=username.strip(),
            password=hash_password(password),
            email=email,
            country=country,
            number=number.strip(),
        )

        self.uow.clients.add(client)
        self.uow.clients.flush()
        self.uow.commit()

        return client

    # ---------- Login ----------

    def login(self, *, username_or_email, password):

        cc = (
            self.uow.session.query(CallCenters)
            .filter(
                (CallCenters.email == username_or_email.lower()) |
                (CallCenters.username == username_or_email)
            )
            .one_or_none()
        )

        if cc and verify_password(password, cc.password):
            token = create_access_token(
                subject=str(cc.call_center_id),
                claims={"actor_type": "call_center", "actor_id": cc.call_center_id}
            )
            return token

        cl = (
            self.uow.session.query(Client)
            .filter(
                (Client.email == username_or_email.lower()) |
                (Client.username == username_or_email)
            )
            .one_or_none()
        )

        if cl and verify_password(password, cl.password):
            token = create_access_token(
                subject=str(cl.client_id),
                claims={"actor_type": "client", "actor_id": cl.client_id, "call_center_id": cl.call_center_id}
            )

            return token

        raise NotAllowed("Invalid credentials")


    def logout(self, *, jti: str) -> None:
        # idempotent revoke
        if not self.uow.revoked_tokens.is_revoked(jti):
            self.uow.revoked_tokens.revoke(jti)
            self.uow.revoked_tokens.flush()
            self.uow.commit()