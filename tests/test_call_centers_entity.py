import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.model.call_centers.model import CallCenters
from app.model.enums import DomainEnum, CountryEnum


def test_call_centers_tablename_and_pk(db_session):
    assert CallCenters.__tablename__ == "call_centers"

    mapper = inspect(CallCenters)
    pk_cols = [c.name for c in mapper.primary_key]
    assert pk_cols == ["call_center_id"]


def test_call_centers_columns_exist(db_session):
    cols = {c.name for c in CallCenters.__table__.columns}
    expected = {
        "call_center_id", "name", "username", "password", "email",
        "domain", "country", "number"
    }
    assert expected.issubset(cols)


def test_call_centers_create_valid(db_session):
    cc = CallCenters(
        name="Acme CC",
        username="acme",
        password="hashed_pw",
        email="admin@acme.com",
        domain=DomainEnum.TECHNOLOGY,   # enum
        country=CountryEnum.RO,         # enum
        number="+40123456789",
    )
    db_session.add(cc)
    db_session.commit()
    assert cc.call_center_id is not None


def test_call_centers_enum_invalid_domain_raises(db_session):
    # încearcă să bagi un string invalid -> ar trebui să crape (StatementError / IntegrityError depinde de DB)
    cc = CallCenters(
        name="Bad CC",
        username="bad",
        password="hashed_pw",
        email="bad@acme.com",
        domain="not-a-domain",
        country=CountryEnum.RO,
        number="123",
    )
    db_session.add(cc)
    with pytest.raises((StatementError, IntegrityError)):
        db_session.commit()


def test_call_centers_enum_invalid_country_raises(db_session):
    cc = CallCenters(
        name="Bad CC2",
        username="bad2",
        password="hashed_pw",
        email="bad2@acme.com",
        domain=DomainEnum.FINANCE,
        country="XX",
        number="123",
    )
    db_session.add(cc)
    with pytest.raises((StatementError, IntegrityError)):
        db_session.commit()
