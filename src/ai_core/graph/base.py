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
        """初始化LangSmith配置"""
        try:
            if settings.ai.LANGSMITH_TRACING_ENABLED:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_ENDPOINT"] = settings.ai.LANGSMITH_ENDPOINT
                os.environ["LANGCHAIN_API_KEY"] = settings.ai.LANGSMITH_API_KEY
                os.environ["LANGCHAIN_PROJECT"] = settings.ai.LANGSMITH_PROJECT
                logger.info("LangSmith追踪已启用")
            else:
                logger.info("LangSmith追踪未启用")
        except Exception as e:
            logger.error(f"初始化LangSmith配置失败: {str(e)}")
    
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
            "tracing_enabled": settings.ai.LANGSMITH_TRACING_ENABLED
        }
        config.update(kwargs)
        return config 