import pytest
from pathlib import Path
from src.doc_analyzer.doc_analyzer import DocAnalyzer
from src.logger.logger import logger
from tests.test_base import log_test_step, verify_testcase_structure

def test_doc_analyzer():
    """测试文档分析器
    
    测试流程:
    1. 多模态模型分析PRD图片
    2. 通用模型汇总分析生成测试用例
    """
    # 准备测试数据
    zip_path = "tests/test_data/test_prd.zip"
    assert Path(zip_path).exists(), f"测试文件不存在: {zip_path}"
    
    # 创建分析器
    analyzer = DocAnalyzer("tests/test_data/temp")
    
    # 分析PRD
    log_test_step("开始分析PRD文档:")
    result = analyzer.analyze_prd(zip_path)
    
    # 验证基本结构
    assert result is not None
    assert isinstance(result, dict)
    assert all(key in result for key in ['summary', 'testcases', 'details'])
    
    # 验证多模态分析结果
    assert isinstance(result['details'], dict)
    assert 'images' in result['details']
    assert isinstance(result['details']['images'], list)
    assert len(result['details']['images']) > 0  # 确保有图片分析结果
    
    # 验证每个图片的分析结果
    for image_result in result['details']['images']:
        # 验证基本字段
        assert isinstance(image_result, dict)
        assert 'file' in image_result
        assert 'content' in image_result
        assert 'features' in image_result
        
        # 验证内容不为空
        assert len(image_result['content']) > 0
        
        # 验证特征结构
        features = image_result['features']
        assert isinstance(features, dict)
        assert all(key in features for key in [
            'functionality', 'workflow', 'data_flow',
            'interfaces', 'constraints', 'exceptions'
        ])
    
    # 验证通用模型汇总结果
    assert isinstance(result['summary'], str)
    assert len(result['summary']) > 0
    log_test_step(f"需求汇总:\n{result['summary']}")
    
    # 验证生成的测试用例
    assert isinstance(result['testcases'], list)
    if result['testcases']:  # 如果生成了测试用例
        log_test_step(f"生成的测试用例数量: {len(result['testcases'])}")
        for testcase in result['testcases']:
            verify_testcase_structure(testcase)
        
        # 输出第一个测试用例作为示例
        if result['testcases']:
            log_test_step(f"测试用例示例:\n{result['testcases'][0]}")
    
    # 验证临时目录已清理
    assert not Path("tests/test_data/temp").exists()