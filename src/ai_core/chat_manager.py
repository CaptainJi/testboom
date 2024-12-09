from typing import List, Dict, Optional
from .zhipu_api import ZhipuAI
from ..logger.logger import logger

class ChatManager:
    """对话管理器"""
    
    def __init__(self):
        """初始化对话管理器"""
        self.zhipu_client = ZhipuAI()
        self.history: List[Dict[str, str]] = []
        self.max_history_length = 10  # 最大历史记录长度
    
    def add_message(self, role: str, content: str):
        """添加消息到历史记录
        
        Args:
            role: 角色(user/assistant)
            content: 消息内容
        """
        self.history.append({
            "role": role,
            "content": content
        })
        
        # 如果历史记录超过最大长度,删除最早的消息
        if len(self.history) > self.max_history_length:
            self.history.pop(0)
    
    def clear_history(self):
        """清空历史记录"""
        self.history = []
    
    def chat(self, message: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """发送对话请求
        
        Args:
            message: 用户���息
            system_prompt: 系统提示语
            
        Returns:
            Optional[str]: AI回复内容
        """
        try:
            messages = []
            
            # 添加系统提示语
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 添加历史记录
            messages.extend(self.history)
            
            # 添加当前消息
            messages.append({
                "role": "user",
                "content": message
            })
            
            # 发送请求
            response = self.zhipu_client.chat(messages)
            
            # 解析响应
            reply = self.zhipu_client.parse_response(response)
            if reply:
                # 将对话记录添加到历史
                self.add_message("user", message)
                self.add_message("assistant", reply)
                return reply
            return None
            
        except Exception as e:
            logger.error(f"对话请求失败: {str(e)}")
            return None
    
    def chat_with_images(self, message: str, images: List[str], 
                        system_prompt: Optional[str] = None) -> Optional[str]:
        """发送带图片的对话请求
        
        Args:
            message: 用户消息
            images: 图片URL或Base64列表
            system_prompt: 系统提示语
            
        Returns:
            Optional[str]: AI回复内容
        """
        try:
            messages = []
            
            # 添加系统提示语
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 添加历史记录
            messages.extend(self.history)
            
            # 添加当前消息
            messages.append({
                "role": "user",
                "content": message
            })
            
            # 发送请求
            response = self.zhipu_client.chat_with_images(messages, images)
            
            # 解析响应
            reply = self.zhipu_client.parse_response(response)
            if reply:
                # 将对话记录添加到历史
                self.add_message("user", message)
                self.add_message("assistant", reply)
                return reply
            return None
            
        except Exception as e:
            logger.error(f"带��片的对话请求失败: {str(e)}")
            return None
