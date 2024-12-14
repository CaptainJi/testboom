from typing import List, Dict, Optional, Any
from .zhipu_api import ZhipuAI
from .prompt_template import PromptTemplate
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions, log_function_call
from src.utils.common import safe_json_loads
import json

class ChatManager:
    """AI对话管理器
    
    负责管理与AI模型的对话交互，包括：
    1. 基础对话功能
    2. 图片理解功能
    3. 需求分析功能
    4. 测试用例生成和分析功能
    
    主要职责：
    - 维护对话上下文
    - 处理多轮对话
    - 管理对话历史
    - 处理多模态输入
    - 解析AI响应
    """
    
    def __init__(self):
        """初始化对话管理器"""
        self.ai = ZhipuAI()
        self.history = []
        self.template = PromptTemplate()
    
    @handle_exceptions(default_return=None)
    @log_function_call()
    def chat(self, message: str) -> Optional[str]:
        """执行基础对话
        
        Args:
            message: 用户消息
            
        Returns:
            Optional[str]: AI的回复，如果���错则返回None
        """
        # 记录用户消息
        self.history.append({
            "role": "user",
            "content": message
        })
        
        # 调用AI接口
        response = self.ai.chat(self.history)
        if not response:
            return None
            
        # 记录AI回复
        self.history.append({
            "role": "assistant", 
            "content": response
        })
        
        return response
    
    @handle_exceptions(default_return=None)
    @log_function_call()
    def chat_with_images(self, message: str, image_paths: List[str]) -> Optional[str]:
        """执行带图片的对话
        
        Args:
            message: 用户消息
            image_paths: 图片路径列表
            
        Returns:
            Optional[str]: AI的回复，如果出错则返回None
        """
        # 记录用户消息
        self.history.append({
            "role": "user",
            "content": message,
            "images": image_paths
        })
        
        # 调用AI接口
        response = self.ai.chat_with_images(self.history, image_paths)
        if not response:
            return None
            
        # 记录AI回复    
        self.history.append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    @handle_exceptions(default_return=None)
    @log_function_call()
    def analyze_requirement(
        self, 
        content: str, 
        image_paths: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """分析需求文档"""
        # 清除历史对话记录
        self.history = []
        
        # 渲染分析模板
        prompt = self.template.render(
            template_name="requirement_analysis",
            content=content
        )
        if not prompt:
            return None
        
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的需求分析专家。请仔细分析需求文档，提取关键信息并生成结构化的分析结果。分析要点包括：功能需求、非功能需求、业务规则、用户界面等。请确保返回的是格式正确的JSON对象。"
            }
        ]
        
        # 添加用户消息
        if image_paths:
            messages.append({
                "role": "user",
                "content": prompt,
                "images": image_paths
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        # 根据是否有图片选择对话方式
        if image_paths:
            response = self.ai.chat_with_images(messages, image_paths)
        else:
            response = self.ai.chat(messages, response_format={"type": "json_object"})
            
        if not response:
            return None
            
        # 解析响应
        return safe_json_loads(response)
    
    @handle_exceptions(default_return=None)
    @log_function_call()
    def generate_testcases(
        self, 
        summary: Dict[str, Any], 
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """生成测试用例"""
        # 构建完整的上下文内容
        context = json.dumps(summary, ensure_ascii=False, indent=2)
        
        if details:
            # 添加图片分析结果
            if "images" in details:
                context += "\n\n图片分析结果:\n"
                for img_result in details["images"]:
                    if isinstance(img_result.get('content'), dict):
                        content = json.dumps(img_result['content'], ensure_ascii=False, indent=2)
                    else:
                        content = str(img_result.get('content', ''))
                    context += f"\n{content}\n"
                    
                    features = img_result.get('features', {})
                    for key, value in features.items():
                        context += f"{key}: {value}\n"
        
        # 渲染测试用例生成模板
        prompt = self.template.render(
            template_name="testcase_generation",
            content=context
        )
        if not prompt:
            logger.error("渲染测试用例生成模板失败")
            return None
        
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的测试用例设计专家。请仔细分析需求，生成全面的测试用例。测试用例必须包含正向流程、异常场景、边界条件等。每个功能点至少生成3-5个测试用例。请确保返回的是格式正确的JSON对象。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 调用AI生成测试用例
        response = self.ai.chat(messages, response_format={"type": "json_object"})
        if not response:
            logger.error("生成测试用例失败：AI返回为空")
            return None
        
        # 解析响应
        result = safe_json_loads(response)
        if not result:
            return None
            
        # 验证测试用例格式
        testcases = result.get("testcases")
        if not isinstance(testcases, list):
            logger.error(f"测试用例格式错误: {type(testcases)}")
            return None
            
        # 验证每个测试用例的结构
        valid_testcases = []
        for testcase in testcases:
            if not isinstance(testcase, dict):
                logger.error(f"测试用例项格式错误: {type(testcase)}")
                continue
                
            # 验证必要字段
            required_fields = ['id', 'module', 'name', 'level', 'precondition', 'steps', 'expected']
            missing_fields = [field for field in required_fields if field not in testcase]
            if missing_fields:
                logger.error(f"测试用例缺少必要字段: {missing_fields}")
                continue
                
            # 确保steps和expected是列表
            if not isinstance(testcase['steps'], list):
                testcase['steps'] = [testcase['steps']]
            if not isinstance(testcase['expected'], list):
                testcase['expected'] = [testcase['expected']]
                
            valid_testcases.append(testcase)
            
        return valid_testcases if valid_testcases else None
