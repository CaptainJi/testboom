import os
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
from ..ai_core.chat_manager import ChatManager
from ..logger.logger import logger
from .file_processor import FileProcessor

class DocAnalyzer:
    """文档分析器"""
    
    def __init__(self, work_dir: Optional[str] = None):
        """初始化文档分析器
        
        Args:
            work_dir: 工作目录,默认为当前目录下的temp
        """
        self.work_dir = work_dir
        self.file_processor = FileProcessor(work_dir)
        self.chat_manager = ChatManager()
        
        # 支持的图片格式
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp']
        # 最大图片大小(10MB)
        self.max_image_size = 10 * 1024 * 1024
    
    def _validate_image(self, image_path: Path) -> bool:
        """验证图片是否有效
        
        Args:
            image_path: 图片路径
            
        Returns:
            bool: 图片是否有效
        """
        try:
            # 检查文件是否存在
            if not image_path.exists():
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            # 检查文件大小
            file_size = image_path.stat().st_size
            if file_size > self.max_image_size:
                logger.error(f"图片文件过大: {image_path}, 大小: {file_size/1024/1024:.2f}MB")
                return False
            
            # 检查文件格式
            file_ext = image_path.suffix.lower()
            if file_ext not in self.supported_formats:
                logger.error(f"不支持的图片格式: {image_path}, 格式: {file_ext}")
                return False
            
            # 检查MIME类型
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type or not mime_type.startswith('image/'):
                logger.error(f"无效的图片MIME类型: {image_path}, MIME: {mime_type}")
                return False
            
            # 尝试读取文件
            with open(image_path, 'rb') as f:
                # 读取前几个字节检查文件头
                header = f.read(8)
                # 检查是否为空文件
                if not header:
                    logger.error(f"图片文件为空: {image_path}")
                    return False
                # 检查是否为损坏的文件
                if len(header) < 8:
                    logger.error(f"图片文件可能已损坏: {image_path}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证图片失败: {image_path}, 错误: {e}")
            logger.exception(e)
            return False
    
    def analyze_prd(self, zip_path: str) -> Optional[Dict[str, Any]]:
        """分析PRD文档
        
        Args:
            zip_path: PRD文档zip文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 分析结果
        """
        try:
            # 解压文件
            files = self.file_processor.extract_zip(zip_path)
            if not files:
                logger.error(f"解压文件失败或文件为空: {zip_path}")
                return None
            
            # 分类文件
            classified = self.file_processor.classify_files(files)
            logger.info(f"文件分类结果: {classified}")
            
            # 分析图片
            image_results = []
            for image_path in classified['images']:
                logger.info(f"\n开始分析图片: {image_path}")
                
                # 验证图片
                if not self._validate_image(image_path):
                    logger.warning(f"跳过无效图片: {image_path}")
                    continue
                
                # 分析图片
                result = self.chat_manager.chat_with_images(
                    "请分析这张图片，提取所有对测试用例设计有帮助的信息。",
                    [str(image_path)]
                )
                
                if result:
                    logger.info(f"\n图片分析结果:\n{result}")
                    image_results.append({
                        'file': str(image_path),
                        'content': result,
                        'features': self._extract_features(result)
                    })
                else:
                    logger.error(f"分析图片失败: {image_path}")
            
            # 构建汇总内容
            logger.info("\n开始构建汇总内容...")
            summary_content = ""
            for result in image_results:
                summary_content += f"\n文件名: {Path(result['file']).name}\n"
                summary_content += f"类型: image\n"
                summary_content += f"分析结果:\n{result['content']}\n"
                summary_content += "=" * 50 + "\n"
            
            # 生成汇总报告
            logger.info("\n开始生成汇总报告...")
            summary = self.chat_manager.analyze_requirement(summary_content)
            if not summary:
                logger.error("生成汇总报告失败")
                return None
            
            # 生成测试用例
            logger.info("\n开始生成测试用例...")
            testcases = self.chat_manager.generate_testcases(
                summary,
                {'images': image_results}
            )
            if not testcases:
                logger.error("生成测试用例失败")
                return None
            
            # 导出测试用例到Excel
            if testcases:
                self._export_testcases_to_excel(testcases)
            
            # 清理临时文件
            self.file_processor.cleanup()
            
            return {
                'summary': summary,
                'testcases': testcases,
                'details': {
                    'images': image_results
                }
            }
            
        except Exception as e:
            logger.error(f"分析PRD文档失败: {e}")
            logger.exception(e)
            return None
    
    def _extract_features(self, content: str) -> Dict[str, Any]:
        """从分析结果中提取特征
        
        Args:
            content: 分析结果文本
            
        Returns:
            Dict[str, Any]: 提取的特征
        """
        try:
            features = {
                'functionality': [],  # 功能点
                'workflow': [],  # 业务流程
                'data_flow': [],  # 数据流向
                'interfaces': [],  # 接口定义
                'constraints': [],  # 约束条件
                'exceptions': []  # 异常场景
            }
            
            # 按段落分割内容
            paragraphs = content.split('\n\n')
            
            current_section = None
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # 识别段落类型
                if '功能点' in para or '功能列表' in para:
                    current_section = 'functionality'
                elif '业务流程' in para or '操作步骤' in para:
                    current_section = 'workflow'
                elif '数据流' in para:
                    current_section = 'data_flow'
                elif '接口' in para:
                    current_section = 'interfaces'
                elif '约束' in para or '限制' in para:
                    current_section = 'constraints'
                elif '异常' in para or '错误' in para:
                    current_section = 'exceptions'
                elif current_section:
                    # 将内容添加到当前段落类型
                    features[current_section].append(para)
            
            return features
            
        except Exception as e:
            logger.error(f"提取特征失败: {e}")
            logger.exception(e)
            return {
                'functionality': [],
                'workflow': [],
                'data_flow': [],
                'interfaces': [],
                'constraints': [],
                'exceptions': []
            }
    
    def _export_testcases_to_excel(self, testcases: List[Dict[str, Any]], output_path: str):
        """导出测试用例到Excel
        
        Args:
            testcases: 测试用例列表
            output_path: 输出文件路径
        """
        try:
            # 转换测试用例格式
            data = []
            for tc in testcases:
                data.append({
                    '用例ID': tc.get('id', ''),
                    '所属模块': tc.get('module', ''),
                    '用例名称': tc.get('name', ''),
                    '用例等级': tc.get('level', ''),
                    '前置条件': tc.get('precondition', ''),
                    '测试步骤': '\n'.join(tc.get('steps', [])),
                    '预期结果': '\n'.join(tc.get('expected', [])),
                    '实际结果': tc.get('actual', ''),
                    '测试状态': tc.get('status', ''),
                    '备注': tc.get('remark', '')
                })
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 导出到Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"测试用例已导出到: {output_path}")
            
        except Exception as e:
            logger.error(f"导出测试用例失败: {e}")
            logger.exception(e)
            raise
