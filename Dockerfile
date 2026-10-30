# 使用官方 Python 3.11 轻量级镜像
FROM python:3.11-slim



# 🌟 强制清空代理，防止 Docker 构建时走本地 7877 端口
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""

# 设置工作目录
WORKDIR /app

# 🌟 核心修复：将 Debian 默认源替换为阿里云源（解决 exit code 100）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（某些 Python 包需要编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖文件并安装（利用 Docker 缓存层，加快后续构建）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝整个项目代码
COPY . .

# 暴露 FastAPI 的端口
EXPOSE 8000

# 默认启动命令（可在 docker-compose 中被覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]