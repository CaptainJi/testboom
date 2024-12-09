import os
from pathlib import Path
from typing import Union, List
from ..logger.logger import logger

def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """确保目录存在,如果不存在则创建"""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_file_extension(file_path: Union[str, Path]) -> str:
    """获取文件扩展名"""
    return Path(file_path).suffix.lower()

def list_files(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
    """列出目录下符合模式的所有文件"""
    path = Path(directory)
    return list(path.glob(pattern))

def safe_file_write(file_path: Union[str, Path], content: str, mode: str = "w", encoding: str = "utf-8") -> bool:
    """安全地写入文件内容"""
    try:
        path = Path(file_path)
        ensure_dir(path.parent)
        with open(path, mode=mode, encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        return False

def safe_file_read(file_path: Union[str, Path], encoding: str = "utf-8") -> Union[str, None]:
    """安全地读取文件内容"""
    try:
        with open(file_path, encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return None 