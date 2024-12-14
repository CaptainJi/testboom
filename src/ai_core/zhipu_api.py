from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions, log_function_call, retry
from src.utils.common import truncate_text, process_multimodal_content, safe_json_loads
import base64
import json

class ZhipuAI:
    """智谱AI API封装(基于LangChain)"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
        logger.info("初始化智谱AI客户端")
        
        # 通用对话模型
        self.chat_model = ChatZhipuAI(
            api_key=settings.ai.ZHIPU_API_KEY,
            model_name=settings.ai.ZHIPU_MODEL_CHAT,
            temperature=0.2,
            top_p=0.2,
            streaming=False
        )
        
        # 多模态模型
        self.vision_model = ChatZhipuAI(
            api_key=settings.ai.ZHIPU_API_KEY,
            model_name=settings.ai.ZHIPU_MODEL_VISION,
            temperature=0.2,
            top_p=0.2,
            streaming=False
        )
    
    @log_function_call(level="DEBUG")
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Any]:
        """转换消息格式为LangChain格式
        
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
    
    @retry(
        max_retries=settings.ai.RETRY_COUNT,
        delay=settings.ai.RETRY_DELAY,
        backoff=settings.ai.RETRY_BACKOFF
    )
    @handle_exceptions(default_return=None)
    @log_function_call()
    def chat(
        self, 
        messages: List[Dict[str, Any]], 
        response_format: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """发送对话请求
        
        Args:
            messages: 对话历史��录列表
            response_format: 响应格式,如 {"type": "json_object"}
            
        Returns:
            Optional[str]: AI的响应，如果出错则返回None
        """
        # 转换消息格式
        langchain_messages = self._convert_messages(messages)
        
        # 如果需要JSON响应，添加system消息
        if response_format and response_format.get("type") == "json_object":
            system_msg = SystemMessage(content="请以JSON格式返回响应")
            langchain_messages.insert(0, system_msg)
        
        # 调用模型
        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format
        
        logger.info(f"正在使用模型: {self.chat_model.model_name}")
        response = self.chat_model.invoke(langchain_messages, **kwargs)
        
        return response.content if isinstance(response, AIMessage) else response
    
    @retry(
        max_retries=settings.ai.RETRY_COUNT,
        delay=settings.ai.RETRY_DELAY,
        backoff=settings.ai.RETRY_BACKOFF
    )
    @handle_exceptions(default_return=None)
    @log_function_call()
    def chat_with_images(
        self, 
        messages: List[Dict[str, Any]], 
        image_paths: List[str]
    ) -> Optional[str]:
        """发送带图片的对��请求"""
        try:
            # 处理图片
            content = []
            for path in image_paths:
                try:
                    with open(path, 'rb') as f:
                        image_data = f.read()
                        if len(image_data) > settings.ai.MAX_IMAGE_SIZE:
                            logger.warning(f"图片过大: {path}")
                            continue
                        
                        base64_image = base64.b64encode(image_data).decode()
                        content.append({
                            "type": "image",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        })
                except Exception as e:
                    logger.error(f"处理图片失败: {path}, 错误: {str(e)}")
                    continue
                    
            # 添加文本内容
            if messages:
                last_message = messages[-1]
                if isinstance(last_message.get("content"), str):
                    content.append({
                        "type": "text",
                        "text": last_message["content"]
                    })
            
            # 处理多模态内容
            processed_content = process_multimodal_content(
                content, 
                settings.ai.MAX_TOKENS
            )
            
            # 构建系统消息
            system_message = SystemMessage(content="""你是一个专业的需求分析专家。请仔细分析图片中的需求，提取关键信息并生成结构化的分析结果。
请以JSON格式返回分析结果，格式如下：
{
    "title": "需求标题",
    "description": "需求描述",
    "modules": [
        {
            "name": "模块名称",
            "features": [
                {
                    "name": "功能名称",
                    "description": "功能描述",
                    "key_points": ["关键点1", "关键点2"]
                }
            ]
        }
    ],
    "test_focus": ["测试重点1", "测试重点2"],
    "notes": ["注意事项1", "注意事项2"]
}""")
            
            # 构建用户消息
            user_message = HumanMessage(content=processed_content)
            
            # 发送请求
            logger.info(f"正在使用模型: {self.vision_model.model_name}")
            response = self.vision_model.invoke(
                [system_message, user_message],
                response_format={"type": "json_object"}
            )
            
            return response.content if isinstance(response, AIMessage) else response
            
        except Exception as e:
            logger.error(f"图片对话请求失败: {str(e)}")
            raise
    
    @handle_exceptions(default_return=None)
    def parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析AI响应
        
        Args:
            response: AI的响应文本
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的响应，如果解析失败则返回None
        """
        return safe_json_loads(response)
