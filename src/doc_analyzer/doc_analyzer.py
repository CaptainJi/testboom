import os
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
from ..logger.logger import logger
from ..utils.common import ensure_dir
from ..ai_core.chat_manager import ChatManager
from .file_processor import FileProcessor
import pandas as pd

class DocAnalyzer:
    """文档分析器"""
    
    def __init__(self, work_dir: Optional[str] = None):
        """初始化文档分析器
        
        Args:
            work_dir: 工作目录,默认为当前目录下的temp
        """
        self.work_dir = Path(work_dir) if work_dir else Path("temp")
        self.file_processor = FileProcessor(work_dir)
        self.chat_manager = ChatManager()
    
    def analyze_prd(self, zip_path: str) -> Optional[Dict[str, Any]]:
        """分析PRD文档
        
        Args:
            zip_path: PRD文档压缩包路径
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            # 解压文件
            files = self.file_processor.extract_zip(zip_path)
            if not files:
                logger.error("解压文件失败")
                return None
            
            # 分类文件
            classified = self.file_processor.classify_files(files)
            logger.info(f"文件分类结果: {classified}")
            
            # 分析图片
            details = {"images": []}
            for image in classified["images"]:
                logger.info(f"\n开始分析图片: {image}")
                result = self.chat_manager.analyze_requirement(
                    f"请分析这张图片({image.name})的内容，分析结果用于创建测试用例时参考，所以请尽量描述图片中的功能点，如果图片中有文字说明信息，请尽量描述文字信息，如果图片中没有文字说明信息，请尽量描述图片中的功能点:",
                    [str(image)]
                )
                if result:
                    logger.info(f"\n图片分析结果:\n{result}")
                    details["images"].append({
                        "file": str(image),
                        "content": result,
                        "features": {
                            "functionality": [],
                            "workflow": [],
                            "data_flow": [],
                            "interfaces": [],
                            "constraints": [],
                            "exceptions": []
                        }
                    })
            
            # 构建汇总内容
            logger.info("\n开始构建汇总内容...")
            content = ""
            for image in details["images"]:
                content += f"\n文件名: {Path(image['file']).name}\n"
                content += f"类型: image\n"
                content += f"分析结果:\n{image['content']}\n"
                content += "="*50 + "\n"
            logger.info(f"\n汇总内容:\n{content}")
            
            # 生成汇总报告
            logger.info("\n开始生成汇总报告...")
            summary = self.chat_manager.analyze_requirement(content)
            if not summary:
                logger.error("生成汇总报告失败")
                return None
            logger.info(f"\n汇总报告:\n{summary}")
            
            # 生成测试用例
            logger.info("\n开始生成测试用例...")
            testcases = self.chat_manager.generate_testcases(summary.content if hasattr(summary, 'content') else summary)
            if not testcases:
                logger.error("生成测试用例失败")
                return None
            
            # 导出测试用例到Excel
            self._export_testcases_to_excel(testcases)
            
            # 清理临时文件
            self.file_processor.cleanup()
            
            return {
                "summary": summary.content if hasattr(summary, 'content') else summary,
                "testcases": testcases,
                "details": details
            }
            
        except Exception as e:
            logger.error(f"分析PRD文档失败: {e}")
            return None
    
    def _export_testcases_to_excel(self, testcases: List[Dict[str, Any]]):
        """导出测试用例到Excel
        
        Args:
            testcases: 测试用例列表
        """
        try:
            # 确保output目录存在
            output_dir = Path("output")
            ensure_dir(output_dir)
            
            # 转换测试用例格式
            rows = []
            for case in testcases:
                rows.append({
                    "用例ID": case["id"],
                    "所属模块": case["module"],
                    "用例名称": case["name"],
                    "用例等级": case["level"],
                    "前置条件": case["precondition"],
                    "测试步骤": "\n".join(case["steps"]),
                    "预期结果": "\n".join(case["expected"]),
                    "实际结果": case["actual"],
                    "测试状态": case["status"],
                    "备注": case["remark"]
                })
            
            # 创建DataFrame并导出到Excel
            df = pd.DataFrame(rows)
            
            # 设置列顺序
            columns = [
                "用例ID", "所属模块", "用例名称", "用例等级", 
                "前置条件", "测试步骤", "预期结果", "实际结果", 
                "测试状态", "备注"
            ]
            df = df[columns]
            
            # 导出到Excel
            excel_path = output_dir / "testcases.xlsx"
            writer = pd.ExcelWriter(excel_path, engine="openpyxl")
            
            # 写入数据
            df.to_excel(writer, index=False, sheet_name="测试用例")
            
            # 调整列宽
            worksheet = writer.sheets["测试用例"]
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            # 保存文件
            writer.close()
            logger.info(f"测试用例已导出到: {excel_path}")
            
        except Exception as e:
            logger.error(f"导出测试用例到Excel失败: {e}")
            raise
