import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.agent.config import cc_data_dir
from app.agent.registry import get_operator, reset_operator
from app.model.call_centers.model import CallCenters
from app.persistence.unit_of_work import UnitOfWork, get_uow
from app.security.current_actor import CurrentActor, get_current_actor


router = APIRouter(prefix="/call-center", tags=["call-center"])


def _resolve_kb_dir(uow: UnitOfWork, call_center_id: int) -> Path:
    """
    Return the directory where PDFs should be stored for this call center.

    Uses ``call_centers.knowledge_base_path`` if set; otherwise defaults to
    ``<repo>/data/cc_<id>/kb`` and persists that default on the row so the
    coordinator (and future uploads) see the same location.
    """
    cc = uow.session.get(CallCenters, call_center_id)
    if cc is None:
        raise HTTPException(status_code=404, detail="Call center not found")

    kb_path = (cc.knowledge_base_path or "").strip()
    if not kb_path:
        kb_path = str(cc_data_dir(call_center_id) / "kb")
        cc.knowledge_base_path = kb_path
        uow.commit()

    kb_dir = Path(kb_path)
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Upload a PDF into the call center's knowledge base, then rebuild the
    agentic-RAG operator so the new content is immediately searchable.
    """
    if actor.actor_type != "call_center":
        raise HTTPException(status_code=403, detail="Only call centers can upload PDFs")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    kb_dir = _resolve_kb_dir(uow, actor.actor_id)

    # Drop any path components from the uploaded filename.
    safe_name = Path(file.filename).name
    file_path = kb_dir / safe_name

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store PDF: {e}")

    # Rebuild the operator: this re-indexes the knowledge base into Chroma
    # using OpenAI embeddings and refreshes the DB-schema view.
    try:
        reset_operator(actor.actor_id)
        op = get_operator(actor.actor_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF stored but agent rebuild failed: {e}",
        )

    return {
        "message": f"PDF '{safe_name}' uploaded successfully",
        "file_path": str(file_path),
        "call_center_id": actor.actor_id,
        "knowledge_base_path": str(kb_dir),
        "vector_store_empty": op.ctx.vector_store.is_empty(),
    }
