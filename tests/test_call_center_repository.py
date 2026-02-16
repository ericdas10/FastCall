import pytest
from app.persistence.repositories.call_center import CallCentersRepository
from app.model.call_centers.model import CallCenters
from app.model.enums import DomainEnum, CountryEnum

def test_add_and_get_call_center(db_session):
    repo = CallCentersRepository(db_session)

    cc = CallCenters(
        name="Acme CC",
        username="acme",
        password="hashed",
        email="admin@acme.com",
        domain=DomainEnum.TECHNOLOGY,
        country=CountryEnum.RO,
        number="0700000000",
    )

    repo.add(cc)
    repo.flush()

    found = repo.get(cc.call_center_id)
    assert found is not None
    assert found.email == "admin@acme.com"
    assert found.domain == DomainEnum.TECHNOLOGY

def test_get_by_email(db_session):
    repo = CallCentersRepository(db_session)
    cc = CallCenters(
        name="Acme CC",
        username="acme",
        password="hashed",
        email="admin@acme.com",
        domain=DomainEnum.FINANCE,
        country=CountryEnum.RO,
        number="0700000000",
    )
    repo.add(cc)
    repo.flush()

    found = repo.get_by_email("admin@acme.com")
    assert found is not None
    assert found.username == "acme"

def test_get_by_email_returns_none_when_missing(db_session):
    repo = CallCentersRepository(db_session)
    assert repo.get_by_email("missing@x.com") is None