from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from .. import models
from ..database import get_db

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename.endswith(".txt") or file.filename.endswith(".md")):
        raise HTTPException(status_code=400, detail="只支持上传 .txt 或 .md 文件")

    content_bytes = await file.read()
    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("gbk")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(content_bytes)

    new_doc = models.KnowledgeDoc(filename=file.filename, content=content_str)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return {
        "status": "success",
        "message": f"文件 {file.filename} 上传成功",
        "doc_id": new_doc.id,
        "char_count": len(content_str)
    }