import base64
import os
import json
import time
from typing import List, Dict, Any, Optional, Union
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from src.config.settings import settings
from src.logger.logger import logger
import zhipuai
import aiohttp
import asyncio

class ZhipuAI:
    """智谱AI API封装(基于LangChain)"""
    
    # 智谱AI的token限制
    MAX_TOKENS = 6000  # GLM-4的最大token数
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        """初始化智谱AI客户端"""
        logger.info("初始化智谱AI客户端")
        
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
        
        # 根据模型设置token限制
        if settings.ZHIPU_MODEL_CHAT == "glm-4-flash":
            self.MAX_TOKENS = 128000  # glm-4-flash的最大token数
        else:
            self.MAX_TOKENS = 6000  # glm-4的最大token数
            
        self.MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 5  # 增加重试间隔到5秒
        self.retry_backoff = 2  # 重试间隔倍数
    
    def _truncate_text(self, text: str, max_length: int = 4000) -> str:
        """截断文本到指定长度
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            str: 截断后的文本
        """
        if len(text) <= max_length:
            return text
        
        # 按句子截断
        sentences = text.split('。')
        result = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) + 1 <= max_length - 10:  # 预留10个字符给省略号
                result.append(sentence)
                current_length += len(sentence) + 1  # +1 是句号
            else:
                break
        
        return '。'.join(result) + '。...(已截断)'
    
    def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理消息，确保不超出限制
        
        Args:
            message: 原始消息
            
        Returns:
            Dict[str, Any]: 处理后的消息
        """
        try:
            logger.debug(f"开始处理消息: role={message.get('role')}")
            
            # 处理系统消息
            if message.get("role") == "system":
                if isinstance(message.get("content"), str):
                    original_content = message["content"]
                    message["content"] = message["content"][:200]
                    logger.debug(f"系统消息已截断: {len(original_content)} -> {len(message['content'])} 字符")
                return message
            
            # 处理文本内容
            if isinstance(message.get("content"), str):
                text = message["content"]
                text_bytes = text.encode('utf-8')
                estimated_tokens = len(text_bytes) / 3
                logger.debug(f"文本消息统计: {len(text)} 字符, {len(text_bytes)} 字节, 估算 {estimated_tokens:.0f} tokens")
                
                if estimated_tokens > self.MAX_TOKENS * 0.8:
                    logger.debug(f"文本超出限制 ({estimated_tokens:.0f} > {self.MAX_TOKENS * 0.8:.0f}), 开始截断")
                    sentences = text.split('。')
                    result = []
                    current_tokens = 0
                    target_tokens = self.MAX_TOKENS * 0.8
                    
                    for i, sentence in enumerate(sentences):
                        sentence_bytes = sentence.encode('utf-8')
                        sentence_tokens = len(sentence_bytes) / 3
                        if current_tokens + sentence_tokens <= target_tokens:
                            result.append(sentence)
                            current_tokens += sentence_tokens
                            logger.debug(f"添加第 {i+1}/{len(sentences)} 个句子: +{sentence_tokens:.0f} tokens, 当前总计 {current_tokens:.0f} tokens")
                        else:
                            logger.debug(f"截断于第 {i+1}/{len(sentences)} 个句子")
                            break
                    
                    original_tokens = estimated_tokens
                    message["content"] = '。'.join(result) + '。...(已截断)'
                    final_tokens = len(message["content"].encode('utf-8')) / 3
                    logger.debug(f"文本截断完成: {original_tokens:.0f} -> {final_tokens:.0f} tokens")
                    
            # 处理多模态内容
            elif isinstance(message.get("content"), list):
                logger.debug("开始处理多模态内容")
                processed_content = []
                total_tokens = 0
                target_tokens = self.MAX_TOKENS * 0.8
                
                for i, item in enumerate(message["content"]):
                    logger.debug(f"处理第 {i+1}/{len(message['content'])} 个内容项: type={item.get('type')}")
                    
                    if item["type"] == "text":
                        text = item["text"]
                        text_bytes = text.encode('utf-8')
                        text_tokens = len(text_bytes) / 3
                        logger.debug(f"文本项统计: {len(text)} 字符, {len(text_bytes)} 字节, 估算 {text_tokens:.0f} tokens")
                        
                        if total_tokens + text_tokens > target_tokens:
                            remaining_tokens = target_tokens - total_tokens
                            logger.debug(f"文本项超出限制, 剩余配额: {remaining_tokens:.0f} tokens")
                            
                            if remaining_tokens > 100:
                                sentences = text.split('。')
                                result = []
                                current_tokens = 0
                                
                                for j, sentence in enumerate(sentences):
                                    sentence_bytes = sentence.encode('utf-8')
                                    sentence_tokens = len(sentence_bytes) / 3
                                    if current_tokens + sentence_tokens <= remaining_tokens:
                                        result.append(sentence)
                                        current_tokens += sentence_tokens
                                        logger.debug(f"添加第 {j+1}/{len(sentences)} 个句子: +{sentence_tokens:.0f} tokens, 当前总计 {current_tokens:.0f} tokens")
                                    else:
                                        logger.debug(f"截断于第 {j+1}/{len(sentences)} 个句子")
                                        break
                                
                                item["text"] = '。'.join(result) + '。...(已截断)'
                                total_tokens += current_tokens
                                logger.debug(f"文本项处理完成, 当前总计 {total_tokens:.0f} tokens")
                            else:
                                logger.debug(f"剩余配额不足 100 tokens, 跳过此文本项")
                                continue
                        else:
                            total_tokens += text_tokens
                            logger.debug(f"文本项未超出限制, 当前总计 {total_tokens:.0f} tokens")
                            
                    processed_content.append(item)
                
                message["content"] = processed_content
                logger.debug(f"多模态内容处理完成, 共处理 {len(processed_content)} 个内容项")
            
            return message
            
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            return message
    
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
                # 换消息格式
                langchain_messages = self._convert_messages(messages)
                
                # 如果需要 JSON 响应，添加 system 息
                if response_format and response_format.get("type") == "json_object":
                    system_msg = SystemMessage(content="请以 JSON 格式返回响应")
                    langchain_messages.insert(0, system_msg)
                
                # 使用通用对话模型
                kwargs = {}
                if response_format:
                    kwargs["response_format"] = response_format
                
                logger.info(f"正在使用模型: {self.chat_model.model_name}")
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
                    current_delay *= self.retry_backoff
                else:
                    logger.error(f"智谱AI对话请求失败，已达到最大重试次数: {e}")
                    logger.exception(e)
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
                    logger.error("没有有内容")
                    return None
                
                # 构建完整的消���列表
                langchain_messages = [HumanMessage(content=content)]
                logger.debug("已构建完整的消息列表")
                
                # 使用多模态模型
                logger.info(f"正在使用模型: {self.vision_model.model_name}")
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
                    current_delay *= self.retry_backoff
                else:
                    logger.error(f"智谱AI图片对话请求失败，已达到最大重试次数: {e}")
                    logger.exception(e)
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
    
    async def achat(self, messages: List[Dict[str, Any]], **kwargs) -> Optional[str]:
        """异��调用智谱AI对话接口
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            Optional[str]: 对话响应，如果出错则返回None
        """
        retries = 0
        current_delay = self.retry_delay
        
        logger.debug(f"开始处理 {len(messages)} 条消息")
        # 处理消息，确保不超出限制
        processed_messages = []
        total_tokens = 0
        
        for i, msg in enumerate(messages):
            processed_msg = self._process_message(msg)
            if isinstance(processed_msg.get("content"), str):
                msg_tokens = len(processed_msg["content"].encode('utf-8')) / 3
                total_tokens += msg_tokens
                logger.debug(f"消息 {i+1}: {msg_tokens:.0f} tokens, 累计 {total_tokens:.0f} tokens")
            elif isinstance(processed_msg.get("content"), list):
                for item in processed_msg["content"]:
                    if item.get("type") == "text":
                        text_tokens = len(item["text"].encode('utf-8')) / 3
                        total_tokens += text_tokens
                        logger.debug(f"消息 {i+1} 文本项: {text_tokens:.0f} tokens, 累计 {total_tokens:.0f} tokens")
            processed_messages.append(processed_msg)
        
        logger.debug(f"消息处理完成, 总计约 {total_tokens:.0f} tokens")
        
        # 获取实际使用的模型名称
        model_name = data.get("model", "unknown")
        logger.info(f"正在使用模型: {model_name}")
        
        while retries < self.max_retries:
            try:
                # 构建请求数据
                data = {
                    "model": settings.ZHIPU_MODEL_CHAT,  # 使用环境变量中配置的模型
                    "messages": processed_messages,
                    **kwargs
                }
                
                # 准备请求头
                headers = {
                    "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # 异步发送请求
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        result = await response.json()
                        logger.debug(f"收到API响应: {result}")
                        
                        if result.get('code') == 200:
                            return result['data']['choices'][0]['message']['content']
                        else:
                            error = result.get('error', {})
                            error_code = error.get('code', '')
                            error_message = error.get('message', '')
                            logger.error(f"异步调用智谱AI失败: {error_code} - {error_message}")
                            
                            if error_code == '1261' and retries < self.max_retries - 1:
                                retries += 1
                                logger.warning(f"Prompt超长，正在进行第 {retries} 次重试...")
                                # 进一步截断内容
                                for msg in processed_messages:
                                    if isinstance(msg.get("content"), str):
                                        msg["content"] = msg["content"][:int(len(msg["content"]) * 0.8)]
                                    elif isinstance(msg.get("content"), list):
                                        for item in msg["content"]:
                                            if item.get("type") == "text":
                                                item["text"] = item["text"][:int(len(item["text"]) * 0.8)]
                                await asyncio.sleep(current_delay)
                                current_delay *= self.retry_backoff
                                continue
                            return None
                            
            except Exception as e:
                logger.error(f"异步调用智谱AI异常: {str(e)}")
                logger.exception(e)
                if retries < self.max_retries - 1:
                    retries += 1
                    logger.warning(f"正在进行第 {retries} 次重试...")
                    await asyncio.sleep(current_delay)
                    current_delay *= self.retry_backoff
                    continue
                return None
        
        return None
