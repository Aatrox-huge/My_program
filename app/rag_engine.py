import os

import time
from sentence_transformers import SentenceTransformer


# 🌟 强制全局离线，绝对不允许去外网
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HF_HUB_OFFLINE"] = "1"
import chromadb
from sentence_transformers import SentenceTransformer
# 🌟 2. 动态读取主机名（本地跑就是 127.0.0.1，Docker 里读环境变量变成 chromadb）
chroma_host = os.getenv("CHROMA_HOST", "127.0.0.1")
print(f"🚀 正在通过 HTTP 连接 ChromaDB (主机: {chroma_host})...",flush=True)



# 🌟 3. 把 HttpClient 的重试逻辑加在这里
# 🌟 核心修改：无限重试，直到连上为止！
chroma_client = None
for i in range(3): # 🌟 只试 3 次
    try:
        chroma_client = chromadb.HttpClient(host=chroma_host, port=8000)
        chroma_client.heartbeat()
        print("✅ 成功连接到 ChromaDB！", flush=True)
        break
    except Exception as e:
        print(f"⚠️ 连接 Chroma 失败，2 秒后重试... (错误: {e})", flush=True)
        time.sleep(2)

# 🌟 核心修复：如果连不上，直接打印致命错误，但不要让程序完全卡死
if not chroma_client:
    print("❌ 致命错误：无法连接 ChromaDB！", flush=True)
    # 故意抛出一个可以捕获的异常，让 FastAPI 启动失败但留下日志
    raise RuntimeError("ChromaDB connection failed!")

# 获取或创建集合
collection = chroma_client.get_or_create_collection(name="knowledge_base")
print("✅ 成功连接到 Docker ChromaDB，集合已准备就绪！")

# 🌟 3. 把模型下载路径指定到当前项目下，方便 Docker 挂载（防止每次重启重新下载）
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "./model_cache"

import os

# 获取当前文件所在目录的上一级（即 /app），然后拼接 model_cache 路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model_cache", "hub", "models--sentence-transformers--all-MiniLM-L6-v2", "snapshots")

# 🌟 核心修复：动态找到 snapshots 下面那个长得像哈希值的文件夹
if os.path.exists(MODEL_PATH):
    # 取 snapshots 下的第一个文件夹作为真正的模型路径
    snapshot_folders = os.listdir(MODEL_PATH)
    if snapshot_folders:
        actual_model_path = os.path.join(MODEL_PATH, snapshot_folders[0])
        print(f"✅ 找到本地模型，路径为: {actual_model_path}", flush=True)
        embed_model = SentenceTransformer(actual_model_path)
    else:
        raise Exception("❌ model_cache 里面的 snapshots 文件夹是空的！")
else:
    raise Exception(f"❌ 找不到模型路径！请检查 Docker 挂载是否正确。路径: {MODEL_PATH}")


def add_document_to_rag(doc_id: int, filename: str, text: str, user_id: str = "default_user"):
    """把文本切片并存入向量库"""
    chunk_size = 500
    overlap = 50
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"filename": filename, "doc_id": doc_id, "user_id": user_id} for _ in range(len(chunks))]
    embeddings = embed_model.encode(chunks).tolist()

    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)


def search_in_rag(query: str, user_id: str = "default_user", top_k: int = 2):
    """根据用户的提问，在向量库里找最相似的片段"""
    query_embedding = embed_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"user_id": user_id}
    )

    if not results['documents'] or len(results['documents'][0]) == 0:
        return "没有找到相关内容。"

    valid_docs = []
    threshold = 1.6  # 距离阈值

    for i, distance in enumerate(results['distances'][0]):
        if distance <= threshold:
            valid_docs.append(results['documents'][0][i])

    if not valid_docs:
        return "没有找到相关内容。"

    return "\n\n".join(valid_docs)