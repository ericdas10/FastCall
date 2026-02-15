from fastapi import FastAPI

from app.persistence.db import engine
from app.db import Base

# import models so SQLAlchemy registers them (important for create_all in dev)
from app.model.call_centers.model import CallCenters
from app.model.client.model import Client
from app.model.messages.model import Messages

# If you added revoked tokens model, import it too:
# from app.models.revoked_tokens.model import RevokedTokens

# Routers
from app.controller.auth_controller import router as auth_router
from app.controller.messaging_controller import router as messaging_router
from app.controller.call_center_controller import router as call_center_router


app = FastAPI(title="FastCall API", version="0.1.0")

# DEV ONLY: create tables automatically.
# In production use Alembic migrations.
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth_router)
app.include_router(messaging_router)
app.include_router(call_center_router)
