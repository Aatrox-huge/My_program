from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .database import Base

class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    user_id = Column(String(50), index=True, comment="所属用户ID")
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), index=True, comment="文件名")
    content = Column(Text, comment="文件提取的原始文本内容")
    created_at = Column(DateTime, default=datetime.now, comment="上传时间")

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), index=True)  # 🌟 新增：归属用户
    session_id = Column(String(50), index=True, comment="会话ID，用于区分不同用户的聊天")
    role = Column(String(20), comment="角色：user 或 assistant")
    content = Column(Text, comment="聊天内容")
    created_at = Column(DateTime, default=datetime.now)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, comment="用户名")
    hashed_password = Column(String(255), comment="加密后的密码")
    created_at = Column(DateTime, default=datetime.now)