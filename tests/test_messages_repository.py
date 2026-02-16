from app.persistence.repositories.messages import MessagesRepository
from app.persistence.repositories.call_center import CallCentersRepository
from app.persistence.repositories.client import ClientRepository
from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.messages.model import Messages
from app.model.enums import DomainEnum, CountryEnum

def test_list_by_client_orders_by_id(db_session):
    cc_repo = CallCentersRepository(db_session)
    c_repo = ClientRepository(db_session)
    m_repo = MessagesRepository(db_session)

    cc = CallCenters(
        name="CC",
        username="cc",
        password="hashed",
        email="cc@ex.com",
        domain=DomainEnum.FINANCE,
        country=CountryEnum.RO,
        number="1",
    )
    cc_repo.add(cc)
    cc_repo.flush()

    client = Client(
        call_center_id=cc.call_center_id,
        first_name="Ion",
        last_name="Pop",
        username="ion",
        password="hashed",
        email="ion@ex.com",
        country=CountryEnum.RO,
        number="1",
    )
    c_repo.add(client)
    c_repo.flush()

    m_repo.add(Messages(client_id=client.client_id, text_message="1", response="r1"))
    m_repo.add(Messages(client_id=client.client_id, text_message="2", response="r2"))
    m_repo.flush()

    msgs = m_repo.list_by_client(client.client_id)
    assert [m.text_message for m in msgs] == ["1", "2"]