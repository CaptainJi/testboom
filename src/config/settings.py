from pydantic import Field, ConfigDict, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache
import os
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class AIConfig(BaseSettings):
    """AI模型配置"""
    ZHIPU_API_KEY: str = Field(
        default="",  # 允许空值，但会在使用时检查
        description="智谱AI API密钥"
    )
    ZHIPU_MODEL_CHAT: str = Field("glm-4", description="对话模型名称")
    ZHIPU_MODEL_VISION: str = Field("glm-4v", description="多模态模型名称")
    MAX_TOKENS: int = Field(6000, description="最大token数")
    MAX_IMAGE_SIZE: int = Field(10 * 1024 * 1024, description="最大图片大小(bytes)")
    RETRY_COUNT: int = Field(3, description="重试次数")
    RETRY_DELAY: int = Field(5, description="重试延迟(秒)")
    RETRY_BACKOFF: float = Field(2.0, description="重试延迟倍数")
    
    model_config = ConfigDict(
        env_prefix="AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

class LogConfig(BaseSettings):
    """日志配置"""
    LOG_LEVEL: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO").upper(),
        description="日志级别"
    )
    LOG_FILE: str = Field(str(BASE_DIR / "logs/app.log"), description="日志文件路径")
    LOG_FORMAT: str = Field(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        description="日志格式"
    )
    LOG_ROTATION: str = Field("500 MB", description="日志轮转大小")
    LOG_RETENTION: str = Field("10 days", description="日志保留时间")
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            import warnings
            warnings.warn(f"无效的日志级别: {v}，使用默认值: INFO")
            return "INFO"
        return v
    
    model_config = ConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

class DatabaseConfig(BaseSettings):
    """数据库配置"""
    DB_URL: str = Field(
        default=f"sqlite:///{BASE_DIR}/testboom.db",
        description="数据库连接URL"
    )
    DB_ECHO: bool = Field(False, description="是否打印SQL语句")
    DB_POOL_SIZE: int = Field(5, description="连接池大小")
    DB_MAX_OVERFLOW: int = Field(10, description="最大溢出连接数")
    
    model_config = ConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

class Settings(BaseSettings):
    """应用配置"""
    # 基础配置
    APP_NAME: str = Field("TestBoom", description="应用名称")
    APP_VERSION: str = Field("1.0.0", description="应用版本")
    DEBUG: bool = Field(False, description="调试模式")
    
    # 路径配置
    BASE_DIR: Path = Field(default=BASE_DIR, description="项目根目录")
    
    # 子配置
    ai: AIConfig = Field(default_factory=AIConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_directories()
        self._validate_api_key()
        self._print_debug_info()
    
    def _init_directories(self):
        """初始化必要的目录"""
        # 确保日志目录存在
        log_dir = Path(self.log.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保数据库目录存在
        if self.db.DB_URL.startswith("sqlite:///"):
            db_path = self.db.DB_URL.replace("sqlite:///", "")
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_api_key(self):
        """验证API密钥"""
        if not self.ai.ZHIPU_API_KEY:
            import warnings
            warnings.warn(
                "ZHIPU_API_KEY 未设置！请在环境变量或 .env 文件中设置 AI_ZHIPU_API_KEY",
                RuntimeWarning
            )
    
    def _print_debug_info(self):
        """打印调试信息"""
        print("\n=== 配置加载信息 ===")
        print(f"环境变量文件: {self.model_config.get('env_file', '未指定')}")
        print(f"环境变量 LOG_LEVEL: {os.getenv('LOG_LEVEL', '未设置')}")
        print(f"配置 LOG_LEVEL: {self.log.LOG_LEVEL}")
        print(f"调试模式: {self.DEBUG}")
        print("===================\n")

# 创建全局配置实例
settings = Settings()

# 导出配置实例
__all__ = ["settings"]