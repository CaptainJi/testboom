from pydantic import ConfigDict
from pydantic_settings import BaseSettings
import os
from typing import Optional

print("[Settings] 当前环境变量:")
print(f"[Settings] LOG_LEVEL = {os.getenv('LOG_LEVEL')}")
print(f"[Settings] 环境变量文件路径: {os.path.abspath('.env')}")

class Settings(BaseSettings):
    """配置类"""
    
    # 智谱AI配置
    ZHIPU_API_KEY: str = ""
    ZHIPU_MODEL_CHAT: str = "glm-4-flash"  # 通用对话模型
    ZHIPU_MODEL_VISION: str = "glm-4v-plus"  # 多模态模型
    
    # 日志配置
    LOG_LEVEL: str = "DEBUG"  # 默认值为 DEBUG
    LOG_PATH: str = "logs"
    
    # 资源路径配置
    RESOURCE_PATH: str = "resources"
    
    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        extra = "allow",  # 允许额外的配置项
        env_prefix = "",  # 不使用前缀
        env_file_override = True  # .env 文件优先级高于环境变量
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 强制使用 .env 文件中的配置
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        if key == "LOG_LEVEL":
                            self.LOG_LEVEL = value
                            break
        
        print(f"[Settings] 配置加载完成，LOG_LEVEL = {self.LOG_LEVEL}")

settings = Settings()
print(f"[Settings] 最终配置: LOG_LEVEL = {settings.LOG_LEVEL}")

# 强制设置环境变量
os.environ["LOG_LEVEL"] = settings.LOG_LEVEL