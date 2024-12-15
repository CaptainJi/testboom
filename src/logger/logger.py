import os
from pathlib import Path
from loguru import logger
from src.config.settings import settings

def setup_logger():
    """配置日志记录器"""
    # 创建日志目录
    log_dir = Path(settings.log.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sink=lambda msg: print(msg),
        level=settings.log.LOG_LEVEL,
        format=settings.log.LOG_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 添加文件处理器
    logger.add(
        sink=settings.log.LOG_FILE,
        level=settings.log.LOG_LEVEL,
        format=settings.log.LOG_FORMAT,
        rotation=settings.log.LOG_ROTATION,
        retention=settings.log.LOG_RETENTION,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    
    return logger

# 创建全局日志实例
logger = setup_logger()

# 导出日志实例
__all__ = ["logger"]