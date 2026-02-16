import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base  # your declarative Base

# import models so they register in metadata
from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.messages.model import Messages
import sys, os
from dotenv import load_dotenv
load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set. Point it to a dedicated test DB.")

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, future=True, pool_pre_ping=True)
    return eng

@pytest.fixture(scope="session", autouse=True)
def create_schema(engine):
    # Clean schema at start of test session (safe only if this is a dedicated test DB!)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Transaction-per-test pattern:
    - open connection
    - begin outer transaction
    - create a session bound to that connection
    - rollback after test
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False, future=True)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
