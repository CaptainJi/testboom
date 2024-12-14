import sys
import os
from loguru import logger
from pathlib import Path
from ..config.settings import settings

def setup_logger():
    """配置日志"""
    # 确保使用绝对路径
    log_path = Path(os.path.abspath(settings.LOG_PATH))
    log_path.mkdir(exist_ok=True)
    
    # 移除默认的处理器
    logger.remove()
    
    # 强制使用配置文件中的日志级别
    log_level = os.getenv('LOG_LEVEL', settings.LOG_LEVEL).upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level = "DEBUG"  # 如果配置无效，默认使用 DEBUG
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # 添加文件处理器
    logger.add(
        str(log_path / "testboom.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="1 day",
        retention="7 days"
    )
    
    return logger

# 初始化日志配置
logger = setup_logger()