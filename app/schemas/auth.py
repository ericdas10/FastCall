from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr
from app.model.enums import CountryEnum, DomainEnum


class RegisterCallCenterIn(BaseModel):
    name: str
    username: str
    password: str
    email: str
    domain: DomainEnum
    country: CountryEnum
    number: str
    description: Optional[str] = None
    knowledge_base_path: Optional[str] = None
    database_uri: Optional[str] = None


class RegisterClientIn(BaseModel):
    call_center_id: int
    first_name: str
    last_name: str
    username: str
    password: str
    email: EmailStr
    country: CountryEnum
    number: str


class LoginIn(BaseModel):
    username_or_email: str
    password: str
    # When the same identifier maps to multiple call centers, the client must
    # re-submit with this field set to choose which one to log into.
    call_center_id: Optional[int] = None


class TokenOut(BaseModel):
    kind: Literal["token"] = "token"
    access_token: str
    token_type: str = "bearer"
    actor_type: Literal["call_center", "client"]
    actor_id: int
    call_center_id: Optional[int] = None


class CallCenterCandidate(BaseModel):
    client_id: int
    call_center_id: int
    call_center_name: str


class LoginMultiOut(BaseModel):
    kind: Literal["select_call_center"] = "select_call_center"
    candidates: List[CallCenterCandidate]