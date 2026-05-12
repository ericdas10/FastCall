from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.persistence.db import engine
from app.db import Base

from app.controller.auth_controller import router as auth_router
from app.controller.call_center_controller_fixed import router as call_center_router
from app.controller.conversation_controller import (
    router as conversation_router,
    tickets_router,
)
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
app.include_router(conversation_router)
app.include_router(tickets_router)
app.include_router(call_center_router)
app.include_router(pdf_upload_router)
