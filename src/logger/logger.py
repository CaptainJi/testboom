import sys
from loguru import logger
from pathlib import Path
from ..config.config import settings

def setup_logger():
    """配置日志"""
    # 确保日志目录存在
    log_path = Path(settings.LOG_PATH)
    log_path.mkdir(exist_ok=True)
    
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # 添加文件处理器
    logger.add(
        str(log_path / "testboom.log"),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="1 day",
        retention="7 days"
    )
    
    return logger

logger = setup_logger() 