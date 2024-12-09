from pathlib import Path
from typing import List, Dict, Any, Optional
from .file_processor import FileProcessor
from ..ai_core.chat_manager import ChatManager
from ..logger.logger import logger

class DocAnalyzer:
    """文档分析器"""
    
    def __init__(self, work_dir: Optional[str] = None):
        """初始化文档分析器
        
        Args:
            work_dir: 工作目录
        """
        self.file_processor = FileProcessor(work_dir)
        self.chat_manager = ChatManager()
        
    def analyze_prd(self, zip_path: str) -> Optional[str]:
        """分析PRD文档
        
        Args:
            zip_path: PRD压缩包路径
            
        Returns:
            Optional[str]: 分析结果
        """
        try:
            # 解压文件
            files = self.file_processor.extract_zip(zip_path)
            if not files:
                logger.error("未找到任何文件")
                return None
            
            # 分类文件
            classified = self.file_processor.classify_files(files)
            
            # 分析每个文件
            analysis_results = []
            
            # 处理图片文件
            for image in classified['images']:
                logger.info(f"分析图片: {image}")
                result = self.chat_manager.analyze_requirement(f"请分析这张图片({image.name})的内容:", [str(image)])
                if result:
                    analysis_results.append({
                        'file': image.name,
                        'type': 'image',
                        'content': result
                    })
            
            # 处理文档文件
            for doc in classified['documents']:
                logger.info(f"分析文档: {doc}")
                file_type, content = self.file_processor.get_file_content(doc)
                if content:
                    result = self.chat_manager.analyze_requirement(content)
                    if result:
                        analysis_results.append({
                            'file': doc.name,
                            'type': 'document',
                            'content': result
                        })
            
            if not analysis_results:
                logger.error("没有成功分析任何文件")
                return None
            
            # 构建汇总内容
            summary_content = ""
            for result in analysis_results:
                summary_content += f"\n文件名: {result['file']}\n类型: {result['type']}\n分析结果:\n{result['content']}\n{'='*50}\n"
            
            # 使用需求汇总模板生成总结
            final_result = self.chat_manager.prompt_manager.render(
                template_name="requirement_summary",
                content=summary_content
            )
            if not final_result:
                logger.error("生成需求汇总失败")
                return None
                
            # 使用通用模型生成最终报告
            final_report = self.chat_manager.chat(final_result)
            
            # 清理临时文件
            self.file_processor.cleanup()
            
            return final_report
            
        except Exception as e:
            logger.error(f"分析PRD文档失败: {e}")
            return None 