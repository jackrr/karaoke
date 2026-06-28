"""Upload API routes: accept uploaded audio files."""
import uuid
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi import UploadFile, File
from app.config import settings

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Accept a single audio file upload (.mp3 / .wav).

    Returns the file_id and storage path.
    """
    allowed_ext = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_ext)}",
        )

    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext.lower()}"
    upload_dir = Path(settings.storage_root) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename

    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    return {"file_id": file_id, "path": str(dest), "filename": filename}
