import base64
import os
import json
import time
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
            temperature=0.2,  # 降低随机性
            top_p=0.2,  # 降低随机性
            streaming=False
        )
        
        # 多模态模型
        self.vision_model = ChatZhipuAI(
            api_key=settings.ZHIPU_API_KEY,
            model_name=settings.ZHIPU_MODEL_VISION,
            temperature=0.2,  # 降低随机性
            top_p=0.2,  # 降低随机性
            streaming=False
        )
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 5  # 增加重试间隔到5秒
        self.retry_backoff = 2  # 重试间隔倍数
    
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
    
    def chat(self, messages: List[Dict[str, Any]], response_format: Optional[Dict[str, str]] = None) -> Optional[Any]:
        """发送对话请求
        
        Args:
            messages: 对话历史记录列表
            response_format: 响应格式,如 {"type": "json_object"}
            
        Returns:
            智谱AI的原始响应
        """
        retries = 0
        current_delay = self.retry_delay
        
        while retries < self.max_retries:
            try:
                # 转换消息格式
                langchain_messages = self._convert_messages(messages)
                
                # 如果需要 JSON 响应，添加 system 消息
                if response_format and response_format.get("type") == "json_object":
                    system_msg = SystemMessage(content="请以 JSON 格式返回响应")
                    langchain_messages.insert(0, system_msg)
                
                # 使用通用对话模型
                kwargs = {}
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = self.chat_model.invoke(langchain_messages, **kwargs)
                if isinstance(response, str):
                    return response
                return response.content
                
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    logger.warning(f"智谱AI对话请求失败，正在重试({retries}/{self.max_retries}): {e}")
                    logger.warning(f"等待 {current_delay} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= self.retry_backoff  # 增加下一次重试的等待时间
                else:
                    logger.error(f"智谱AI对话请求失败，已达到最大重试次数: {e}")
                    logger.exception(e)  # 添加详细的异常堆栈
                    return None
    
    def chat_with_images(self, messages: List[Dict[str, Any]], images: List[str]) -> Optional[Any]:
        """发送带图片的对话请求
        
        Args:
            messages: 对话历史记录列表
            images: 图片文件路径列表
            
        Returns:
            智谱AI的原始响应
        """
        retries = 0
        current_delay = self.retry_delay
        
        while retries < self.max_retries:
            try:
                # 构建多模态消息
                content = []
                logger.debug(f"开始处理图片列表: {images}")
                
                # 添加图片内容
                for image_path in images:
                    if not os.path.exists(image_path):
                        logger.error(f"图片文件不存在: {image_path}")
                        continue
                        
                    try:
                        with open(image_path, "rb") as f:
                            base64_image = base64.b64encode(f.read()).decode('utf-8')
                            logger.debug(f"图片 {image_path} 已转换为base64")
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            })
                    except Exception as e:
                        logger.error(f"处理图片 {image_path} 失败: {e}")
                        continue
                
                logger.debug(f"图片内容处理完成, 共 {len(content)} 个图片")
                
                # 添加文本内容
                logger.debug("开始处理消息列表")
                for msg in messages:
                    if msg["role"] == "user":
                        if isinstance(msg["content"], str):
                            content.append({
                                "type": "text",
                                "text": msg["content"]
                            })
                            logger.debug("已添加文本消息")
                        elif isinstance(msg["content"], list):
                            content.extend(msg["content"])
                            logger.debug("已添加列表消息")
                
                if not content:
                    logger.error("没有有效的内容")
                    return None
                
                # 构建完整的消息列表
                langchain_messages = [HumanMessage(content=content)]
                logger.debug("已构建完整的消息列表")
                
                # 使用多模态模型
                logger.debug("开始调用智谱AI多模态模型")
                response = self.vision_model.invoke(langchain_messages)
                logger.debug("已收到智谱AI响应")
                return response
                
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    logger.warning(f"智谱AI图片对话请求失败，正在重试({retries}/{self.max_retries}): {e}")
                    logger.warning(f"等待 {current_delay} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= self.retry_backoff  # 增加下一次重试的等待时间
                else:
                    logger.error(f"智谱AI图片对话请求失败，已达到最大重试次数: {e}")
                    logger.exception(e)  # 添加详细的异常堆栈
                    return None
    
    def parse_response(self, response: Any) -> Optional[Union[str, Dict[str, Any]]]:
        """解析智谱AI的响应
        
        Args:
            response: 智谱AI的原始响应
            
        Returns:
            解析后的回复文本或JSON对象
        """
        try:
            if hasattr(response, "content"):
                content = response.content
                # 尝试解析JSON
                if isinstance(content, str) and content.startswith("{") and content.endswith("}"):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                        return content
                return content
            elif isinstance(response, str):
                # 尝试解析JSON字符串
                if response.startswith("{") and response.endswith("}"):
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                        return response
                return response
            return None
        except Exception as e:
            logger.error(f"解析智谱AI响应失败: {e}")
            logger.exception(e)  # 添加详细的异常堆栈
            return None
