"""
测试ChatGraph功能
"""

import pytest
import asyncio
from src.ai_core.graph.chat import ChatGraph
from src.config.settings import settings
from src.ai_core.graph.base import BaseGraph

@pytest.mark.asyncio
async def test_chat_basic():
    """测试基本对话功能"""
    chat_graph = ChatGraph()
    
    messages = [{
        "role": "user",
        "content": "你好，请介绍一下自己。"
    }]
    
    response = await chat_graph.chat(messages)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_chat_with_template():
    """测试使用模板的对话功能"""
    chat_graph = ChatGraph()
    
    messages = [{
        "role": "user",
        "content": "分析这段代码的功能。"
    }]
    
    response = await chat_graph.chat(
        messages=messages,
        template_name="code_analysis",
        template_args={"code": "print('Hello, World!')"}
    )
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_chat_with_json_response():
    """测试JSON格式响应"""
    chat_graph = ChatGraph()
    
    messages = [{
        "role": "user",
        "content": "生成一个测试用例JSON。"
    }]
    
    response = await chat_graph.chat(
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    assert response is not None
    assert isinstance(response, str)
    assert response.strip().startswith("{")
    assert response.strip().endswith("}")

@pytest.mark.asyncio
async def test_chat_with_timeout():
    """测试超时设置"""
    chat_graph = ChatGraph()
    
    messages = [{
        "role": "user",
        "content": "请生成一个复杂的分析报告。"
    }]
    
    response = await chat_graph.chat(
        messages=messages,
        timeout=30  # 30秒超时
    )
    
    assert response is not None
    assert isinstance(response, str)

@pytest.mark.asyncio
async def test_chat_with_error():
    """测试错误处理"""
    chat_graph = ChatGraph()
    
    # 空消息列表应该返回None
    response = await chat_graph.chat([])
    assert response is None
    
    # 无效的模板名称
    response = await chat_graph.chat(
        messages=[{"role": "user", "content": "test"}],
        template_name="non_existent_template"
    )
    assert response is not None  # 应该仍然返回响应，因为模板是可选的

@pytest.mark.asyncio
async def test_chat_with_system_message():
    """测试系统消息"""
    chat_graph = ChatGraph()
    
    messages = [
        {
            "role": "system",
            "content": "你是一个专业的测试工程师。"
        },
        {
            "role": "user",
            "content": "设计一个登录功能的测试用例。"
        }
    ]
    
    response = await chat_graph.chat(
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    assert response is not None
    assert isinstance(response, str)
    assert response.strip().startswith("{")

@pytest.mark.asyncio
async def test_chat_with_tracing():
    """测试带追踪的对话功能"""
    # 初始化 LangSmith
    base = BaseGraph()  # 这会初始化 LangSmith
    
    chat_graph = ChatGraph()
    
    messages = [{
        "role": "user",
        "content": "你好，请用JSON格式回答：1. 你是谁？2. 你能做什么？"
    }]
    
    # 使用JSON格式以便于验证响应
    response = await chat_graph.chat(
        messages=messages,
        response_format={"type": "json_object"},
        timeout=30,
        metadata={
            "test_name": "chat_with_tracing",
            "test_type": "integration",
            "test_purpose": "验证LangSmith追踪功能"
        }
    )
    
    assert response is not None
    assert isinstance(response, str)
    assert response.strip().startswith("{")
    assert response.strip().endswith("}")
    
    # 等待一段时间确保追踪完成
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_chat_basic())
    asyncio.run(test_chat_with_template())
    asyncio.run(test_chat_with_json_response())
    asyncio.run(test_chat_with_timeout())
    asyncio.run(test_chat_with_error())
    asyncio.run(test_chat_with_system_message())
    asyncio.run(test_chat_with_tracing()) 