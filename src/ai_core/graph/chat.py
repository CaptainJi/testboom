"""
基于LangGraph的对话管理器
"""

from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict, NotRequired
from loguru import logger
from langgraph.graph import StateGraph, START, END
from src.ai_core.zhipu_api import ZhipuAI
from src.ai_core.prompt_template import PromptTemplate
from src.config.settings import settings
from pathlib import Path
import uuid
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks import BaseCallbackHandler

class ChatState(TypedDict):
    messages: List[Dict[str, str]]
    response: Optional[str]
    error: Optional[str]
    template_name: NotRequired[str]
    template_args: NotRequired[Dict[str, Any]]
    response_format: NotRequired[Dict[str, str]]
    timeout: NotRequired[int]

class ChatGraph:
    def __init__(self):
        # 初始化AI客户端
        self.ai = ZhipuAI()
        
        # 初始化提示词模板
        template_dir = str(settings.BASE_DIR / "resources/prompts")
        self.template = PromptTemplate(template_dir=template_dir)
        logger.info(f"已加载提示词模板，目录: {template_dir}")
        
        # 初始化图
        self.graph = StateGraph(state_schema=ChatState)
        
        # 添加节点
        self.graph.add_node("process_message", self._process_message)
        self.graph.add_node("generate_response", self._generate_response)
        
        # 添加边
        self.graph.add_edge(START, "process_message")
        self.graph.add_edge("process_message", "generate_response")
        self.graph.add_edge("generate_response", END)
        
        # 编译图
        self.workflow = self.graph.compile()

    def get_config(
        self,
        response_format: str = "text",
        timeout: int = 60,
        callbacks: List[BaseCallbackHandler] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> RunnableConfig:
        """获取配置

        Args:
            response_format (str, optional): 响应格式. Defaults to "text".
            timeout (int, optional): 超时时间. Defaults to 60.
            callbacks (List[BaseCallbackHandler], optional): 回调函数列表. Defaults to None.
            tags (List[str], optional): 标签列表. Defaults to None.
            metadata (Dict[str, Any], optional): 元数据. Defaults to None.

        Returns:
            RunnableConfig: 配置字典
        """
        # 基础配置
        config = {
            "configurable": {
                "response_format": response_format,
                "timeout": timeout,
                "run_name": str(uuid.uuid4()),
            },
            "metadata": {
                "template_name": "chat",
                "response_format": response_format,
                "timeout": timeout,
            },
            "tags": tags or ["testboom", "chat"],
            "callbacks": callbacks or [],
            "recursion_limit": 25,  # 防止无限递归
            "run_name": f"testboom-chat-{uuid.uuid4()}",  # 确保每次运行都有唯一的名称
        }

        # 合并额外的元数据
        if metadata:
            config["metadata"].update(metadata)

        return config

    async def _process_message(self, state: ChatState) -> ChatState:
        """处理消息"""
        try:
            messages = state.get("messages", [])
            if not messages:
                state["error"] = "消息列表为空"
                return state
                
            # 处理模板
            template_name = state.get("template_name")
            template_args = state.get("template_args", {})
            if template_name:
                try:
                    # 使用模板生成提示词
                    prompt = self.template.render(template_name, **(template_args or {}))
                    if prompt:
                        messages.insert(0, {"role": "system", "content": prompt})
                    else:
                        logger.warning(f"模板 {template_name} 渲染失败，将继续处理原始消息")
                except Exception as e:
                    logger.warning(f"处理模板 {template_name} 失败: {str(e)}，将继续处理原始消息")
                
            state["messages"] = messages
            return state
            
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            state["error"] = str(e)
            return state

    async def _generate_response(self, state: ChatState) -> ChatState:
        """生成响应"""
        try:
            if state.get("error"):
                return state
                
            messages = state.get("messages", [])
            response_format = state.get("response_format")
            timeout = state.get("timeout", 60)
            
            # 获取运行配置
            config = self.get_config(
                callbacks=[],
                tags=["testboom", "chat"],
                metadata={
                    "template_name": state.get("template_name"),
                    "response_format": response_format,
                    "timeout": timeout
                }
            )
            
            # 检查是否包含图片
            image_paths = []
            for msg in messages:
                if isinstance(msg, dict) and msg.get("images"):
                    image_paths.extend(msg["images"])
            
            # 根据是否有图片选择不同的调用方法
            if image_paths:
                logger.info(f"使用视觉模型处理 {len(image_paths)} 张图片")
                response = await self.ai.chat_with_images(
                    messages=messages,
                    image_paths=image_paths,
                    task_id=state.get("task_id"),
                    config=config
                )
            else:
                logger.info("使用对话模型处理请求")
                response = await self.ai.chat(
                    messages=messages,
                    response_format=response_format,
                    timeout=timeout,
                    config=config
                )
            
            # 处理JSON格式
            if response and response_format and response_format.get("type") == "json_object":
                if not response.strip().startswith("{"):
                    # 提取JSON内容
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                    if json_match:
                        response = json_match.group(1)
                    else:
                        response = "{}"
            
            state["response"] = response
            return state
            
        except Exception as e:
            logger.error(f"生成响应失败: {str(e)}")
            state["error"] = str(e)
            return state

    async def chat(
        self,
        messages: List[Dict[str, str]],
        template_name: str = None,
        template_args: Dict[str, Any] = None,
        response_format: Dict[str, str] = None,
        timeout: int = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """聊天入口

        Args:
            messages: 消息列表
            template_name: 模板名称
            template_args: 模板参数
            response_format: 响应格式
            timeout: 超时时间
            metadata: 元数据

        Returns:
            str: 响应内容
        """
        try:
            # 准备初始状态
            state: ChatState = {
                "messages": messages,
                "response": None,
                "error": None
            }
            
            if template_name:
                state["template_name"] = template_name
                state["template_args"] = template_args
                
            if response_format:
                state["response_format"] = response_format
                
            if timeout:
                state["timeout"] = timeout
                
            # 执行工作流
            result = await self.workflow.ainvoke(
                state,
                config=self.get_config(
                    response_format=response_format,
                    timeout=timeout,
                    metadata=metadata
                )
            )
            
            if result.get("error"):
                logger.error(f"聊天失败: {result['error']}")
                return None
                
            return result.get("response")
            
        except Exception as e:
            logger.error(f"聊天异常: {str(e)}")
            return None 