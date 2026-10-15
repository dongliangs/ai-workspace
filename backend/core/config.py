
# 从pydantic_setting 中导入 BaseSetting.
#

from pydantic_settings import BaseSettings, SettingsConfigDict

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
    deepseek_model: str = "https://api.deepseek.com"
    deepseek_base_url: str = "deepseek-flash"

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

#创建一个Setting 实例

# 其他文件也可以下：
#from app.core.config import setting

settings = Settings()