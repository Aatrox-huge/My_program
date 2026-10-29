from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form # 引入 Form
from .. import models
from ..database import get_db
from ..rag_engine import add_document_to_rag # 导入 RAG 引擎
from ..auth import get_current_user # 🌟 新增导入
from ..redis_client import get_redis
import redis

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...),
                      user_id: str = Depends(get_current_user), # 🌟 核心：用 Token 里的用户，不再用 Form 接收
                      db: Session = Depends(get_db),
                      r: redis.Redis = Depends(get_redis) # 🌟 注入 Redis
    ):
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
    new_doc = models.KnowledgeDoc(filename=file.filename, content=content_str,user_id=user_id)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 2. 实时增量更新：立刻把这段文字向量化，存入 ChromaDB！
    try:
        # 把需要处理的任务（文档ID）打包成 JSON，扔进 Redis 的列表中
        import json
        task_data = json.dumps({"doc_id": new_doc.id, "user_id": user_id})
        r.lpush("rag_processing_queue", task_data)  # 从左侧推入队列
        print(f"📥 文档 {new_doc.id} 已进入后台队列，等待 Worker 处理")
    except Exception as e:
        print(f"⚠️ 加入队列失败: {e}")

    return {
        "status": "success",
        "message": f"文件 {file.filename} 上传成功，正在后台解析中...",
        "doc_id": new_doc.id,
    }
@router.get("/list")
def get_file_list(
    user_id: str = Depends(get_current_user), # 🌟 自动校验 Token
    db: Session = Depends(get_db)
):
    docs = db.query(models.KnowledgeDoc).filter(models.KnowledgeDoc.user_id == user_id).all()
    return [{"id": doc.id, "filename": doc.filename} for doc in docs]