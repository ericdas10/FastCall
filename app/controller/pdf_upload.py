from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
import os
import shutil
from app.security.current_actor import get_current_actor, CurrentActor
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.rag.ingestion import ingest_call_center

router = APIRouter(prefix="/call-center", tags=["call-center"])

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow)
):
    """
    Upload PDF for call center ingestion
    """
    if actor.actor_type != "call_center":
        raise HTTPException(status_code=403, detail="Only call centers can upload PDFs")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        call_center_dir = Path(f"app/rag/data/cc_{actor.actor_id}/docs")
        call_center_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = call_center_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        ingest_call_center(actor.actor_id)
        
        return {
            "message": f"PDF '{file.filename}' uploaded successfully",
            "file_path": str(file_path),
            "call_center_id": actor.actor_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")
