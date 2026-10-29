import os

import redis

# 🌟 强制清空系统代理环境变量，防止 Clash 劫持本地 Redis 连接
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

# 创建 Redis 连接池（后续所有操作都从这里借连接）
redis_pool = redis.ConnectionPool(
    host='127.0.0.1',
    port=6379,
    db=0,
    decode_responses=True, # 自动把字节解码成字符串
    socket_connect_timeout=5 # 🌟 加上超时设置，防止死等
)

def get_redis():
    """获取 Redis 客户端的依赖函数"""
    return redis.Redis(connection_pool=redis_pool)