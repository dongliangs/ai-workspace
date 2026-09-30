
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

#创建一个Setting 实例

# 其他文件也可以下：
#from app.core.config import setting

settings = Settings()