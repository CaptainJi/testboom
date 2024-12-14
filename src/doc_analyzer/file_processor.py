import os
import zipfile
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..logger.logger import logger
from ..utils.common import ensure_dir

class FileProcessor:
    """文件处理器
    
    负责处理文件相关操作，包括：
    1. 文件解压
    2. 文件分类
    3. 文件内容读取
    4. 图片验证
    5. 临时文件清理
    """
    
    def __init__(self, work_dir: Optional[str] = None) -> None:
        """初始化文件处理器
        
        Args:
            work_dir: 工作目录,默认为当前目录下的temp
        """
        self.work_dir = Path(work_dir) if work_dir else Path("temp")
        ensure_dir(self.work_dir)
        
        # 支持的图片格式
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp']
        # 最大图片大小(10MB)
        self.max_image_size = 10 * 1024 * 1024
    
    def validate_image(self, image_path: Path) -> bool:
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
            
            # 返回所有文件路径
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
        """获取文��内容
        
        Args:
            file_path: 文件路径
            
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
    
    def cleanup(self) -> None:
        """清理工作目录"""
        try:
            import shutil
            shutil.rmtree(self.work_dir)
            logger.info(f"清理工作目录成功: {self.work_dir}")
        except Exception as e:
            logger.error(f"清理工作目录失败: {e}") 