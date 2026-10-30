import os
import redis

# 🌟 1. 强制清空系统代理环境变量，防止 Clash 劫持本地 Redis 连接
# 注意：这段必须放在实例化连接池之前
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

# 🌟 2. 从环境变量读取主机名（本地默认 127.0.0.1，Docker 里读 redis-db）
redis_host = os.getenv("REDIS_HOST", "127.0.0.1")

# 🌟 3. 创建全局唯一的 Redis 连接池
redis_pool = redis.ConnectionPool(
    host=redis_host,
    port=6379,
    db=0,
    decode_responses=True,      # 自动把字节解码成字符串
    socket_connect_timeout=5    # 🌟 核心：连接超时 5 秒，防止死等
)

def get_redis():
    """获取 Redis 客户端的依赖函数"""
    return redis.Redis(connection_pool=redis_pool)