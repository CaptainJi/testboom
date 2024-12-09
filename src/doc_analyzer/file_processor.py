import os
import zipfile
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..logger.logger import logger
from ..utils.common import ensure_dir

class FileProcessor:
    """文件处理器"""
    
    def __init__(self, work_dir: Optional[str] = None):
        """初始化文件处理器
        
        Args:
            work_dir: 工作目录,默认为当前目录下的temp
        """
        self.work_dir = Path(work_dir) if work_dir else Path("temp")
        ensure_dir(self.work_dir)
    
    def extract_zip(self, zip_path: str) -> List[Path]:
        """解压zip文件
        
        Args:
            zip_path: zip文件路径
            
        Returns:
            List[Path]: 解压后的文件路径列表
        """
        try:
            # 创建解压目录
            extract_dir = self.work_dir / Path(zip_path).stem
            ensure_dir(extract_dir)
            
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 返回所��文件路径
            return list(extract_dir.rglob('*.*'))
            
        except Exception as e:
            logger.error(f"解压zip文件失败: {e}")
            return []
    
    def classify_files(self, files: List[Path]) -> Dict[str, List[Path]]:
        """对文件进行分类
        
        Args:
            files: 文件路径列表
            
        Returns:
            Dict[str, List[Path]]: 按类型分类的文件字典
        """
        classified = {
            'images': [],  # 图片文件
            'documents': [],  # 文档文件
            'others': []  # 其他文件
        }
        
        for file in files:
            mime_type, _ = mimetypes.guess_type(str(file))
            if mime_type:
                if mime_type.startswith('image/'):
                    classified['images'].append(file)
                elif mime_type.startswith(('text/', 'application/')):
                    classified['documents'].append(file)
                else:
                    classified['others'].append(file)
            else:
                classified['others'].append(file)
        
        return classified
    
    def get_file_content(self, file_path: Path) -> Tuple[str, Optional[str]]:
        """获取文件内容
        
        Args:
            file_path: 文件��径
            
        Returns:
            Tuple[str, Optional[str]]: (文件类型, 文件内容)
            文件类型: image或text
            文件内容: 图片文件返回None,文本文件返回内容
        """
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('image/'):
                return 'image', None
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return 'text', f.read()
        except Exception as e:
            logger.error(f"读取文件内容失败: {e}")
            return 'unknown', None
    
    def cleanup(self):
        """清理工作目录"""
        try:
            import shutil
            shutil.rmtree(self.work_dir)
            logger.info(f"清理工作目录成功: {self.work_dir}")
        except Exception as e:
            logger.error(f"清理工作目录失败: {e}") 