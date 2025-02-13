"""
LangGraph基础组件
"""

from typing import Dict, Any, Optional, List, TypedDict, Annotated
from typing_extensions import TypedDict
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from src.config.settings import settings
from src.logger.logger import logger
import os
import uuid

class BaseState(TypedDict):
    """基础状态定义"""
    messages: List[Dict[str, str]]
    response: Optional[str]
    error: Optional[str]

class BaseGraph:
    """LangGraph基础类"""
    
    def __init__(self):
        """初始化基础图"""
        self._init_langsmith()
        self.graph = StateGraph(state_schema=BaseState)
    
    def _init_langsmith(self):
        """初始化 LangSmith 追踪"""
        if settings.ai.LANGSMITH_TRACING:
            # 设置环境变量
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = settings.ai.LANGSMITH_ENDPOINT
            os.environ["LANGCHAIN_API_KEY"] = settings.ai.LANGSMITH_API_KEY
            os.environ["LANGSMITH_API_KEY"] = settings.ai.LANGSMITH_API_KEY  # 同时设置两个 API KEY
            os.environ["LANGCHAIN_PROJECT"] = settings.ai.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_SESSION"] = str(uuid.uuid4())
            os.environ["LANGCHAIN_TAGS"] = "testboom"
            os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"

            logger.info(
                "LangSmith 追踪已启用",
                extra={
                    "endpoint": settings.ai.LANGSMITH_ENDPOINT,
                    "project": settings.ai.LANGSMITH_PROJECT,
                    "session": os.environ["LANGCHAIN_SESSION"],
                    "tags": os.environ["LANGCHAIN_TAGS"],
                    "api_key": "***" + settings.ai.LANGSMITH_API_KEY[-4:]  # 只显示最后4位
                }
            )
        else:
            # 清理环境变量
            for key in [
                "LANGCHAIN_TRACING_V2",
                "LANGCHAIN_ENDPOINT",
                "LANGCHAIN_API_KEY",
                "LANGSMITH_API_KEY",
                "LANGCHAIN_PROJECT",
                "LANGCHAIN_SESSION",
                "LANGCHAIN_TAGS",
                "LANGCHAIN_CALLBACKS_BACKGROUND"
            ]:
                os.environ.pop(key, None)
            logger.info("LangSmith 追踪已禁用")
    
    def get_config(self, **kwargs) -> RunnableConfig:
        """获取运行配置
        
        Args:
            **kwargs: 额外的配置参数
            
        Returns:
            RunnableConfig: 运行配置
        """
        config = {
            "callbacks": [],
            "tags": ["testboom"],
            "metadata": {},
            "tracing": settings.ai.LANGSMITH_TRACING
        }
        config.update(kwargs)
        return config 