"""
测试 LangSmith 配置
"""

import pytest
import os
from langsmith import Client
from src.config.settings import settings
from src.ai_core.graph.base import BaseGraph

@pytest.mark.asyncio
async def test_langsmith_connection():
    """测试 LangSmith 连接"""
    try:
        # 确保环境变量已设置
        assert settings.ai.LANGSMITH_API_KEY, "LANGSMITH_API_KEY 未设置"
        assert settings.ai.LANGSMITH_PROJECT, "LANGSMITH_PROJECT 未设置"
        assert settings.ai.LANGSMITH_ENDPOINT, "LANGSMITH_ENDPOINT 未设置"
        assert settings.ai.LANGSMITH_TRACING, "LANGSMITH_TRACING 未设置"
        
        # 设置环境变量
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.ai.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.ai.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.ai.LANGSMITH_PROJECT
        
        # 创建 LangSmith 客户端
        client = Client()
        
        # 创建项目(如果不存在)
        try:
            client.create_project(settings.ai.LANGSMITH_PROJECT)
            print(f"成功创建项目: {settings.ai.LANGSMITH_PROJECT}")
        except Exception as e:
            if "already exists" not in str(e):
                raise e
            print(f"项目 {settings.ai.LANGSMITH_PROJECT} 已存在")
        
        # 测试连接
        projects = client.list_projects()
        project_names = [p.name for p in projects]
        
        # 验证项目是否存在
        assert settings.ai.LANGSMITH_PROJECT in project_names, f"项目 {settings.ai.LANGSMITH_PROJECT} 不存在"
        
        print(f"成功连接到 LangSmith，可用项目: {project_names}")
        
    except Exception as e:
        pytest.fail(f"LangSmith 连接测试失败: {str(e)}")

def test_langsmith_config():
    """测试 LangSmith 配置"""
    # 初始化 LangSmith
    base = BaseGraph()
    
    # 检查环境变量
    print("\n环境变量:")
    print(f"LANGSMITH_API_KEY: {bool(os.getenv('LANGSMITH_API_KEY'))}")
    print(f"LANGCHAIN_API_KEY: {bool(os.getenv('LANGCHAIN_API_KEY'))}")
    print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
    print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
    
    # 检查配置
    print("\n配置:")
    print(f"LANGSMITH_TRACING: {settings.ai.LANGSMITH_TRACING}")
    print(f"LANGSMITH_PROJECT: {settings.ai.LANGSMITH_PROJECT}")
    print(f"LANGSMITH_API_KEY: {bool(settings.ai.LANGSMITH_API_KEY)}")
    
    # 断言
    assert os.getenv('LANGSMITH_API_KEY') is not None
    assert os.getenv('LANGCHAIN_API_KEY') is not None
    assert os.getenv('LANGCHAIN_PROJECT') == 'testboom'
    assert os.getenv('LANGCHAIN_TRACING_V2') == 'true'
    assert settings.ai.LANGSMITH_TRACING is True
    assert settings.ai.LANGSMITH_PROJECT == 'testboom'
    assert settings.ai.LANGSMITH_API_KEY is not None
    
    # 测试 LangSmith 连接
    try:
        client = Client()
        projects = list(client.list_projects())
        print("\nLangSmith 项目列表:")
        for project in projects:
            print(f"- {project.name}")
            
        # 确保 testboom 项目存在
        project_names = [p.name for p in projects]
        if 'testboom' not in project_names:
            print("\n创建 testboom 项目...")
            client.create_project('testboom')
            print("项目创建成功")
            
    except Exception as e:
        pytest.fail(f"LangSmith 连接测试失败: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_langsmith_config()) 