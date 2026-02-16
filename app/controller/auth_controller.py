from fastapi import APIRouter, Depends, HTTPException, status

from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.auth_service import AuthService
from app.service.exceptions import ValidationError, AlreadyExists, NotFound, NotAllowed
from app.schemas.auth import RegisterCallCenterIn, RegisterClientIn, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register/call-center", status_code=201)
def register_call_center(dto: RegisterCallCenterIn, uow: UnitOfWork = Depends(get_uow)):
    svc = AuthService(uow)
    try:
        cc = svc.register_call_center(
            name=dto.name,
            username=dto.username,
            password=dto.password,
            email=dto.email,
            domain=dto.domain,
            country=dto.country,
            number=dto.number
        )
        return {"call_center_id": cc.call_center_id}
    except (ValidationError, AlreadyExists) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register/client", status_code=201)
def register_client(dto: RegisterClientIn, uow: UnitOfWork = Depends(get_uow)):
    svc = AuthService(uow)
    try:
        client = svc.register_client(
            call_center_id=dto.call_center_id,
            first_name=dto.first_name,
            last_name=dto.last_name,
            username=dto.username,
            password=dto.password,
            email=dto.email,
            country=dto.country,
            number=dto.number
        )
        return {"client_id": client.client_id}
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, AlreadyExists) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenOut)
def login(dto: LoginIn, uow: UnitOfWork = Depends(get_uow)):
    svc = AuthService(uow)
    try:
        token = svc.login(username_or_email=dto.username_or_email, password=dto.password)
        return TokenOut(access_token=token, token_type="bearer")
    except NotAllowed as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout", status_code=204)
def logout(uow: UnitOfWork = Depends(get_uow)):
    """
    Requires a valid token; revokes the current token jti.
    """
    return None