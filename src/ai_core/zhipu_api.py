from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions, log_function_call, retry
from src.utils.common import truncate_text, process_multimodal_content, safe_json_loads
from src.storage.storage import get_storage_service
from .prompt_template import PromptTemplate
import base64
import json
import requests
from urllib.parse import urlparse

class ZhipuAI:
    """智谱AI API封装(基于LangChain)"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
        logger.info("初始化智谱AI客户端")
        logger.info(f"配置的对话模型: {settings.ai.AI_ZHIPU_MODEL_CHAT}")
        logger.info(f"配置的视觉模型: {settings.ai.AI_ZHIPU_MODEL_VISION}")
        
        # 通用对话模型
        self.chat_model = ChatZhipuAI(
            api_key=settings.ai.AI_ZHIPU_API_KEY,
            model_name=settings.ai.AI_ZHIPU_MODEL_CHAT,
            temperature=0.2,
            top_p=0.2,
            streaming=False
        )
        
        # 多模态模型
        self.vision_model = ChatZhipuAI(
            api_key=settings.ai.AI_ZHIPU_API_KEY,
            model_name=settings.ai.AI_ZHIPU_MODEL_VISION,
            temperature=0.2,
            top_p=0.2,
            streaming=False
        )
        
        # 初始化提示词模板管理器
        self.prompt_template = PromptTemplate()
        
        # 验证模型名称
        if self.chat_model.model_name != settings.ai.AI_ZHIPU_MODEL_CHAT:
            logger.warning(f"对话模型名称不匹配: 期望 {settings.ai.AI_ZHIPU_MODEL_CHAT}, 实际 {self.chat_model.model_name}")
            self.chat_model.model_name = settings.ai.AI_ZHIPU_MODEL_CHAT
            
        if self.vision_model.model_name != settings.ai.AI_ZHIPU_MODEL_VISION:
            logger.warning(f"视觉模型名称不匹配: 期望 {settings.ai.AI_ZHIPU_MODEL_VISION}, 实际 {self.vision_model.model_name}")
            self.vision_model.model_name = settings.ai.AI_ZHIPU_MODEL_VISION
    
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
        max_retries=settings.ai.AI_RETRY_COUNT,
        delay=settings.ai.AI_RETRY_DELAY,
        backoff=settings.ai.AI_RETRY_BACKOFF
    )
    @handle_exceptions(default_return=None)
    @log_function_call()
    async def chat(
        self, 
        messages: List[Dict[str, Any]], 
        response_format: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """发送对话请求
        
        Args:
            messages: 对话历史记录列表
            response_format: 响应格式,如 {"type": "json_object"}
            
        Returns:
            Optional[str]: AI的响应，如果出错则返回None
        """
        # 转换消息格式
        langchain_messages = self._convert_messages(messages)
        
        # 如果需JSON响应，添加system消息
        if response_format and response_format.get("type") == "json_object":
            system_msg = SystemMessage(content="请以JSON格式返回响应")
            langchain_messages.insert(0, system_msg)
        
        # 调用模型
        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format
        
        logger.info(f"正在使用的大模型: {self.chat_model.model_name}")
        response = await self.chat_model.ainvoke(langchain_messages, **kwargs)
        
        result = response.content if isinstance(response, AIMessage) else response
        if result:
            logger.debug(f"大模型回复内容:\n{result}")
        else:
            logger.warning("大模型未返回有效内容")
            
        return result
    
    @retry(
        max_retries=settings.ai.AI_RETRY_COUNT,
        delay=settings.ai.AI_RETRY_DELAY,
        backoff=settings.ai.AI_RETRY_BACKOFF
    )
    @handle_exceptions(default_return=None)
    @log_function_call()
    async def chat_with_images(
        self, 
        messages: List[Dict[str, Any]], 
        image_paths: List[str]
    ) -> Optional[str]:
        """发送带图片的对话请求
        
        Args:
            messages: 对话历史记录列表
            image_paths: 图片路径列表（本地路径或URL）
            
        Returns:
            Optional[str]: AI的响应，如果出错则返回None
        """
        logger.info(f"正在使用的视觉模型: {self.vision_model.model_name}")
        try:
            storage_service = get_storage_service()
            all_results = []
            total_images = len(image_paths)
            
            # 获取图片分析提示词
            prompt = self.prompt_template.render("image_analysis")
            if not prompt:
                logger.error("获取图片分析提示词失败")
                return None
            
            # 逐个处理每张图片
            for index, path in enumerate(image_paths, 1):
                logger.info(f"{self.vision_model.model_name}正在处理第 {index}/{total_images} 张图片...")
                
                # 更新任务进度
                from src.api.services.task import TaskManager
                for task_id, task in TaskManager._tasks.items():
                    if task['type'] == 'generate_cases' and task['status'] == 'running':
                        TaskManager.update_task(
                            task_id,
                            result={
                                'progress': f"{self.vision_model.model_name}正在处理第 {index}/{total_images} 张图片",
                                'current': index,
                                'total': total_images
                            }
                        )
                        break
                
                # 构建图片内容
                image_content = None
                if storage_service and storage_service.enabled:
                    image_content = {
                        "type": "image_url",
                        "image_url": {"url": path}
                    }
                else:
                    try:
                        with open(path, 'rb') as f:
                            image_data = f.read()
                            if len(image_data) > settings.ai.AI_MAX_IMAGE_SIZE:
                                logger.warning(f"图片过大: {path}")
                                continue
                            
                            base64_image = base64.b64encode(image_data).decode()
                            image_content = {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                    except Exception as e:
                        logger.error(f"处理图片失败: {path}, 错误: {str(e)}")
                        continue
                
                if not image_content:
                    continue
                
                # 构建消息
                user_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        image_content
                    ]
                }
                
                # 发送请求
                response = await self.vision_model.ainvoke(
                    [user_message],
                    response_format={"type": "json_object"}
                )
                
                result = response.content if isinstance(response, AIMessage) else response
                if result:
                    # 记录大模型的原始回复
                    logger.debug(f"大模型回复内容:\n{result}")
                    
                    parsed_result = self.parse_response(result)
                    if parsed_result:
                        all_results.append(parsed_result)
                        logger.debug(f"解析后的结果:\n{json.dumps(parsed_result, ensure_ascii=False, indent=2)}")
                    else:
                        logger.warning("解析结��失败")
                else:
                    logger.warning("大模型未返回有效内容")
                
            # 如果没有有效结果，返回None
            if not all_results:
                return None
                
            # 如果只有一张图片，直接返回结果
            if len(all_results) == 1:
                return json.dumps(all_results[0], ensure_ascii=False)
            
            # 获取结果汇总提示词
            summary_prompt = self.prompt_template.render(
                "requirement_summary", 
                content=json.dumps(all_results, ensure_ascii=False)
            )
            if not summary_prompt:
                logger.error("获取结果汇总提示词失败")
                return json.dumps(all_results[0], ensure_ascii=False)
            
            # 发送汇总请求
            summary_message = {
                "role": "user",
                "content": summary_prompt
            }
            
            summary_response = await self.chat_model.ainvoke(
                [summary_message],
                response_format={"type": "json_object"}
            )
            
            return summary_response.content if isinstance(summary_response, AIMessage) else summary_response
            
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
