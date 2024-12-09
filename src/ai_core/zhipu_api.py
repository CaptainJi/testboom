from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.chat_models import ChatZhipuAI
from ..config.config import settings
from ..logger.logger import logger

class ZhipuAI:
    """智谱AI API封装类(基于LangChain)"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
        self.llm = ChatZhipuAI(
            api_key=settings.ZHIPUAI_API_KEY,
            model_name="glm-4",  # 默认使用GLM-4模型
            temperature=0.7,
            top_p=0.95,
            streaming=False
        )
        self.llm_4v = ChatZhipuAI(
            api_key=settings.ZHIPUAI_API_KEY,
            model_name="glm-4v",  # 多模态模型
            temperature=0.7,
            top_p=0.95,
            streaming=False
        )
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Any]:
        """转换消息格式
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[Any]: LangChain消息列表
        """
        langchain_messages = []
        for msg in messages:
            content = msg["content"]
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=content))
        return langchain_messages
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """发送对话请求
        
        Args:
            messages: 对话历史记录列表
            model: 模型名称,默认使用实例化时指定的模型
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        try:
            # 选择合适的模型实例
            llm = self.llm
            if model == "glm-4v":
                llm = self.llm_4v
            elif model and model != self.llm.model_name:
                llm = ChatZhipuAI(
                    api_key=settings.ZHIPUAI_API_KEY,
                    model_name=model,
                    temperature=0.7,
                    top_p=0.95,
                    streaming=False
                )
            
            # 转换消息格式
            langchain_messages = self._convert_messages(messages)
            
            # 发送请求
            response = llm.invoke(langchain_messages)
            return response
            
        except Exception as e:
            logger.error(f"智谱AI API调用失败: {str(e)}")
            raise
    
    def chat_with_images(self, messages: List[Dict[str, str]], 
                        images: List[str], model: Optional[str] = None) -> Dict[str, Any]:
        """发送带图片的对话请求
        
        Args:
            messages: 对话历史记录列表
            images: 图片URL或Base64列表
            model: 模型名称,默认使用实例化时指定的模型
            
        Returns:
            Dict[str, Any]: API响应结果
        """
        try:
            # 使用GLM-4V模型
            llm = self.llm_4v
            
            # 构建多模态消息
            langchain_messages = []
            for msg in messages[:-1]:  # 处理除最后一条外的消息
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # 处理最后一条消息,添加图片
            if messages:
                last_msg = messages[-1]
                if last_msg["role"] == "user":
                    content = [{
                        "type": "text",
                        "text": last_msg["content"]
                    }]
                    for image in images:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": image}
                        })
                    langchain_messages.append(HumanMessage(content=content))
            
            # 发送请求
            response = llm.invoke(langchain_messages)
            return response
            
        except Exception as e:
            logger.error(f"智谱AI API带图片调用失败: {str(e)}")
            raise
    
    @staticmethod
    def parse_response(response: Any) -> Optional[str]:
        """解析API响应
        
        Args:
            response: API响应结果
            
        Returns:
            Optional[str]: 解析出的回复内容,失败返回None
        """
        try:
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                logger.error(f"API响应格式错误: {response}")
                return None
        except Exception as e:
            logger.error(f"解析API响应失败: {str(e)}")
            return None
