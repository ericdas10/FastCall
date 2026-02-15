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

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"