from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.persistence.db import engine
from app.db import Base

from app.controller.auth_controller import router as auth_router
from app.controller.messaging_controller import router as messaging_router
from app.controller.call_center_controller_fixed import router as call_center_router
from app.controller.client_messages import router as client_messages_router
from app.controller.pdf_upload import router as pdf_upload_router


app = FastAPI(title="FastCall API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(messaging_router)
app.include_router(call_center_router)
app.include_router(client_messages_router)
app.include_router(pdf_upload_router)
