import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database import get_db
from . import models
from .rag_engine import search_in_rag

# 加载 .env 文件里的 API Key
load_dotenv()

# 初始化大模型客户端（如果你用阿里云，把 base_url 换成阿里云的）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# ==========================================
# 1. 定义你要给大模型使用的工具（真正的数据库查询）
# ==========================================
def search_notes_db(keyword: str, user_id: str):
    """去向量库查询，隔离用户"""
    from .rag_engine import search_in_rag
    result = search_in_rag(query=keyword, user_id=user_id)
    return f"【向量库检索结果】:\n{result}"


# ==========================================
# 2. 告诉大模型，我们有哪些工具可用（JSON 格式）
# ==========================================
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_notes_db",
            "description": "当用户询问他的私人笔记、学习资料等内容时，使用此工具去数据库里搜索关键词。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "要搜索的关键词，比如 'Docker', 'FastAPI'"
                    }
                },
                "required": ["keyword"]
            }
        }
    }
]


# ==========================================
# 3. 核心：手搓 ReAct 循环引擎
# ==========================================
from .database import get_db
from . import models


def run_agent(user_query: str, session_id: str,user_id: str = "default_user"):
    print(f"\n👤 [Session: {session_id}] 用户提问: {user_query}")

    # 1. 获取数据库连接，保存用户的提问
    db_gen = get_db()
    db = next(db_gen)

    # 保存用户问题到 MySQL
    user_msg = models.ChatHistory(session_id=session_id,
                                  role="user", content=user_query,
                                  user_id=user_id,)
    db.add(user_msg)
    db.commit()

    # 2. 从 MySQL 取出该会话最近的 10 条历史记录
    history = db.query(models.ChatHistory).filter(
        models.ChatHistory.session_id == session_id,
        models.ChatHistory.user_id == user_id  # 🌟 查询时过滤！绝不串号！
    ).order_by(models.ChatHistory.id.desc()).limit(10).all()

    # 因为查出来是倒序的，我们要把它反转成正序（时间顺序）
    history.reverse()

    # 3. 构建发给大模型的 Messages 数组
    messages = [
        {"role": "system",
         "content": "你是一个私人知识库助手。如果用户问及笔记内容，请调用 search_notes_db 工具进行搜索。"}
    ]


    # 把历史记录加进去，防止 tool 的脏数据把模型搞崩
    for msg in history:
        if msg.role in ["user", "assistant"] and msg.content:
            messages.append({"role": msg.role, "content": msg.content})

    # 4. 开始 ReAct 循环
    for step in range(3):
        print(f"\n--- [第 {step + 1} 轮思考] ---")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature = 0.3,  # 🌟 降低随机性，让回答更稳定
            frequency_penalty = 0.5  # 🌟 惩罚重复词汇，防止变成复读机
        )

        response_msg = response.choices[0].message

        if not response_msg.tool_calls:
            print(f"🤖 Agent 最终回答: {response_msg.content}")

            # 将大模型的回答也存入 MySQL
            ai_msg = models.ChatHistory(session_id=session_id,
                                        role="assistant", content=response_msg.content,
                                        user_id=user_id,)
            db.add(ai_msg)
            db.commit()
            db.close()

            return response_msg.content

        print("🧠 模型决定调用工具...")
        messages.append(response_msg)

        for tool_call in response_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"🔧 执行本地工具: {func_name}(参数: {args})")

            if func_name == "search_notes_db":
                observation = search_notes_db(keyword=args.get("keyword"), user_id=user_id)
                print(f"👀 数据库观察结果: {observation[:100]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": observation
                })

    db.close()
    print("⚠️ 达到最大循环次数，强制结束。")
    return "思考超时"

# # 测试代码
if __name__ == "__main__":
    # 假设你昨天上传了一个包含 "FastAPI" 的 txt 文件
    run_agent("帮我在我的笔记里找找，关于 FastAPI 我都记了什么？")


from fastapi.responses import StreamingResponse


def stream_chat(user_query: str):
    """流式生成器：像打字机一样返回结果"""
    messages = [
        {"role": "system", "content": "你是一个私人知识库助手。"},
        {"role": "user", "content": user_query}
    ]

    # 开启 stream=True
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        stream=True
    )

    for chunk in response:
        # 提取每个小片段的内容
        content = chunk.choices[0].delta.content
        if content:
            # 产生（yield）内容，FastAPI 会一点点推给前端
            yield content