# AI WorkSpace 后端镜像
# Python 3.12 + CPU 版 torch + LangChain RAG 全家桶
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    TZ=Asia/Shanghai \
    # HuggingFace 模型缓存目录（挂载卷持久化，重建容器不重新下载 BGE 模型）
    HF_HOME=/app/hf_cache \
    # 国内服务器直连 huggingface.co 不通，走 hf-mirror 镜像
    HF_ENDPOINT=https://hf-mirror.com \
    # 生产环境通过 secret 或只读卷挂载固定私钥
    RSA_PRIVATE_KEY_PATH=/run/secrets/auth_rsa_private_key.pem

WORKDIR /app

# 系统依赖：tzdata（时区），不装多余的东西保持镜像精简
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# 1) 先装 CPU 版 torch —— 必须显式指定 CPU 源！
#    Linux 上默认会拉 CUDA 版（约 2.5GB+ 一堆 nvidia 库），服务器无 GPU 纯浪费磁盘
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu

# 2) 再装其余依赖（torch 已满足 sentence-transformers 的 >=1.11.0 要求，不会重复下载）
#    国内服务器走清华 pypi 镜像加速
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3) 拷贝项目代码（放最后：代码变动时上面的依赖层缓存依然有效，重建只需秒级）
COPY . .

# 运行时数据目录（compose 挂载卷的挂载点）
# uploads/ 用户上传文件；data/ milvus-lite 向量库文件；hf_cache/ BGE 模型缓存
RUN mkdir -p /app/uploads /app/data /app/hf_cache

EXPOSE 8000

# 健康检查：用 python 标准库探测，无需安装 curl
HEALTHCHECK --start-period=60s --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3)" || exit 1

# 当前仍以单进程运行；RSA 私钥已经持久化，后续切换多 worker 时
# 需要确保每个 worker 都能只读访问同一个 /run/secrets 密钥文件。
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
