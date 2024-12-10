from typing import List, Dict, Optional, Any, Union
from .zhipu_api import ZhipuAI
from .prompt_template import PromptTemplate
from src.logger.logger import logger
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
        """初始化对话管理器
        
        - 创建AI接口实例
        - 初始化对话历史
        - 加载提示词模板
        """
        self.ai = ZhipuAI()
        self.history = []
        self.template = PromptTemplate()
    
    def chat(self, message: str) -> Optional[str]:
        """执行基础对话
        
        Args:
            message: 用户消息
            
        Returns:
            Optional[str]: AI的回复，如果出错则返回None
            
        功能：
        - 发送消息给AI
        - 记录对话历史
        - 处理AI响应
        """
        try:
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
            
        except Exception as e:
            logger.error(f"对话失败: {str(e)}")
            return None
    
    def chat_with_images(self, message: str, image_paths: List[str]) -> Optional[str]:
        """执行带图片的对话
        
        Args:
            message: 用户消息
            image_paths: 图片路径列表
            
        Returns:
            Optional[str]: AI的回复，如果出错则返回None
            
        功能：
        - 处理多个图片输入
        - 发送多模态消息给AI
        - 记录对话历史
        """
        try:
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
                "content": response.content
            })
            
            return response.content
            
        except Exception as e:
            logger.error(f"图片对话失败: {str(e)}")
            return None
    
    def analyze_requirement(self, content: str, image_paths: Optional[List[str]] = None) -> Optional[str]:
        """分析需求文档
        
        Args:
            content: 需求文本内容
            image_paths: 可选的需求相关图片路径列表
            
        Returns:
            Optional[str]: 分析结果，如果出错则返回None
            
        功能：
        - 使用模板生成分析提示词
        - 处理文本和图片输入
        - 生成结构化的分析结果
        """
        try:
            # 渲染分析模板
            prompt = self.template.render(
                template_name="requirement_analysis",
                content=content
            )
            if not prompt:
                return None
            
            # 根据是否有图片选择对话方式
            if image_paths:
                return self.chat_with_images(prompt, image_paths)
            else:
                return self.chat(prompt)
                
        except Exception as e:
            logger.error(f"需求分析失败: {str(e)}")
            return None
    
    def generate_testcases(self, summary: str, details: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """生成测试用例
        
        Args:
            summary: 需求分析总结
            details: 可选的详细分析结果
            
        Returns:
            Optional[List[Dict[str, Any]]]: 测试用例列表，如果出错则返回None
            
        功能：
        - 使用模板生成测试用例提示词
        - 处理AI响应生成结构化用例
        - 支持JSON格式的响应
        """
        try:
            # 构建完整的上下文内容
            context = summary
            if details:
                # 添加图片分析结果
                if "images" in details:
                    context += "\n\n图片分析结果:\n"
                    for img_result in details["images"]:
                        context += f"\n{img_result.get('content', '')}\n"
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
            
            # 解析JSON响应
            try:
                result = self.ai.parse_response(response)
                if not result:
                    logger.error("解析测试用例响应失败")
                    return None
                
                if not isinstance(result, dict):
                    logger.error(f"测试用例响应格式错误: {type(result)}")
                    return None
                
                testcases = result.get("testcases")
                if not testcases:
                    logger.error("测试用例列表为空")
                    return None
                
                if not isinstance(testcases, list):
                    logger.error(f"测试用例格式错误: {type(testcases)}")
                    return None
                
                # 验证每个测试用例的结构
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
                
                return testcases
                
            except json.JSONDecodeError as e:
                logger.error(f"解析测试用例JSON失败: {e}")
                return None
            except Exception as e:
                logger.error(f"处理测试用例响应失败: {e}")
                return None
                
        except Exception as e:
            logger.error(f"生成测试用例失败: {str(e)}")
            return None
    
    def analyze_testcases(self, testcases: str) -> Optional[str]:
        """分析测试用例
        
        Args:
            testcases: 测试用例内容
            
        Returns:
            Optional[str]: 分析结果，如果出错则返回None
            
        功能：
        - 使用模板生成用例分析提示词
        - 分析用例的覆盖情况
        - 提供改进建议
        """
        try:
            # 渲染测试用例分析模板
            prompt = self.template.render(
                template_name="testcase_understanding",
                content=testcases
            )
            if not prompt:
                return None
                
            # 调用AI分析测试用例
            return self.chat(prompt)
            
        except Exception as e:
            logger.error(f"分析测试用例失败: {str(e)}")
            return None
