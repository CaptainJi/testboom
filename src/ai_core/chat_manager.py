from typing import List, Dict, Optional, Any, Union
from .zhipu_api import ZhipuAI
from .prompt_template import PromptTemplate
from src.logger.logger import logger
import json

class ChatManager:
    """对话管理器"""
    
    def __init__(self):
        """初始化对话管理器"""
        self.client = ZhipuAI()
        self.history: List[Dict[str, Union[str, List[Dict[str, Any]]]]] = []
        self.prompt_manager = PromptTemplate()
    
    def add_message(self, role: str, content: Union[str, List[Dict[str, Any]]]):
        """添加消息到历史记录
        
        Args:
            role: 角色(user/assistant/system)
            content: 消息内容,可以是字符串或多模态内容列表
        """
        # 如果content是字符串,转换为标准格式
        if isinstance(content, str):
            if role == "user":
                content = [{
                    "type": "text",
                    "text": content
                }]
        
        self.history.append({
            "role": role,
            "content": content
        })
    
    def clear_history(self):
        """清空历史记录"""
        self.history = []
    
    def chat(self, message: str) -> Optional[str]:
        """发送对话请求
        
        Args:
            message: 用户消息
            
        Returns:
            Optional[str]: 助手回复
        """
        try:
            # 添加用户消息
            self.add_message("user", message)
            
            # 发送请求
            response = self.client.chat(self.history)
            if response is None:
                return None
            
            # 解析响应
            reply = self.client.parse_response(response)
            if reply:
                self.add_message("assistant", reply)
            return reply
            
        except Exception as e:
            logger.error(f"对话请求失败: {e}")
            return None
    
    def chat_with_images(self, message: str, images: List[str]) -> Optional[str]:
        """发送带图片的对话请求
        
        Args:
            message: 用户消息
            images: 图片文件路径列表
            
        Returns:
            Optional[str]: 助手回复
        """
        try:
            logger.debug(f"开始处理图片对话请求, 消息: {message}, 图片: {images}")
            
            # 多模态消息
            content = [{
                "type": "text",
                "text": message
            }]
            logger.debug(f"构建的多模态消息: {content}")
            
            # 添加用户消息
            self.add_message("user", content)
            logger.debug(f"当前历史记录: {self.history}")
            
            # 发送请求
            response = self.client.chat_with_images(self.history, images)
            logger.debug(f"收到响应: {response}")
            if response is None:
                return None
            
            # 解析响应
            reply = self.client.parse_response(response)
            logger.debug(f"解析后的回复: {reply}")
            if reply:
                self.add_message("assistant", reply)
            return reply
            
        except Exception as e:
            logger.error(f"带图片的对话请求失败: {e}")
            logger.exception(e)  # 添加详细的异常堆栈
            return None
            
    def analyze_requirement(self, message: str, images: Optional[List[str]] = None, template_name: Optional[str] = None) -> Optional[str]:
        """分析需求
        
        Args:
            message: 需求文本
            images: 可选的图片路径列表
            template_name: 可选的模板名称
            
        Returns:
            Optional[str]: 分析结果
        """
        try:
            if template_name:
                # 使用指定模板
                prompt = self.prompt_manager.render(
                    template_name=template_name,
                    content=message
                )
                if not prompt:
                    logger.error("渲染模板失败")
                    return None
                message = prompt
            
            if images:
                # 处理图片
                logger.info(f"开始分析需求: {message}")
                logger.info(f"图片: {images}")
                return self.chat_with_images(message, images)
            else:
                # 处理文本
                logger.info(f"开始分析需求: {message}")
                logger.info("图片: None")
                return self.chat(message)
            
        except Exception as e:
            logger.error(f"分析需求失败: {e}")
            return None
            
    def generate_testcases(self, summary: str, details: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """生成测试用例
        
        Args:
            summary: 需求汇总结果
            details: 可选的详细分析结果
            
        Returns:
            Optional[List[Dict[str, Any]]]: 生成的测试用例列表
        """
        try:
            # 构建完整的输入内容
            content = {
                'summary': summary,
                'details': details or {}
            }
            
            # 渲染测试用例生成模板
            prompt = self.prompt_manager.render(
                template_name="testcase_generation",
                content=json.dumps(content, ensure_ascii=False, indent=2)
            )
            if not prompt:
                logger.error("渲染测试用例生成模板失败")
                return None
                
            # 添加用户消息
            self.add_message("user", prompt)
                
            # 指定JSON输出格式
            response = self.client.chat(self.history, response_format={"type": "json_object"})
            if not response:
                logger.error("生成测试用例失败")
                return None
                
            # 打印原始响应
            logger.info(f"\n大模型返回的原始响应:\n{response}")
            
            # 解析响应
            result = self.client.parse_response(response)
            logger.info(f"\n解析后的响应内容:\n{result}")
            
            if not result or not isinstance(result, dict):
                logger.error("解析测试用例失败")
                return None
                
            # 提取测试用例列表
            testcases = result.get('testcases', [])
            if not testcases:
                logger.warning("未生成任何测试用例")
                return []
                
            logger.info(f"成功生成 {len(testcases)} 个测试用例")
            return testcases
            
        except Exception as e:
            logger.error(f"测试用例生成失败: {e}")
            return None
            
    def analyze_testcases(self, testcases: str) -> Optional[str]:
        """分析测试用例
        
        Args:
            testcases: 测试用例内容
            
        Returns:
            Optional[str]: 分析结果
        """
        try:
            # 渲染测试用例理解模板
            prompt = self.prompt_manager.render(
                template_name="testcase_understanding",
                content=testcases
            )
            if not prompt:
                logger.error("渲染测试用例理解模板失败")
                return None
                
            return self.chat(prompt)
            
        except Exception as e:
            logger.error(f"测试用例分析失败: {e}")
            return None
