from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """项目配置类"""
    # AI API配置
    ZHIPUAI_API_KEY: str = ""
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "logs"
    
    # 文件路径配置
    RESOURCE_PATH: str = "resources"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 