import os
from pathlib import Path
from loguru import logger
from src.config.settings import settings

def setup_logger():
    """配置日志记录器"""
    # 移除默认的处理器
    logger.remove()
    
    # 确保日志目录存在
    log_dir = Path(settings.log.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 转换日志级别为大写
    log_level = settings.log.LOG_LEVEL.upper()
    
    # 添加调试信息
    print(f"当前日志级别设置为: {log_level}")
    
    # 添加控制台处理器
    logger.add(
        sink=lambda msg: print(msg),
        level=log_level,
        format=settings.log.LOG_FORMAT,
        colorize=True,
        diagnose=True,  # 启用详细的异常诊断
        backtrace=True  # 启用回溯信息
    )
    
    # 添加文件处理器
    logger.add(
        sink=settings.log.LOG_FILE,
        level=log_level,
        format=settings.log.LOG_FORMAT,
        rotation=settings.log.LOG_ROTATION,
        retention=settings.log.LOG_RETENTION,
        encoding="utf-8",
        diagnose=True,  # 启用详细的异常诊断
        backtrace=True  # 启用回溯信息
    )
    
    # 添加一条测试日志
    logger.debug("Logger initialized with level: {}", log_level)
    
    return logger

# 导出配置好的logger实例
logger = setup_logger()