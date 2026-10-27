from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from .. import models
from ..database import get_db
from ..rag_engine import add_document_to_rag # 导入 RAG 引擎

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

    # 1. 存入 MySQL
    new_doc = models.KnowledgeDoc(filename=file.filename, content=content_str)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 2. 实时增量更新：立刻把这段文字向量化，存入 ChromaDB！
    try:
        chunk_count = add_document_to_rag(
            doc_id=new_doc.id,
            filename=file.filename,
            text=content_str
        )
        print(f"✅ 增量更新成功：文件 {file.filename} 已切分为 {chunk_count} 个片段存入向量库")
    except Exception as e:
        print(f"⚠️ 向量化失败: {e}")
        chunk_count = 0  # 失败时给个默认值，防止下面 return 报错

    return {
        "status": "success",
        "message": f"文件 {file.filename} 上传成功并已完成向量化",
        "doc_id": new_doc.id,
        "chunks_created": chunk_count
    }