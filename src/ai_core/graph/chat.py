"""
基于LangGraph的对话管理器
"""

from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict, NotRequired
from loguru import logger
from langgraph.graph import StateGraph, START, END
from src.ai_core.zhipu_api import ZhipuAI

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
                # TODO: 从模板生成提示词
                prompt = f"使用{template_name}模板，参数：{template_args}"
                messages.insert(0, {"role": "system", "content": prompt})
                
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
            
            # 调用AI生成响应
            response = await self.ai.chat(
                messages=messages,
                timeout=timeout
            )
            
            # 处理JSON格式
            if response_format and response_format.get("type") == "json_object":
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
        timeout: int = None
    ) -> str:
        """聊天入口"""
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
            result = await self.workflow.ainvoke(state)
            
            if result.get("error"):
                logger.error(f"聊天失败: {result['error']}")
                return None
                
            return result.get("response")
            
        except Exception as e:
            logger.error(f"聊天异常: {str(e)}")
            return None 