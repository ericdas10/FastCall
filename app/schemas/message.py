from pydantic import BaseModel

class SendMessageIn(BaseModel):
    text: str

class SendMessageOut(BaseModel):
    message_id: int
    response: str