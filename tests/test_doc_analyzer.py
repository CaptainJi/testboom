import pytest
from pathlib import Path
from src.doc_analyzer.doc_analyzer import DocAnalyzer
from src.logger.logger import logger

def test_doc_analyzer():
    """测试文档分析器"""
    # 准备测试数据
    zip_path = "tests/test_data/test_prd.zip"
    assert Path(zip_path).exists(), f"测试文件不存在: {zip_path}"
    
    # 创建分析器
    analyzer = DocAnalyzer("tests/test_data/temp")
    
    # 分析PRD
    logger.info("\n开始分析PRD文档:")
    result = analyzer.analyze_prd(zip_path)
    assert result is not None
    logger.info(f"\n分析结果:\n{result}")
    
    # 验证临时目录已清理
    assert not Path("tests/test_data/temp").exists() 