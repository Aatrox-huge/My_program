import os
os.environ["HF_HUB_OFFLINE"] = "1" # 强制离线，拒绝外网检查
import chromadb
from sentence_transformers import SentenceTransformer


print("🚀 正在通过 HTTP 连接 Docker 里的 ChromaDB (端口 8001)...")
chroma_client = chromadb.HttpClient(host='127.0.0.1', port=8001)

# 🌟 终极修复：不要删除，直接获取或创建。如果里面有脏数据，我们用代码手动清空。
collection = chroma_client.get_or_create_collection(name="knowledge_base")
print("✅ 成功连接到 Docker ChromaDB，集合已准备就绪！")

embed_model = SentenceTransformer('all-MiniLM-L6-v2')


def add_document_to_rag(doc_id: int, filename: str, text: str,user_id: str = "default_user"):
    """把文本切片并存入向量库"""
    chunk_size = 500
    overlap = 50
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"filename": filename, "doc_id": doc_id,"user_id": user_id} for _ in range(len(chunks))]
    embeddings = embed_model.encode(chunks).tolist()

    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)


def search_in_rag(query: str,user_id: str = "default_user", top_k: int = 2):
    """根据用户的提问，在向量库里找最相似的片段"""
    query_embedding = embed_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where = {"user_id": user_id}
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