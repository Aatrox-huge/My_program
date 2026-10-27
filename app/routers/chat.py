from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from ..agent_core import run_agent, stream_chat
router = APIRouter(prefix="/chat", tags=["对话"])

# 定义前端传过来的数据格式
class ChatRequest(BaseModel):
    query: str

@router.post("/agent")
async def chat_with_agent(request: ChatRequest):
    try:
        # 调用我们手搓的 Agent 大脑
        answer = run_agent(request.query)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    # 返回流式响应
    return StreamingResponse(stream_chat(request.query), media_type="text/event-stream")


