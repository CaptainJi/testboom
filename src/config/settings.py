from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """配置类"""
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL_CHAT: str = "glm-4-flash"  # 通用对话模型
    ZHIPU_MODEL_VISION: str = "glm-4v-plus"  # 多模态模型
    
    # 日志配置
    LOG_LEVEL: str = "DEBUG"
    LOG_PATH: str = "logs"
    
    # 资源路径配置
    RESOURCE_PATH: str = "resources"
    
    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "allow"  # 允许额外的配置项
    )

settings = Settings()