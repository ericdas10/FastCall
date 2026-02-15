from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer()

def create_access_token(*, subject: str, claims: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        **claims,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_claims(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    return decode_token(creds.credentials)
