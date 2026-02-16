import pytest
from sqlalchemy import inspect

from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.messages.model import Messages
from app.model.enums import DomainEnum, CountryEnum


def test_messages_tablename_and_pk(db_session):
    assert Messages.__tablename__ == "messages"

    mapper = inspect(Messages)
    pk_cols = [c.name for c in mapper.primary_key]
    assert pk_cols == ["message_id"]


def test_messages_columns_exist(db_session):
    cols = {c.name for c in Messages.__table__.columns}
    expected = {"message_id", "client_id", "text_message", "response"}
    assert expected.issubset(cols)


def test_message_create_and_relationship(db_session):
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
    db_session.flush()

    msg = Messages(
        client_id=client.client_id,
        text_message="Salut",
        response="Bună! Cu ce te ajut?",
    )
    db_session.add(msg)
    db_session.commit()

    assert msg.message_id is not None
    assert msg.client is not None
    assert msg.client.client_id == client.client_id


def test_cascade_delete_client_deletes_messages(db_session):
    # create graph
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
    db_session.flush()

    msg = Messages(client_id=client.client_id, text_message="x", response="y")
    db_session.add(msg)
    db_session.commit()

    # delete client => should delete messages because of relationship cascade in Client.messages
    db_session.delete(client)
    db_session.commit()

    remaining = db_session.query(Messages).count()
    assert remaining == 0
