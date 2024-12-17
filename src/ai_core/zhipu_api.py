from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions, retry
from src.utils.common import process_multimodal_content, safe_json_loads
from src.storage.storage import get_storage_service
from .prompt_template import PromptTemplate
import base64
import json
import httpx
from src.api.services.task import TaskManager
import aiohttp
import asyncio
import uuid

class ZhipuAI:
    """智谱AI API封装"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
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
        
        self.prompt_template = PromptTemplate()
        logger.info(f"初始化AI客户端完成，对话模型: {settings.ai.AI_ZHIPU_MODEL_CHAT}, 视觉模型: {settings.ai.AI_ZHIPU_MODEL_VISION}")
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Any]:
        """转换消息格式为LangChain格式"""
        message_map = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage
        }
        return [message_map[msg["role"]](content=msg["content"]) 
                for msg in messages if msg["role"] in message_map]
    
    def _process_image(self, path: str) -> Optional[Dict[str, Any]]:
        """处理图片内容"""
        storage_service = get_storage_service()
        if storage_service and storage_service.enabled:
            return {
                "type": "image_url",
                "image_url": {"url": path}
            }
        
        try:
            with open(path, 'rb') as f:
                image_data = f.read()
                if len(image_data) > settings.ai.AI_MAX_IMAGE_SIZE:
                    logger.warning(f"图片过大: {path}")
                    return None
                    
                base64_image = base64.b64encode(image_data).decode()
                return {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
        except Exception as e:
            logger.error(f"处理图片失败: {path}, 错误: {str(e)}")
            return None
    
    @retry(
        max_retries=5,
        delay=10,
        backoff=2,
        exceptions=(httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException)
    )
    @handle_exceptions(default_return=None)
    async def chat(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """发送聊天请求
        
        Args:
            messages: 消息列表
            response_format: 响应格式
            timeout: 超时时间（秒）
            
        Returns:
            Optional[str]: 响应内容
        """
        try:
            logger.info("发送聊天请求 (尝试 1/3)")
            
            # 转换消息格式
            langchain_messages = self._convert_messages(messages)
            
            # 添加JSON格式要求
            if response_format and response_format.get("type") == "json_object":
                langchain_messages.insert(0, SystemMessage(content="请以JSON格式返回响应"))
            
            # 设置超时时间
            if timeout:
                # 创建新的超时配置
                timeout_config = httpx.Timeout(
                    connect=30.0,
                    read=float(timeout),
                    write=60.0,
                    pool=30.0
                )
                # 创建新的模型实例
                chat_model = ChatZhipuAI(
                    api_key=settings.ai.AI_ZHIPU_API_KEY,
                    model_name=settings.ai.AI_ZHIPU_MODEL_CHAT,
                    temperature=0.2,
                    top_p=0.2,
                    streaming=False,
                    timeout=timeout_config,
                    max_retries=3
                )
            else:
                chat_model = self.chat_model
            
            # 使用chat_model发送请求
            try:
                response = await chat_model.ainvoke(
                    langchain_messages,
                    response_format=response_format if response_format else None
                )
                
                # 提取响应内容
                result = response.content if isinstance(response, AIMessage) else response
                if not result:
                    logger.error("响应内容为空")
                    return None
                
                return result
                
            except asyncio.TimeoutError as e:
                logger.error(f"请求超时: {str(e)}", exc_info=True)
                return None
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP请求错误: {str(e)}")
                logger.error(f"状态码: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
                logger.error(f"响应内容: {e.response.text if hasattr(e, 'response') else 'unknown'}")
                return None
                
            except Exception as e:
                logger.error(f"请求失败: {str(e)}", exc_info=True)
                # 尝试提取更多错误信息
                error_info = {}
                for attr in ['response', 'message', 'args', 'code', 'reason']:
                    if hasattr(e, attr):
                        error_info[attr] = getattr(e, attr)
                if error_info:
                    logger.error(f"错误详情: {json.dumps(error_info, ensure_ascii=False)}")
                return None
                
        except Exception as e:
            logger.error(f"外部错误: {str(e)}", exc_info=True)
            return None
    
    @retry(
        max_retries=5,  # 增加重试次数
        delay=10,       # 增加延迟时间
        backoff=2,      # 保持指数退避
        exceptions=(httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException)
    )
    @handle_exceptions(default_return=None)
    async def chat_with_images(
        self, 
        messages: List[Dict[str, Any]], 
        image_paths: List[str]
    ) -> Optional[str]:
        """发送带图片的对话请求"""
        try:
            logger.info(f"开始处理图片对话请求，使用模型: {self.vision_model.model_name}")
            
            prompt = self.prompt_template.render("image_analysis")
            if not prompt:
                logger.error("获取图片分析提示词失败")
                return None
                
            all_results = []
            total_images = len(image_paths)
            logger.info(f"共需处理 {total_images} 张图片")
            
            for index, path in enumerate(image_paths, 1):
                logger.info(f"正在处理第 {index}/{total_images} 张图片: {path}")
                
                # 更新任务进度
                for task_id, task in TaskManager._tasks.items():
                    if task['type'] == 'generate_cases' and task['status'] == 'running':
                        progress_msg = f"{self.vision_model.model_name}正在处理第 {index}/{total_images} 张图片"
                        logger.debug(f"更新任务进度 - TaskID: {task_id}, Progress: {progress_msg}")
                        TaskManager.update_task(
                            task_id,
                            result={
                                'progress': progress_msg,
                                'current': index,
                                'total': total_images
                            }
                        )
                        break
                
                image_content = self._process_image(path)
                if not image_content:
                    logger.warning(f"跳过处理失败的图片: {path}")
                    continue
                    
                # 构建多模态消息内容
                multimodal_content = [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    image_content
                ]
                
                logger.debug(f"发送图片分析请求: {path}")
                try:
                    # 使用vision_model处理请求
                    response = await self.vision_model.ainvoke(
                        [HumanMessage(content=multimodal_content)],
                        response_format={"type": "json_object"}
                    )
                    
                    result = response.content if isinstance(response, AIMessage) else response
                    if result:
                        logger.debug(f"收到模型响应:\n{result}")
                        parsed_result = safe_json_loads(result)
                        if parsed_result:
                            logger.debug(f"解析结果成功:\n{json.dumps(parsed_result, ensure_ascii=False, indent=2)}")
                            all_results.append(parsed_result)
                        else:
                            logger.warning(f"解析响应失败: {result}")
                    else:
                        logger.warning("模型未返回有效响应")
                        
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
                    logger.error(f"处理图片 {path} 超时: {str(e)}")
                    raise
                except Exception as e:
                    logger.error(f"处理图片 {path} 失败: {str(e)}")
                    continue
            
            if not all_results:
                logger.error("没有成功处理任何图片")
                return None
                
            logger.info(f"成功处理 {len(all_results)}/{total_images} 张图片")
            
            # 直接返回第一个结果
            return json.dumps(all_results[0], ensure_ascii=False)
                
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
            logger.error(f"请求超时: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"图片对话请求失败: {str(e)}")
            return None
