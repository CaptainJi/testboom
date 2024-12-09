from pathlib import Path
from typing import List, Dict, Any, Optional
from .file_processor import FileProcessor
from ..ai_core.chat_manager import ChatManager
from ..logger.logger import logger
import re

class DocAnalyzer:
    """文档分析器"""
    
    def __init__(self, work_dir: Optional[str] = None):
        """初始化文档分析器
        
        Args:
            work_dir: 工作目录
        """
        self.file_processor = FileProcessor(work_dir)
        self.chat_manager = ChatManager()
        
    def analyze_prd(self, zip_path: str) -> Optional[Dict[str, Any]]:
        """分析PRD文档
        
        Args:
            zip_path: PRD压缩包路径
            
        Returns:
            Optional[Dict[str, Any]]: 分析结果,包含:
            - summary: 需求汇总报告
            - testcases: 生成的测试用例
            - details: 详细的分析结果
        """
        try:
            # 解压文件
            files = self.file_processor.extract_zip(zip_path)
            if not files:
                logger.error("未找到任何文件")
                return None
            
            # 分类文件
            classified = self.file_processor.classify_files(files)
            logger.info(f"文件分类结果: {classified}")
            
            # 分析结果
            analysis_results = {
                'images': [],
                'documents': []
            }
            
            # 收集所有图片路径
            image_paths = []
            
            # 处理图片文件
            for image in classified['images']:
                logger.info(f"\n开始分析图片: {image}")
                image_paths.append(str(image))
                result = self.chat_manager.analyze_requirement(
                    f"请分析这张图片({image.name})的内容，分析结果用于创建测试用例时参考，所以请尽量描述图片中的功能点，如果图片中有文字说明信息，请尽量描述文字信息，如果图片中没有文字说明信息，请尽量描述图片中的功能点:",
                    [str(image)]
                )
                if result and "抱歉，我无法" not in result:
                    logger.info(f"\n图片分析结果:\n{result}")
                    # 解析结构化的分析结果
                    features = self._parse_analysis_result(result)
                    analysis_results['images'].append({
                        'file': image.name,
                        'content': result,
                        'features': features
                    })
            
            # 处理文档文件
            for doc in classified['documents']:
                logger.info(f"\n开始分析文档: {doc}")
                file_type, content = self.file_processor.get_file_content(doc)
                if content:
                    result = self.chat_manager.analyze_requirement(content)
                    if result:
                        logger.info(f"\n文档分析结果:\n{result}")
                        features = self._parse_analysis_result(result)
                        analysis_results['documents'].append({
                            'file': doc.name,
                            'content': result,
                            'features': features
                        })
            
            if not analysis_results['images'] and not analysis_results['documents']:
                logger.error("没有成功分析任何文件")
                return None
            
            # 构建汇总内容
            logger.info("\n开始构建汇总内容...")
            summary_content = self._build_summary_content(analysis_results)
            logger.info(f"\n汇总内容:\n{summary_content}")
            
            # 使用requirement_summary模板生成汇总报告
            logger.info("\n开始生成汇总报告...")
            final_report = self.chat_manager.analyze_requirement(
                summary_content,
                template_name="requirement_summary"
            )
            if not final_report:
                logger.error("生成汇总报告失败")
                return None
            logger.info(f"\n汇总报告:\n{final_report}")
            
            # 生成测试用例
            logger.info("\n开始生成测试用例...")
            testcases_report = self.chat_manager.generate_testcases(final_report)
            if not testcases_report:
                logger.error("生成测试用例失败")
                return None
            logger.info(f"\n测试用例生成结果:\n{testcases_report}")
            
            # 提取测试用例
            logger.info("\n开始提取测试用例...")
            testcases = self._extract_testcases(testcases_report)
            logger.info(f"\n提取的测试用例:\n{testcases}")
            
            # 清理临时文件
            self.file_processor.cleanup()
            
            return {
                'summary': final_report,
                'testcases': testcases,
                'details': analysis_results
            }
            
        except Exception as e:
            logger.error(f"分析PRD文档失败: {e}")
            return None

    def _parse_analysis_result(self, result: str) -> Dict[str, List[str]]:
        """解析分析结果,提取结构化信息
        
        Args:
            result: AI返回的分析结果文本
            
        Returns:
            Dict[str, List[str]]: 结构化的分析结果,包含:
            - functionality: 功能点列表
            - workflow: 业务流程
            - data_flow: 数据流向
            - interfaces: 接口定义
            - constraints: 约束条件
            - exceptions: 异常场景
        """
        features = {
            'functionality': [],
            'workflow': [],
            'data_flow': [],
            'interfaces': [],
            'constraints': [],
            'exceptions': []
        }
        
        try:
            # 分割文本为段落
            sections = result.split('\n\n')
            current_section = None
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                    
                # 检查是否是新的段落标题
                if '功能点列表' in section or '功能点' in section:
                    current_section = 'functionality'
                elif '业务流程' in section:
                    current_section = 'workflow'
                elif '数据流向' in section:
                    current_section = 'data_flow'
                elif '接口定义' in section:
                    current_section = 'interfaces'
                elif '约束条件' in section:
                    current_section = 'constraints'
                elif '异常场景' in section:
                    current_section = 'exceptions'
                
                # 如果在某个段落中,提取要点
                if current_section:
                    lines = section.split('\n')
                    for line in lines:
                        line = line.strip()
                        # 跳过段落标题和空行
                        if not line or any(keyword in line for keyword in ['功能点列表', '业务流程', '数据流向', '接口定义', '约束条件', '异常场景']):
                            continue
                        # ���取以-或*开头的要点
                        if line.startswith(('-', '*', '•')) or line.startswith(('1.', '2.', '3.')):
                            point = line.lstrip('-* 123456789.').strip()
                            if point:
                                features[current_section].append(point)
                    
            return features
            
        except Exception as e:
            logger.error(f"解析分析结果失败: {e}")
            return features

    def _build_summary_content(self, analysis_results: Dict[str, Any]) -> str:
        """构建汇总内容
        
        Args:
            analysis_results: 分析结果
            
        Returns:
            str: 汇总内容
        """
        summary_content = ""
        for result in analysis_results['images']:
            summary_content += f"\n文件名: {result['file']}\n类型: image\n分析结果:\n{result['content']}\n{'='*50}\n"
        for result in analysis_results['documents']:
            summary_content += f"\n文件名: {result['file']}\n类型: document\n分析结果:\n{result['content']}\n{'='*50}\n"
        return summary_content

    def _extract_testcases(self, final_report: str) -> List[Dict[str, str]]:
        """从最终报告中提取测试用例
        
        Args:
            final_report: 最终报告
            
        Returns:
            List[Dict[str, str]]: 测试用例列表,每个用例包含:
            - id: 用例ID
            - module: 所属模块
            - name: 用例名称
            - level: 用例等级
            - precondition: 前置条件
            - steps: 测试步骤
            - expected: 预期结果
            - actual: 实际结果
            - status: 测试状态
            - remark: 备注
        """
        testcases = []
        try:
            # 查找测试用例表格
            table_pattern = r'\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|[\r\n]+'
            tables = re.findall(table_pattern, final_report, re.MULTILINE)
            
            if not tables:
                logger.warning("未找到测试用例表格")
                return testcases
                
            # 解析每个表格
            for table in tables:
                rows = table.strip().split('\n')
                if len(rows) < 3:  # 至少需要表头、分隔行和一行数据
                    continue
                    
                # 跳过表头和分隔行
                for row in rows[2:]:
                    # 分割单元格,去除首尾的|和空格
                    cells = [cell.strip() for cell in row.split('|')[1:-1]]
                    if len(cells) != 10:  # 应该有10列
                        continue
                        
                    testcase = {
                        'id': cells[0],
                        'module': cells[1],
                        'name': cells[2],
                        'level': cells[3],
                        'precondition': cells[4],
                        'steps': cells[5],
                        'expected': cells[6],
                        'actual': cells[7],
                        'status': cells[8],
                        'remark': cells[9]
                    }
                    testcases.append(testcase)
                    
            return testcases
            
        except Exception as e:
            logger.error(f"提取测试用例失败: {e}")
            return testcases
