from fastapi import FastAPI
from .database import engine, Base
from .routers import knowledge
import uvicorn

# 启动时自动在 MySQL 里建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartKB-Agent")

# 挂载路由
app.include_router(knowledge.router)

@app.get("/")
def root():
    return {"message": "智能知识库 Agent 已启动"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)