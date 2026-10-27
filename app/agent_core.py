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
def search_notes_db(keyword: str):
    """去向量库里进行语义检索"""
    result = search_in_rag(query=keyword, top_k=2)
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
def run_agent(user_query: str):
    print(f"\n👤 用户提问: {user_query}")

    messages = [
        {"role": "system",
         "content": "你是一个私人知识库助手。如果用户问及笔记内容，请调用 search_notes_db 工具进行搜索。"},
        {"role": "user", "content": user_query}
    ]

    # 我们设置最多循环 3 次，防止大模型陷入死循环
    for step in range(3):
        print(f"\n--- [第 {step + 1} 轮思考] ---")

        # 1. 请求大模型
        response = client.chat.completions.create(
            model="deepseek-flash",  # 如果用通义千问，改为 qwen-turbo 或 qwen-plus
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )

        response_msg = response.choices[0].message

        # 2. 如果模型没有调用工具，说明它可以直接回答
        if not response_msg.tool_calls:
            print(f"🤖 Agent 最终回答: {response_msg.content}")
            return response_msg.content

        # 3. 如果模型要求调用工具
        print("🧠 模型决定调用工具...")
        messages.append(response_msg)  # 把模型的思考过程存入记忆

        for tool_call in response_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"🔧 执行本地工具: {func_name}(参数: {args})")

            # 真正执行我们刚才写的 Python 数据库查询函数
            if func_name == "search_notes_db":
                observation = search_notes_db(args.get("keyword"))
                print(f"👀 数据库观察结果: {observation[:100]}...")  # 只打印前100字看看

                # 4. 把执行结果作为“观察(Observation)”告诉大模型，进入下一轮循环
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": observation
                })

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