from typing import List, Dict, Optional, Any, Callable
from .graph.chat import ChatGraph
from .prompt_template import PromptTemplate
from src.logger.logger import logger
from src.utils.decorators import handle_exceptions
from src.utils.common import safe_json_loads
from src.utils.plantuml_generator import PlantUMLGenerator
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.memory import BaseMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from pydantic import Field
import json
import asyncio

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
        self.chat_graph = ChatGraph()
        self.template = PromptTemplate()
        self.memory = ChatMemory()

    @handle_exceptions(default_return=None)
    async def analyze_requirement(
        self, 
        content: str, 
        image_paths: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """分析需求文档
        
        Args:
            content: 文本内容
            image_paths: 图片路径列表
            progress_callback: 进度回调函数，参数为(当前进度, 总进度)
            
        Returns:
            Optional[Dict[str, Any]]: 分析结果
        """
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
                    "你是一个专业的需求分析专家。请仔细分析需求文档中的图片，提取关键信息并生成结构化的分析结果。\n"
                    "分析要点和返回格式要求：\n"
                    "{\n"
                    "  \"需求背景\": {\n"
                    "    \"项目背景\": \"项目的具体业务场景和目标\",\n"
                    "    \"业务目标\": [\"目标1\", \"目标2\"],\n"
                    "    \"主要痛点\": [\"痛点1\", \"痛点2\"],\n"
                    "    \"解决方案\": \"具体的解决方案\"\n"
                    "  },\n"
                    "  \"整体功能架构\": {\n"
                    "    \"系统模块\": [\"模块1\", \"模块2\"],\n"
                    "    \"功能结构\": [\"功能1\", \"功能2\"],\n"
                    "    \"核心功能\": [\"功能1\", \"功能2\"],\n"
                    "    \"辅助功能\": [\"功能1\", \"功能2\"]\n"
                    "  },\n"
                    "  \"核心业务流程\": {\n"
                    "    \"业务场景\": [\"场景1\", \"场景2\"],\n"
                    "    \"操作步骤\": [\"步骤1\", \"步骤2\"],\n"
                    "    \"业务规则\": [\"规则1\", \"规则2\"],\n"
                    "    \"处理逻辑\": [\"逻辑1\", \"逻辑2\"]\n"
                    "  },\n"
                    "  \"系统交互关系\": {\n"
                    "    \"交互流程\": [\"流程1\", \"流程2\"],\n"
                    "    \"模块调用\": [\"调用1\", \"调用2\"],\n"
                    "    \"数据传递\": [\"数据流1\", \"数据流2\"],\n"
                    "    \"接口依赖\": [\"依赖1\", \"依赖2\"]\n"
                    "  }\n"
                    "}\n\n"
                    "注意事项：\n"
                    "1. 必须基于图片内容进行分析，不要使用通用模板\n"
                    "2. 确保返回完整的 JSON 格式\n"
                    "3. 字段名称必须与示例格式完全一致\n"
                    "4. 分析要全面但简洁，避免冗长"
                )
            }]
            
            # 添加用户消息
            messages.append({
                "role": "user",
                "content": prompt,
                **({"images": image_paths} if image_paths else {})
            })
            
            logger.debug(f"发送消息到AI:\n{json.dumps(messages, ensure_ascii=False, indent=2)}")
            
            # 使用新的chat_graph发送请求
            response = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await (
                        self.chat_graph.chat(
                            messages=messages,
                            response_format={"type": "json_object"},
                            timeout=180  # 3分钟超时
                        )
                    )
                    
                    if not response:
                        logger.warning(f"第{attempt + 1}次尝试未收到响应")
                        continue
                        
                    # 尝试解析JSON
                    result = safe_json_loads(response)
                    if result:
                        logger.info(f"第{attempt + 1}次尝试成功解析响应")
                        break
                    
                    logger.warning(f"第{attempt + 1}次尝试解析JSON失败")
                    
                except Exception as e:
                    logger.error(f"第{attempt + 1}次尝试失败: {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # 等待2秒后重试
                    continue
                
                # 更新进度
                if progress_callback:
                    progress_callback(attempt + 1, max_retries)
            
            if not response or not result:
                logger.error("需求分析失败：未能获取有效响应")
                return None
            
            logger.debug(f"收到AI响应:\n{response[:200]}...")
            
            # 检查结果格式并转换
            if isinstance(result, list):
                logger.debug("收到列表格式的响应，将合并结果")
                if not result:
                    logger.error("需求分析失败：响应列表为空")
                    return None
                # 使用第一个结果作为基础
                result = result[0]
            
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
            elif "需求分析报告" in result:
                result = result["需求分析报告"]
                logger.debug("从 需求分析报告 字段中提取结果")
            
            # 标准化字段名称（移除序号前缀）
            normalized_result = {}
            for key, value in result.items():
                # 移除可能的序号前缀（如 "1. "）
                clean_key = key.split(". ")[-1] if ". " in key else key
                normalized_result[clean_key] = value
            
            logger.debug(f"标准化后的结果:\n{json.dumps(normalized_result, ensure_ascii=False, indent=2)}")
            
            # 检查必要字段
            required_fields = ['整体功能架构', '核心业务流程', '系统交互关系']
            if image_paths:
                required_fields.append('需求背景')  # 移除关联信息的强制要求
            
            missing_fields = [field for field in required_fields if field not in normalized_result]
            if missing_fields:
                # 如果缺少字段，尝试从原始响应中提取更多信息
                for key in result.keys():
                    clean_key = key.split(". ")[-1] if ". " in key else key
                    # 检查是否有相似的字段名
                    for required_field in missing_fields[:]:
                        if (required_field in clean_key.lower() or 
                            clean_key.lower() in required_field.lower()):
                            normalized_result[required_field] = result[key]
                            missing_fields.remove(required_field)
                
                # 再次检查是否还有缺失字段
                if missing_fields:
                    logger.warning(f"需求分析缺少字段 - {missing_fields}，但将继续处理")
            
            # 如果是多图片分析，进行汇总
            if image_paths and len(image_paths) > 1:
                logger.info("开始生成多图片分析总结")
                summary_prompt = self.template.render(
                    "requirement_batch_summary",
                    content=json.dumps(normalized_result, ensure_ascii=False)
                )
                
                if summary_prompt:
                    try:
                        # 构建总结消息
                        summary_messages = [{
                            "role": "system",
                            "content": (
                                "你是一个专业的需求分析专家。请对多张需求图片的分析结果进行总结。\n"
                                "要求：\n"
                                "1. 合并相同或相似的功能点\n"
                                "2. 解决可能的冲突点\n"
                                "3. 保持关键信息的完整性\n"
                                "4. 确保返回完整的JSON格式\n"
                                "5. 控制返回内容的大小，避免过于冗长"
                            )
                        }, {
                            "role": "user",
                            "content": summary_prompt
                        }]
                        
                        # 使用chat_graph生成总结
                        logger.info("使用chat_graph生成总结")
                        summary_response = await self.chat_graph.chat(
                            messages=summary_messages,
                            response_format={"type": "json_object"},
                            timeout=180  # 3分钟超时
                        )
                        
                        if summary_response:
                            summary_result = safe_json_loads(summary_response)
                            if summary_result and isinstance(summary_result, dict):
                                logger.info("成功生成多图片分析总结")
                                # 保留原始分析中的某些字段
                                for key in ['需求背景', '关联信息']:
                                    if key in normalized_result and key not in summary_result:
                                        summary_result[key] = normalized_result[key]
                                normalized_result = summary_result
                                logger.debug(f"总结果:\n{json.dumps(summary_result, ensure_ascii=False, indent=2)}")
                            else:
                                logger.warning("总结结果解析失败，将使用原始分析结果")
                                logger.debug(f"无效的总结响应:\n{summary_response[:200]}...")
                        else:
                            logger.warning("未收到总结响应，将使用原始分析结果")
                            
                    except Exception as e:
                        logger.error(f"生成总结时出错: {str(e)}")
                        logger.warning("将使用原始分析结果")
            
            # 更新记忆
            self.memory.save_context(
                {"input": prompt},
                {"output": json.dumps(normalized_result, ensure_ascii=False)}
            )
            
            logger.info("需求分析完成")
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
                    f"你是一个专业的测试用例设计专家。现请专注分析需求中的{batch_type}部分。"
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
            
            response = await self.chat_graph.chat(messages, response_format={"type": "json_object"})
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
        retry_count: int = 3,
        retry_delay: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """生成单个批次的测试用例
        
        Args:
            batch_type: 批次类型
            batch_data: 批次数据
            focus: 关注点
            retry_count: 重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            Optional[List[Dict[str, Any]]]: 测试用例列表
        """
        last_error = None
        for attempt in range(retry_count):
            try:
                logger.info(f"开始生成{batch_type}批次测试用例 (尝试 {attempt + 1}/{retry_count})")
                
                # 构建提示词
                prompt = (
                    f"请基于下{batch_type}信息生成测试用例：\n\n"
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
                
                # 发送请求
                response = await self.chat_graph.chat(
                    [{
                        "role": "system",
                        "content": f"你是测试专家，请专注于{batch_type}相关的测试用例生成。"
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    response_format={"type": "json_object"},
                    timeout=180  # 增加超时时间到3分钟
                )
                
                if not response:
                    logger.warning(f"{batch_type}批次生成失败，尝试次数: {attempt + 1}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None
                
                # 解析响应
                result = safe_json_loads(response)
                if not result:
                    logger.error(f"{batch_type}批次响应解析失败")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None
                
                # 验证测试用例格式
                testcases = result.get("testcases")
                if not isinstance(testcases, list):
                    logger.error(f"{batch_type}批次响应格式错误")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return None
                
                logger.info(f"成功生成{batch_type}批次测试用例，数量: {len(testcases)}")
                return testcases
                
            except Exception as e:
                last_error = e
                logger.error(f"{batch_type}批次生成出错 (尝试 {attempt + 1}/{retry_count}): {str(e)}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay)
                    continue
        
        if last_error:
            logger.error(f"{batch_type}批次生成最终失败: {str(last_error)}")
        return None

    @handle_exceptions(default_return=None)
    async def generate_testcases(
        self,
        summary: Dict[str, Any],
        details: Optional[Dict[str, Any]] = None,
        project_name: Optional[str] = None,
        progress_callback: Optional[Callable[[str, None], None]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """生成测试用例
        
        Args:
            summary: 需求分析结果
            details: 额外的细节信息
            project_name: 项目名称
            progress_callback: 进度回调函数，参数为(当前阶段, None)
            
        Returns:
            Optional[List[Dict[str, Any]]]: 测试用例列表
        """
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
                # 更新进度
                if progress_callback:
                    progress_callback(batch["type"], None)
                    
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
                    # 设置项目名称
                    if project_name:
                        testcase['project'] = project_name
                    valid_testcases.append(testcase)
            
            return valid_testcases
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {str(e)}")
            return None

    @handle_exceptions(default_return=None)
    async def export_testcases_to_plantuml(
        self,
        testcases: List[Dict[str, Any]],
        diagram_type: str = "mindmap"
    ) -> Optional[str]:
        """导出测试用例为PlantUML格式
        
        Args:
            testcases: 测试用例列表
            diagram_type: 图表类型 ("mindmap" 或 "sequence")
            
        Returns:
            Optional[str]: PlantUML代码
        """
        try:
            logger.info(f"开始导出测试用例为PlantUML格式，图表类型: {diagram_type}")
            
            generator = PlantUMLGenerator()
            
            if diagram_type == "mindmap":
                logger.info("生成思维导图")
                return generator.generate_mindmap(testcases)
            elif diagram_type == "sequence":
                logger.info("生成时序图")
                # 对于时序图，每个用例生成单独的图
                sequence_diagrams = []
                for case in testcases:
                    diagram = generator.generate_sequence(case)
                    if diagram:
                        sequence_diagrams.append(diagram)
                
                if not sequence_diagrams:
                    logger.error("没有生成任何时序图")
                    return None
                    
                return "\n\n".join(sequence_diagrams)
            else:
                logger.error(f"不支持的图表类型: {diagram_type}")
                return None
                
        except Exception as e:
            logger.error(f"导出PlantUML失败: {str(e)}")
            return None
