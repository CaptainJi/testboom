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

class ZhipuAI:
    """智谱AI API封装"""
    
    def __init__(self):
        """初始化智谱AI客户端"""
        # 配置超时时间
        self.timeout_config = httpx.Timeout(
            connect=30.0,     # 连接超时增加到30秒
            read=300.0,       # 读取超时增加到5分钟
            write=60.0,       # 写入超时增加到1分钟
            pool=30.0         # 连接池超时增加到30秒
        )
        
        # 通用对话模型
        self.chat_model = ChatZhipuAI(
            api_key=settings.ai.AI_ZHIPU_API_KEY,
            model_name=settings.ai.AI_ZHIPU_MODEL_CHAT,
            temperature=0.2,
            top_p=0.2,
            streaming=False,
            timeout=self.timeout_config,
            max_retries=3,     # 添加重试次数
            request_timeout=300.0  # 总体请求超时时间
        )
        
        # 多模态模型
        self.vision_model = ChatZhipuAI(
            api_key=settings.ai.AI_ZHIPU_API_KEY,
            model_name=settings.ai.AI_ZHIPU_MODEL_VISION,
            temperature=0.2,
            top_p=0.2,
            streaming=False,
            timeout=self.timeout_config,
            max_retries=3,     # 添加重试次数
            request_timeout=300.0  # 总体请求超时时间
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
        messages: List[Dict[str, Any]], 
        response_format: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """发送对话请求"""
        try:
            langchain_messages = self._convert_messages(messages)
            
            if response_format and response_format.get("type") == "json_object":
                langchain_messages.insert(0, SystemMessage(content="请以JSON格式返回响应"))
            
            logger.info(f"发送对话请求，消息数: {len(messages)}")
            response = await self.chat_model.ainvoke(
                langchain_messages, 
                response_format=response_format if response_format else None
            )
            
            result = response.content if isinstance(response, AIMessage) else response
            if result:
                logger.debug(f"收到模型响应:\n{result}")
                return result
            else:
                logger.warning("模型未返回有效响应")
                return None
                
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
            logger.error(f"请求超时: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"对话请求失败: {str(e)}")
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
                    
                user_message = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        image_content
                    ]
                }
                
                logger.debug(f"发送图片分析请求: {path}")
                try:
                    response = await self.vision_model.ainvoke(
                        [user_message],
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
            
            if len(all_results) == 1:
                return json.dumps(all_results[0], ensure_ascii=False)
            
            logger.info("开始生成多图片分析总结")
            summary_prompt = self.prompt_template.render(
                "requirement_summary", 
                content=json.dumps(all_results, ensure_ascii=False)
            )
            
            if not summary_prompt:
                logger.warning("获取总结提示词失败，将返回原始结果")
                return json.dumps(all_results, ensure_ascii=False)
                
            logger.debug("发送总结请求")
            summary_response = await self.chat(
                [{"role": "user", "content": summary_prompt}],
                response_format={"type": "json_object"}
            )
            
            if summary_response:
                logger.info("成功生成分析总结")
                return summary_response
            else:
                logger.warning("生成总结失败，返回原始结果")
                return json.dumps(all_results, ensure_ascii=False)
                
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
            logger.error(f"请求超时: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"图片对话请求失败: {str(e)}")
            return None
