from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库连接地址（密码 123456）
DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/smart_kb"

# 核心：创建带连接池的引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 自动检测断连并重连
    pool_recycle=3600,
    echo=False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 依赖注入函数，保证每个请求用完连接后自动归还
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()