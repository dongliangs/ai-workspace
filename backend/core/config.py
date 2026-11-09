
# 从pydantic_setting 中导入 BaseSetting.
#

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Setting 是整个项目的配置类。
#
class Settings(BaseSettings):
    #Pydantic setting 会自动读取环境变量 DATABASE_URL
    database_url: str

    # jwt生成和验证的时候需要使用这个秘钥
    jwt_secret_key: str
    # JWT Token 的有效时间，单位：分钟
    access_token_expire_minutes: int = 60

    deepseek_api_key: str
    deepseek_model: str = "deepseek-flash"
    deepseek_base_url: str = "https://api.deepseek.com"

    # ---- LLM 调用可靠性配置 ----
    # 单次请求（非流式响应或建立流式连接）的最长等待时间，单位：秒。
    llm_request_timeout_seconds: float = Field(default=60.0, gt=0)
    # 流式响应两次数据片之间的最大空闲时间。超过该时间视为上游卡死，
    # 主动关闭连接并按普通超时处理，避免 SSE 长时间没有任何反馈。
    llm_stream_idle_timeout_seconds: float = Field(default=30.0, gt=0)
    # 单次流式生成的总时长上限，单位：秒。即使上游持续缓慢输出，
    # 也不能无限占用连接和服务器资源。
    llm_stream_total_timeout_seconds: float = Field(default=300.0, gt=0)
    # 上游调用失败后的最大重试次数（不包含第一次正式调用）。
    llm_max_retries: int = Field(default=2, ge=0)
    # 指数退避的基础等待时间和最大等待时间，单位：秒。
    llm_retry_base_delay_seconds: float = Field(default=0.5, ge=0)
    llm_retry_max_delay_seconds: float = Field(default=4.0, ge=0)
    # 连续多少次完整调用失败后打开熔断器。
    llm_circuit_failure_threshold: int = Field(default=5, ge=1)
    # 熔断器冷却时间，冷却结束后才会放行半开探测请求。
    llm_circuit_recovery_timeout_seconds: float = Field(default=30.0, gt=0)
    # 半开状态下允许同时通过的最大探测请求数。
    llm_circuit_half_open_max_calls: int = Field(default=1, ge=1)

    # ---- 文件上传配置 ----
    # 文件存储根目录（相对于项目根目录）
    upload_dir: str = "uploads"
    # 最大文件大小，单位 MB
    max_file_size_mb: int = 20
    # 允许的文件扩展名（小写，不含点）
    allowed_file_extensions: str = (
        "jpg,jpeg,png,gif,webp,"
        "pdf,txt,md,csv,"
        "xlsx,xls,"
        "doc,docx,"
        "ppt,pptx"
    )

    # ---- V0.3 RAG 知识库配置 ----
    # Embedding 模型名称（HuggingFace hub ID）
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    # Embedding 向量维度（bge-small-zh-v1.5 = 512）
    embedding_dim: int = 512
    # Milvus-lite 数据库文件路径
    milvus_db_path: str = "milvus_data.db"
    # Milvus collection 名称
    milvus_collection_name: str = "knowledge_chunks"
    # 文本分块大小（token 数）
    chunk_size: int = 600
    # 文本分块重叠（token 数）
    chunk_overlap: int = 100
    # 检索 Top-K
    retrieval_top_k: int = 5
    # 相似度阈值（低于此分数的结果被过滤）
    retrieval_score_threshold: float = 0.3
    # 同步索引任务的独立并发数与超时时间（单位：秒）
    rag_index_concurrency: int = Field(default=1, ge=1)
    rag_index_timeout_seconds: float = Field(default=300.0, gt=0)
    # 同步检索任务的独立并发数与超时时间（单位：秒）
    rag_retrieval_concurrency: int = Field(default=2, ge=1)
    rag_retrieval_timeout_seconds: float = Field(default=30.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

#创建一个Setting 实例

# 其他文件也可以下：
#from app.core.config import setting

settings = Settings()
