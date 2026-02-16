from app.persistence.repositories.client import ClientRepository
from app.persistence.repositories.call_center import CallCentersRepository
from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.enums import DomainEnum, CountryEnum

def test_list_by_call_center(db_session):
    cc_repo = CallCentersRepository(db_session)
    c_repo = ClientRepository(db_session)

    cc = CallCenters(
        name="CC1",
        username="cc1",
        password="hashed",
        email="cc1@ex.com",
        domain=DomainEnum.TECHNOLOGY,
        country=CountryEnum.RO,
        number="1",
    )
    cc_repo.add(cc)
    cc_repo.flush()

    c1 = Client(
        call_center_id=cc.call_center_id,
        first_name="A",
        last_name="B",
        username="ab",
        password="hashed",
        email="ab@ex.com",
        country=CountryEnum.RO,
        number="1",
    )
    c2 = Client(
        call_center_id=cc.call_center_id,
        first_name="C",
        last_name="D",
        username="cd",
        password="hashed",
        email="cd@ex.com",
        country=CountryEnum.RO,
        number="2",
    )
    c_repo.add(c1)
    c_repo.add(c2)
    c_repo.flush()

    res = c_repo.list_by_call_center(cc.call_center_id)
    assert len(res) == 2
    assert {x.email for x in res} == {"ab@ex.com", "cd@ex.com"}