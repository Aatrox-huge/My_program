from fastapi import APIRouter, HTTPException,Depends,Request
from ..auth import get_current_user
from ..redis_client import get_redis
import redis
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from ..agent_core import run_agent, stream_chat
from ..auth import get_current_user # 导入
from ..agent_core import run_agent, run_agent_stream # 🌟 引入流式函数

router = APIRouter(prefix="/chat", tags=["对话"])

# 定义前端传过来的数据格式
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default_session"  # 给个默认值，防止前端没传报错

@router.post("/agent")
async def chat_with_agent(request: ChatRequest,
                          req_obj: Request,  # 🌟 用来获取用户的 IP
                          current_user: str = Depends(get_current_user),
                          r: redis.Redis = Depends(get_redis)
    ):
    # 🚦 核心限流逻辑：基于用户 ID 或 IP 作为 Key
    rate_key = f"rate_limit:{current_user}"

    # 每次请求，这个 Key 的值 +1
    current_count = r.incr(rate_key)

    # 如果是第一次请求，设置 60 秒的过期时间
    if current_count == 1:
        r.expire(rate_key, 60)

    if current_count > 10:
        raise HTTPException(status_code=429, detail="请求太频繁啦，请 1 分钟后再试！")


    try:
        # 🌟 核心修复：把 query 和 session_id 都传给 Agent
        answer = run_agent(user_query=request.query,
                           session_id=request.session_id,
                           user_id=current_user # 🌟 强制使用 Token 里的用户
         )
        return {"status": "success", "answer": answer}
    except Exception as e:
        # 把真实错误打印到终端，方便下次排错
        print(f"❌ 抓到了后端报错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🌟 新增一个流式接口（替代原来的 /stream）
@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: str = Depends(get_current_user)
):
    # 返回流式生成器
    return StreamingResponse(
        run_agent_stream(request.query, request.session_id, current_user),
        media_type="text/event-stream"
    )


