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

    def register_call_center(
        self, *, name, username, password, email, domain, country, number,
        description=None, knowledge_base_path=None, database_uri=None,
    ):

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
            description=(description.strip() if isinstance(description, str) and description.strip() else None),
            knowledge_base_path=(knowledge_base_path.strip() if isinstance(knowledge_base_path, str) and knowledge_base_path.strip() else None),
            database_uri=(database_uri.strip() if isinstance(database_uri, str) and database_uri.strip() else None),
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

        # Uniqueness is now scoped to a single call center: the same person can
        # have separate accounts at different call centers using the same
        # username/email.
        existing = (
            self.uow.session.query(Client)
            .filter(
                Client.call_center_id == call_center_id,
                (Client.email == email) | (Client.username == username.strip()),
            )
            .one_or_none()
        )
        if existing:
            raise AlreadyExists("An account with this email or username already exists for this call center")

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

    def login(self, *, username_or_email, password, call_center_id=None):
        """
        Returns one of:
          { "kind": "token", "access_token": ..., "actor_type": ..., "actor_id": ..., "call_center_id": ... }
          { "kind": "select_call_center", "candidates": [ {client_id, call_center_id, call_center_name}, ... ] }

        Raises NotAllowed for invalid credentials.
        """
        identifier = (username_or_email or "").strip()
        identifier_lower = identifier.lower()

        # 1) Call-center accounts (single tenant, no ambiguity).
        cc = (
            self.uow.session.query(CallCenters)
            .filter(
                (CallCenters.email == identifier_lower) |
                (CallCenters.username == identifier)
            )
            .one_or_none()
        )

        if cc and verify_password(password, cc.password):
            token = create_access_token(
                subject=str(cc.call_center_id),
                claims={"actor_type": "call_center", "actor_id": cc.call_center_id},
            )
            return {
                "kind": "token",
                "access_token": token,
                "actor_type": "call_center",
                "actor_id": cc.call_center_id,
                "call_center_id": None,
            }

        # 2) Client accounts: a single (username|email) may match multiple rows
        #    across different call centers. Filter by password validity.
        candidates = (
            self.uow.session.query(Client)
            .filter(
                (Client.email == identifier_lower) |
                (Client.username == identifier)
            )
            .all()
        )
        verified = [c for c in candidates if verify_password(password, c.password)]

        if not verified:
            raise NotAllowed("Invalid credentials")

        if call_center_id is not None:
            verified = [c for c in verified if c.call_center_id == int(call_center_id)]
            if not verified:
                raise NotAllowed("Invalid credentials for the selected call center")

        if len(verified) == 1:
            cl = verified[0]
            token = create_access_token(
                subject=str(cl.client_id),
                claims={
                    "actor_type": "client",
                    "actor_id": cl.client_id,
                    "call_center_id": cl.call_center_id,
                },
            )
            return {
                "kind": "token",
                "access_token": token,
                "actor_type": "client",
                "actor_id": cl.client_id,
                "call_center_id": cl.call_center_id,
            }

        # Multiple call centers — let the user pick.
        cc_ids = list({c.call_center_id for c in verified})
        cc_rows = (
            self.uow.session.query(CallCenters)
            .filter(CallCenters.call_center_id.in_(cc_ids))
            .all()
        )
        cc_map = {row.call_center_id: row for row in cc_rows}

        return {
            "kind": "select_call_center",
            "candidates": [
                {
                    "client_id": c.client_id,
                    "call_center_id": c.call_center_id,
                    "call_center_name": cc_map[c.call_center_id].name if c.call_center_id in cc_map else "",
                }
                for c in verified
            ],
        }


    def logout(self, *, jti: str) -> None:
        # idempotent revoke
        if not self.uow.revoked_tokens.is_revoked(jti):
            self.uow.revoked_tokens.revoke(jti)
            self.uow.revoked_tokens.flush()
            self.uow.commit()