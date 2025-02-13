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
    AI_ZHIPU_API_KEY: str = Field(
        default="",  # 允许空值，但会在使用时检查
        description="智谱AI API密钥"
    )
    AI_ZHIPU_MODEL_CHAT: str = Field("glm-4-flash", description="对话模型名称")
    AI_ZHIPU_MODEL_VISION: str = Field("glm-4v-flash", description="多模态模型名称")
    AI_MAX_TOKENS: int = Field(6000, description="最大token数")
    AI_MAX_IMAGE_SIZE: int = Field(10 * 1024 * 1024, description="最大图片大小(bytes)")
    AI_RETRY_COUNT: int = Field(3, description="重试次数")
    AI_RETRY_DELAY: int = Field(5, description="重试延迟(秒)")
    AI_RETRY_BACKOFF: float = Field(2.0, description="重试延迟倍数")
    
    # LangSmith配置
    LANGSMITH_API_KEY: str = Field("", description="LangSmith API密钥")
    LANGSMITH_PROJECT: str = Field("testboom", description="LangSmith项目名称")
    LANGSMITH_ENDPOINT: str = Field(
        "https://api.smith.langchain.com",
        description="LangSmith API端点"
    )
    LANGSMITH_TRACING: bool = Field(
        False, 
        description="是否启用LangSmith追踪"
    )
    
    model_config = ConfigDict(
        env_file=".env",  # 启用环境变量文件
        env_prefix="",  # 不使用前缀，因为属性名已包含前缀
        extra="ignore",
        case_sensitive=True
    )

class LogConfig(BaseSettings):
    """日志配置"""
    LOG_LEVEL: str = Field("INFO", description="日志级别")
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
    
    model_config = ConfigDict(
        env_file="",  # 禁用环境变量文件
        env_prefix="",  # 不使用前缀，因为属性名已包含前缀
        extra="ignore",
        case_sensitive=True
    )
    
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
        env_file="",  # 禁用环境变量文件
        env_prefix="",  # 不使用前缀，因为属性名已包含前缀
        extra="ignore",
        case_sensitive=True
    )

class StorageConfig(BaseSettings):
    """对象存储配置"""
    STORAGE_ENABLED: bool = Field(False, description="是否启用对象存储")
    STORAGE_PROVIDER: str = Field("minio", description="存储提供商")
    STORAGE_ENDPOINT: str = Field("", description="存储服务端点")
    STORAGE_ACCESS_KEY: str = Field("", description="访问密钥")
    STORAGE_SECRET_KEY: str = Field("", description="访问密钥")
    STORAGE_BUCKET_NAME: str = Field("", description="存储桶名称")
    STORAGE_PUBLIC_URL: str = Field("", description="公共访问URL")
    STORAGE_REGION: str = Field("", description="区域")
    
    model_config = ConfigDict(
        env_file="",  # 禁用环境变量文件
        env_prefix="",  # 不使用前缀，因为属性名已包含前缀
        extra="ignore",
        case_sensitive=True
    )

class PlantUMLSettings(BaseSettings):
    """PlantUML 配置"""
    PLANTUML_SERVER_URL: str = "http://www.plantuml.com/plantuml"

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
    storage: StorageConfig = Field(default_factory=StorageConfig)
    
    # PlantUML 配置
    plantuml: PlantUMLSettings = PlantUMLSettings()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix=""  # 不使用前缀
    )
    
    def __init__(self, **kwargs):
        # 从 .env 文件加载配置
        from dotenv import dotenv_values
        
        # 获取 .env 文件的绝对路径
        env_path = BASE_DIR / ".env"
        if not env_path.exists():
            import warnings
            warnings.warn(f".env 文件不存在: {env_path}")
            env_config = {}
        else:
            # 直接读取 .env 文件
            env_config = dotenv_values(env_path)
            
        # 更新配置
        if env_config:
            # 更新 AI 配置
            ai_config = {
                k: v for k, v in env_config.items() 
                if k.startswith('AI_') or k.startswith('LANGSMITH_') or k.startswith('LANGCHAIN_')
            }
            if ai_config:
                # 处理布尔值
                for key in ['LANGSMITH_TRACING', 'LANGCHAIN_TRACING_V2']:
                    if key in ai_config:
                        ai_config[key] = ai_config[key].lower() == 'true'
                kwargs['ai'] = AIConfig(**ai_config)
            
            # 更新日志配置
            log_config = {k: v for k, v in env_config.items() if k.startswith('LOG_')}
            if log_config:
                kwargs['log'] = LogConfig(**log_config)
            
            # 更新数据库配置
            db_config = {k: v for k, v in env_config.items() if k.startswith('DB_')}
            if db_config:
                kwargs['db'] = DatabaseConfig(**db_config)
            
            # 更新存储配置
            storage_config = {k: v for k, v in env_config.items() if k.startswith('STORAGE_')}
            if storage_config:
                # 处理布尔值
                if 'STORAGE_ENABLED' in storage_config:
                    storage_config['STORAGE_ENABLED'] = storage_config['STORAGE_ENABLED'].lower() == 'true'
                kwargs['storage'] = StorageConfig(**storage_config)
            
            # 更新基础配置
            if 'APP_NAME' in env_config:
                kwargs['APP_NAME'] = env_config['APP_NAME']
            if 'APP_VERSION' in env_config:
                kwargs['APP_VERSION'] = env_config['APP_VERSION']
            if 'DEBUG' in env_config:
                kwargs['DEBUG'] = env_config['DEBUG'].lower() == 'true'
        
        super().__init__(**kwargs)
        self._init_directories()
        self._validate_api_key()
        
        # 只在主进程中打印配置信息
        if not os.environ.get('RELOAD_PROCESS'):
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
        if not self.ai.AI_ZHIPU_API_KEY:
            import warnings
            warnings.warn(
                "AI_ZHIPU_API_KEY 未设置！请在 .env 文件中设置 AI_ZHIPU_API_KEY",
                RuntimeWarning
            )
    
    def _print_debug_info(self):
        """打印调试信息"""
        print("\n=== 配置加载信息 ===")
        print(f"项目根目录: {self.BASE_DIR}")
        print(f"环境变量文件: {self.model_config.get('env_file', '未指定')}")
        print(f"环境变量文件编码: {self.model_config.get('env_file_encoding', '未指定')}")
        
        # 日志配置
        print("\n日志配置:")
        print(f"配置文件 LOG_LEVEL: {self.log.LOG_LEVEL}")
        print(f"配置文件 LOG_FILE: {self.log.LOG_FILE}")
        
        # AI配置
        print("\nAI配置:")
        print(f"配置文件 AI_ZHIPU_MODEL_CHAT: {self.ai.AI_ZHIPU_MODEL_CHAT}")
        print(f"配置文件 AI_ZHIPU_MODEL_VISION: {self.ai.AI_ZHIPU_MODEL_VISION}")
        
        # LangSmith配置
        print("\nLangSmith配置:")
        print(f"追踪功能: {'已启用' if self.ai.LANGSMITH_TRACING else '未启用'}")
        if self.ai.LANGSMITH_TRACING:
            print(f"项目名称: {self.ai.LANGSMITH_PROJECT}")
            print(f"API密钥: ***{self.ai.LANGSMITH_API_KEY[-4:]}")
        
        # 存储配置
        print("\n存储配置:")
        print(f"存储功能: {'已启用' if self.storage.STORAGE_ENABLED else '未启用'}")
        if self.storage.STORAGE_ENABLED:
            print(f"存储提供商: {self.storage.STORAGE_PROVIDER}")
            print(f"存储桶: {self.storage.STORAGE_BUCKET_NAME}")
        
        print("\n其他配置:")
        print(f"调试模式: {self.DEBUG}")
        print("===================\n")

# 创建全局配置实例
settings = Settings()

# 导出配置实例
__all__ = ["settings"]