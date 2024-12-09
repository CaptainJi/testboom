import pytest
from pathlib import Path
from src.ai_core.zhipu_api import ZhipuAI
from src.ai_core.chat_manager import ChatManager
from src.ai_core.prompt_template import PromptTemplate
from src.logger.logger import logger

def test_zhipu_api():
    """测试智谱AI API封装"""
    client = ZhipuAI()
    
    # 测试基本对话
    question = "你是谁?请简单介绍一下你自己。"
    logger.info(f"\n提问: {question}")
    
    response = client.chat([{
        "role": "user",
        "content": question
    }])
    assert response is not None
    
    reply = client.parse_response(response)
    assert reply is not None
    logger.info(f"\n回复: {reply}")

def test_chat_manager():
    """测试对话管理器"""
    manager = ChatManager()
    
    # 测试添加消息
    manager.add_message("user", "你好")
    manager.add_message("assistant", "你好!有什么我可以帮你的吗?")
    assert len(manager.history) == 2
    
    # 测试清空历史
    manager.clear_history()
    assert len(manager.history) == 0
    
    # 测试对话
    question = "解释一下什么是自动化测试?"
    logger.info(f"\n提问: {question}")
    
    reply = manager.chat(question)
    assert reply is not None
    logger.info(f"\n回复: {reply}")
    assert len(manager.history) == 2  # user消息和assistant回复

def test_prompt_template():
    """测试Prompt模板管理"""
    template_dir = "tests/test_data/prompts"
    template_manager = PromptTemplate(template_dir)
    
    # 测试添加模板
    assert template_manager.add_template(
        "test",
        "你好,$name,今天是$date"
    )
    
    # 测试渲染模板
    result = template_manager.render(
        template_name="test",
        name="张三",
        date="2024-01-01"
    )
    assert result == "你好,张三,今天是2024-01-01"
    logger.info(f"\n模板渲染结果: {result}")
    
    # 测试保存和加载
    assert template_manager.save_templates()
    
    # 创建新实例测试加载
    new_manager = PromptTemplate(template_dir)
    result = new_manager.render(
        template_name="test",
        name="李四",
        date="2024-01-02"
    )
    assert result == "你好,李四,今天是2024-01-02"
    logger.info(f"\n模板渲染结果: {result}") 