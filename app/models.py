from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .database import Base

class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), index=True, comment="文件名")
    content = Column(Text, comment="文件提取的原始文本内容")
    created_at = Column(DateTime, default=datetime.now, comment="上传时间")