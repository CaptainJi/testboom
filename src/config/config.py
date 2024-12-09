from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """配置类"""
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL: str = "glm-4v"  # 默认使用GLM-4V模型
    
    # 日志配置
    LOG_LEVEL: str = "DEBUG"
    LOG_PATH: str = "logs"
    
    # 文件路径配置
    RESOURCE_PATH: str = "resources"
    
    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "allow"  # 允许额外的配置项
    )

settings = Settings() 