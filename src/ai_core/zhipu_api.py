import base64
import os
from typing import List, Dict, Any, Optional, Union
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.logger.logger import logger

class ZhipuAI:
    """智谱AI API封装(基于LangChain)"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
        # 通用对话模型
        self.chat_model = ChatZhipuAI(
            api_key=settings.ZHIPU_API_KEY,
            model_name=settings.ZHIPU_MODEL_CHAT,
            temperature=0.7,
            top_p=0.7,
            streaming=False
        )
        
        # 多模态模型
        self.vision_model = ChatZhipuAI(
            api_key=settings.ZHIPU_API_KEY,
            model_name=settings.ZHIPU_MODEL_VISION,
            temperature=0.7,
            top_p=0.7,
            streaming=False
        )
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Any]:
        """转换消息格式
        
        Args:
            messages: 原始消息列表
            
        Returns:
            List[Any]: LangChain消息列表
        """
        message_map = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage
        }
        
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role in message_map:
                message_class = message_map[role]
                langchain_messages.append(message_class(content=content))
                
        return langchain_messages
    
    def chat(self, messages: List[Dict[str, Any]]) -> Optional[Any]:
        """发送对话请求
        
        Args:
            messages: 对话历史记录列表
            
        Returns:
            智谱AI的原始响应
        """
        try:
            # 转换消息格式
            langchain_messages = self._convert_messages(messages)
            
            # 使用通用对话模型
            response = self.chat_model.invoke(langchain_messages)
            return response
        except Exception as e:
            logger.error(f"智谱AI对话请求失败: {e}")
            return None
    
    def chat_with_images(self, messages: List[Dict[str, Any]], images: List[str]) -> Optional[Any]:
        """发送带图片的对话请求
        
        Args:
            messages: 对话历史记录列表
            images: 图片文件路径列表
            
        Returns:
            智谱AI的原始响应
        """
        try:
            # 将图片转换为base64编码
            image_list = []
            for image_path in images:
                if not os.path.exists(image_path):
                    logger.error(f"图片文件不存在: {image_path}")
                    continue
                    
                with open(image_path, "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode('utf-8')
                    image_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image
                        }
                    })
            
            if not image_list:
                logger.error("没有有效的图片文件")
                return None
            
            # 构建多模态消息
            content = []
            # 先添加图片
            content.extend(image_list)
            
            # 再添加文本
            for msg in messages:
                if msg["role"] == "user":
                    if isinstance(msg["content"], str):
                        content.append({
                            "type": "text",
                            "text": msg["content"]
                        })
                    elif isinstance(msg["content"], list):
                        for item in msg["content"]:
                            if item["type"] == "text":
                                content.append(item)
            
            # 构建完整的消息列表
            langchain_messages = [HumanMessage(content=content)]
            
            # 使用多模态模型
            response = self.vision_model.invoke(langchain_messages)
            return response
        except Exception as e:
            logger.error(f"智谱AI图片对话请求失败: {e}")
            return None
    
    def parse_response(self, response: Any) -> Optional[str]:
        """解析智谱AI的响应
        
        Args:
            response: 智谱AI的原始响应
            
        Returns:
            解析后的回复文本
        """
        try:
            if hasattr(response, "content"):
                return response.content
            elif isinstance(response, str):
                return response
            return None
        except Exception as e:
            logger.error(f"解析智谱AI响应失败: {e}")
            return None
