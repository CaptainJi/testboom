import pytest
from pathlib import Path
from src.config.config import settings
from src.logger.logger import logger
from src.utils.common import ensure_dir, safe_file_write, safe_file_read

def test_config():
    """测试配置加载"""
    assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert Path(settings.LOG_PATH).exists()
    assert Path(settings.RESOURCE_PATH).exists()

def test_logger():
    """测试日志功能"""
    logger.debug("测试debug日志")
    logger.info("测试info日志")
    logger.warning("测试warning日志")
    logger.error("测试error日志")
    assert Path(settings.LOG_PATH).exists()
    assert list(Path(settings.LOG_PATH).glob("*.log"))

def test_utils():
    """测试工具函数"""
    # 测试目录创建
    test_dir = Path("tests/test_data/test_dir")
    created_dir = ensure_dir(test_dir)
    assert created_dir.exists()
    
    # 测试文件写入和读取
    test_file = test_dir / "test.txt"
    test_content = "测试内容"
    assert safe_file_write(test_file, test_content)
    assert safe_file_read(test_file) == test_content 