import pytest
from pathlib import Path
from src.ai_core.prompt_template import PromptTemplate
from src.logger.logger import logger

def test_prompt_template():
    """测试Prompt模板功能"""
    # 使用测试目录
    template_dir = "resources/prompts"
    template_manager = PromptTemplate(template_dir)
    
    # 测试加载模板
    assert template_manager.get_template("requirement_analysis") is not None
    assert template_manager.get_template("testcase_generation") is not None
    assert template_manager.get_template("testcase_understanding") is not None
    
    # 测试渲染需求分析模板
    content = "这是一个示例需求文档"
    result = template_manager.render(
        template_name="requirement_analysis",
        content=content
    )
    assert result is not None
    assert content in result
    logger.info(f"\n需求分析模板渲染结果:\n{result}")
    
    # 测试渲染测试用例生成模板
    content = "这是需求分析的结果"
    result = template_manager.render(
        template_name="testcase_generation",
        content=content
    )
    assert result is not None
    assert content in result
    assert "|用例ID|所属模块|" in result
    logger.info(f"\n用例生成模板渲染结果:\n{result}")
    
    # 测试渲染测试用例理解模板
    content = "这是一个测试用例"
    result = template_manager.render(
        template_name="testcase_understanding",
        content=content
    )
    assert result is not None
    assert content in result
    logger.info(f"\n用例理解模板渲染结果:\n{result}")
    
    # 测试添加新模板
    assert template_manager.add_template(
        "custom_template",
        "这是一个自定义模板: $content"
    )
    
    # 测试保存和加载
    assert template_manager.save_templates()
    
    # 创建新实例测试加载
    new_manager = PromptTemplate(template_dir)
    result = new_manager.render(
        template_name="custom_template",
        content="测试内容"
    )
    assert result == "这是一个自定义模板: 测试内容"
    logger.info(f"\n自定义模板渲染结果:\n{result}") 