import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.enums import CountryEnum, DomainEnum


def test_client_tablename_and_pk(db_session):
    assert Client.__tablename__ == "client"

    mapper = inspect(Client)
    pk_cols = [c.name for c in mapper.primary_key]
    assert pk_cols == ["client_id"]


def test_client_columns_exist(db_session):
    cols = {c.name for c in Client.__table__.columns}
    expected = {
        "client_id", "call_center_id", "first_name", "last_name",
        "username", "password", "email", "country", "number"
    }
    assert expected.issubset(cols)


def test_client_create_with_company_relationship(db_session):
    cc = CallCenters(
        name="Acme CC",
        username="acme",
        password="hashed_pw",
        email="admin@acme.com",
        domain=DomainEnum.TECHNOLOGY,
        country=CountryEnum.RO,
        number="+40123456789",
    )
    db_session.add(cc)
    db_session.flush()

    client = Client(
        call_center_id=cc.call_center_id,
        first_name="Ion",
        last_name="Pop",
        username="ion.pop",
        password="hashed_pw",
        email="ion@ex.com",
        country=CountryEnum.RO,
        number="0700000000",
    )
    db_session.add(client)
    db_session.commit()

    assert client.client_id is not None
    assert client.call_center is not None
    assert client.call_center.call_center_id == cc.call_center_id


def test_client_enum_invalid_country_raises(db_session):
    client = Client(
        call_center_id=None,
        first_name="Bad",
        last_name="User",
        username="bad.user",
        password="hashed_pw",
        email="bad@ex.com",
        country="XX",
        number="1",
    )
    db_session.add(client)
    with pytest.raises((StatementError, IntegrityError)):
        db_session.commit()
