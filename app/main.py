from fastapi import FastAPI
from openai import chat
from fastapi.staticfiles import StaticFiles  # 新增导入
from .database import engine, Base
from .routers import knowledge,chat,users
import uvicorn

# 启动时自动在 MySQL 里建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartKB-Agent")

# 挂载路由
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(users.router)

# 挂载静态文件夹，允许浏览器访问里面的 HTML/JS/CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    # 返回一段简单的 HTML，自动跳转到网页
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)