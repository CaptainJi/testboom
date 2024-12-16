from typing import List, Dict, Optional, Any
from .zhipu_api import ZhipuAI
from .prompt_template import PromptTemplate
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions
from src.utils.common import safe_json_loads
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.memory import BaseMemory
from langchain.memory import ChatMessageHistory
from pydantic import Field
import json

class ChatMemory(BaseMemory):
    """自定义聊天记忆管理"""
    
    chat_history: BaseChatMessageHistory = Field(default_factory=ChatMessageHistory)
    return_messages: bool = Field(default=True)
    
    def clear(self) -> None:
        """清除历史记忆"""
        self.chat_history.clear()
    
    @property
    def memory_variables(self) -> List[str]:
        """获取记忆变量列表"""
        return ["chat_history"]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量
        
        Args:
            inputs: 输入参数
            
        Returns:
            Dict[str, Any]: 包含历史记忆的字典
        """
        if self.return_messages:
            return {"chat_history": self.chat_history.messages}
        
        return {"chat_history": self._get_chat_string()}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """保存上下文
        
        Args:
            inputs: 输入内容
            outputs: 输出内容
        """
        input_str = inputs.get("input", "")
        output_str = outputs.get("output", "")
        
        self.chat_history.add_message(HumanMessage(content=input_str))
        self.chat_history.add_message(AIMessage(content=output_str))
    
    def _get_chat_string(self) -> str:
        """获取聊天历史字符串"""
        return "\n".join(
            [f"{msg.type}: {msg.content}" for msg in self.chat_history.messages]
        )

class ChatManager:
    """AI对话管理器"""
    
    def __init__(self):
        """初始化对话管理器"""
        self.ai = ZhipuAI()
        self.template = PromptTemplate()
        self.memory = ChatMemory()

    @handle_exceptions(default_return=None)
    async def analyze_requirement(
        self, 
        content: str, 
        image_paths: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """分析需求文档"""
        try:
            logger.info(f"开始分析需求文档，图片数量: {len(image_paths) if image_paths else 0}")
            
            # 清除之前的记忆
            self.memory.clear()
            
            # 生成提示词
            prompt = self.template.render(
                template_name="requirement_analysis",
                content=content
            )
            if not prompt:
                logger.error("生成需求分析提示词失败")
                return None
            
            logger.debug(f"生成的提示词:\n{prompt}")
            
            # 构建消息
            messages = [{
                "role": "system",
                "content": (
                    "你是一个专业的需求分析专家。请仔细分析需求文档，提取关键信息并生成结构化的分析结果。"
                    "分析要点包括：功能需求、非功能需求、业务规则、用户界面等。"
                    "请确保返回的是格式正确的JSON对象。"
                )
            }]
            
            # 添加用户消息
            messages.append({
                "role": "user",
                "content": prompt,
                **({"images": image_paths} if image_paths else {})
            })
            
            logger.debug(f"发送消息到AI:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            # 发送请求
            response = await (
                self.ai.chat_with_images(messages, image_paths) if image_paths
                else self.ai.chat(messages, response_format={"type": "json_object"})
            )
            
            if not response:
                logger.error("需求分析失败：未收到有效响应")
                return None
            
            logger.debug(f"收到AI响应:\n{response[:200]}...")
            
            # 解析响应
            result = safe_json_loads(response)
            if not result:
                logger.error("需求分析失败：响应格式错误")
                return None
            
            logger.debug(f"解析后的结果:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 检查结果格式
            if not isinstance(result, dict):
                logger.error(f"需求分析失败：响应不是字典类型 - {type(result)}")
                return None
            
            # 处理可能的包装字段
            if "report" in result:
                result = result["report"]
                logger.debug("从 report 字段中提取结果")
            elif "answer" in result:
                result = result["answer"]
                logger.debug("从 answer 字段中提取结果")
            
            # 标准化字段名称（移除序号前缀）
            normalized_result = {}
            for key, value in result.items():
                # 移除可能的序号前缀（如 "1. "）
                clean_key = key.split(". ")[-1] if ". " in key else key
                normalized_result[clean_key] = value
            
            logger.debug(f"标准化后的结果:\n{json.dumps(normalized_result, ensure_ascii=False, indent=2)}")
            
            required_fields = ['整体功能架构', '核心业务流程', '系统交互关系']
            missing_fields = [field for field in required_fields if field not in normalized_result]
            if missing_fields:
                logger.error(f"需求分析失败：缺少必要字段 - {missing_fields}")
                return None
            
            # 更新记忆
            self.memory.save_context(
                {"input": prompt},
                {"output": json.dumps(normalized_result, ensure_ascii=False)}
            )
            
            logger.info("需求分析��成")
            return normalized_result
            
        except Exception as e:
            logger.error(f"需求分析失败: {str(e)}", exc_info=True)
            return None

    async def _process_requirement_batch(
        self,
        content: str,
        batch_type: str
    ) -> Optional[str]:
        """处理单个需求批次"""
        try:
            logger.info(f"开始处理需求批次: {batch_type}")
            logger.debug(f"批次内容:\n{content}")
            
            messages = [{
                "role": "system",
                "content": (
                    f"你是一个专业的测试用例设计专家。现在请专注分析需求中的{batch_type}部分。"
                    "请结合之前的上下文，确保分析的连续性和完整性。"
                    "返回格式应为JSON对象。"
                )
            }, {
                "role": "user",
                "content": content
            }]
            
            # 添加历史记忆
            chat_history = self.memory.load_memory_variables({})
            if chat_history and "chat_history" in chat_history:
                history_messages = [
                    {
                        "role": "assistant" if isinstance(msg, AIMessage) else "user",
                        "content": msg.content
                    }
                    for msg in chat_history["chat_history"]
                ]
                messages.extend(history_messages)
                logger.debug(f"添加了 {len(history_messages)} 条历史消息")
            
            logger.debug(f"发送消息到AI:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            response = await self.ai.chat(messages, response_format={"type": "json_object"})
            if response:
                logger.debug(f"收到AI响应:\n{response[:200]}...")
                # 更新记忆
                self.memory.save_context(
                    {"input": content},
                    {"output": response}
                )
                return response
            
            logger.error(f"处理需求批次失败: {batch_type} - 未收到有效响应")
            return None
            
        except Exception as e:
            logger.error(f"处理需求批次时出错 ({batch_type}): {str(e)}", exc_info=True)
            return None

    async def _generate_batch_testcases(
        self,
        batch_type: str,
        batch_data: Dict[str, Any],
        focus: str,
        retry_count: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """生成单个批次的测试用例
        
        Args:
            batch_type: 批次类型
            batch_data: 批次数据
            focus: 关注点
            retry_count: 重试次数
            
        Returns:
            Optional[List[Dict[str, Any]]]: 测试用例列表
        """
        for attempt in range(retry_count):
            try:
                prompt = (
                    f"请基于以下{batch_type}信息生成测试用例：\n\n"
                    f"{json.dumps({batch_type: batch_data}, ensure_ascii=False, indent=2)}\n\n"
                    "要求：\n"
                    f"1. 重点关注{focus}\n"
                    "2. 包含正向流程和异常场景\n"
                    "3. 每个功能点生成2-3个用例\n"
                    "4. 测试用例格式：\n"
                    "{\n"
                    "  \"testcases\": [{\n"
                    "    \"id\": \"TC_001\",\n"
                    "    \"module\": \"模块名\",\n"
                    "    \"name\": \"用例名称\",\n"
                    "    \"level\": \"P0-P3\",\n"
                    "    \"precondition\": \"前置条件\",\n"
                    "    \"steps\": [\"步骤1\", \"步骤2\"],\n"
                    "    \"expected\": [\"预期1\", \"预期2\"],\n"
                    "    \"actual\": \"\",\n"
                    "    \"status\": \"\",\n"
                    "    \"remark\": \"\"\n"
                    "  }]\n"
                    "}"
                )
                
                response = await self.ai.chat(
                    [{
                        "role": "system",
                        "content": f"你是测试专家，请专注于{batch_type}相关的测试用例生成。"
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    response_format={"type": "json_object"}
                )
                
                if response:
                    result = safe_json_loads(response)
                    if result and isinstance(result.get("testcases"), list):
                        return result["testcases"]
                
                logger.warning(f"{batch_type}批次生成失败，尝试次数: {attempt + 1}")
                
            except Exception as e:
                logger.error(f"{batch_type}批次生成出错: {str(e)}")
                if attempt == retry_count - 1:
                    logger.error(f"{batch_type}批次生成失败，已达最大重试次数")
                    return None
        
        return None

    @handle_exceptions(default_return=None)
    async def generate_testcases(
        self, 
        summary: Dict[str, Any], 
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """生成测试用例"""
        try:
            logger.info("开始生成测试用例")
            
            # 清除之前的记忆
            self.memory.clear()
            
            # 构建需求信息
            requirement_info = {
                "功能架构": summary.get("整体功能架构", {}),
                "业务流程": summary.get("核心业务流程", {}),
                "系统交互": summary.get("系统交互关系", {})
            }
            
            # 分批生成测试用例
            all_testcases = []
            
            # 定义批次配置
            batches = [
                {
                    "type": "功能架构",
                    "focus": "功能验证和异常处理",
                    "data": requirement_info["功能架构"]
                },
                {
                    "type": "业务流程",
                    "focus": "流程完整性和业务规则",
                    "data": requirement_info["业务流程"]
                },
                {
                    "type": "系统交互",
                    "focus": "接口调用和数据传输",
                    "data": requirement_info["系统交互"]
                }
            ]
            
            # 处理每个批次
            for batch in batches:
                batch_cases = await self._generate_batch_testcases(
                    batch_type=batch["type"],
                    batch_data=batch["data"],
                    focus=batch["focus"]
                )
                
                if batch_cases:
                    all_testcases.extend(batch_cases)
                    logger.info(f"{batch['type']}部分生成了 {len(batch_cases)} 个测试用例")
            
            if not all_testcases:
                logger.error("没有生成有效的测试用例")
                return None
            
            # 验证和规范化测试用例
            valid_testcases = []
            required_fields = ['id', 'module', 'name', 'level', 'precondition', 'steps', 'expected']
            
            for idx, testcase in enumerate(all_testcases, 1):
                if not isinstance(testcase, dict):
                    continue
                    
                if all(field in testcase for field in required_fields):
                    # 确保steps和expected是列表
                    testcase['steps'] = [testcase['steps']] if isinstance(testcase['steps'], str) else testcase['steps']
                    testcase['expected'] = [testcase['expected']] if isinstance(testcase['expected'], str) else testcase['expected']
                    # 确保ID不重复
                    testcase['id'] = f"TC_{idx:03d}"
                    valid_testcases.append(testcase)
            
            if not valid_testcases:
                logger.error("没有生成有效的测试用例")
                return None
            
            logger.info(f"成功生成 {len(valid_testcases)} 个测试用例")
            return valid_testcases
            
        except Exception as e:
            logger.error(f"生成测试用例时发生错误: {str(e)}", exc_info=True)
            return None
