import os
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from ..logger.logger import logger
import json

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

def truncate_text(text: str, max_length: int = 4000) -> str:
    """按句子截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    sentences = text.split('。')
    result = []
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) + 1 <= max_length - 10:
            result.append(sentence)
            current_length += len(sentence) + 1
        else:
            break
    
    return '。'.join(result) + '。...(已截断)'

def process_multimodal_content(content: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
    """处理多模态内容
    
    Args:
        content: 多模态内容列表
        max_tokens: 最大token数
        
    Returns:
        List[Dict[str, Any]]: 处理后的内容列表
    """
    processed = []
    total_tokens = 0
    
    for item in content:
        if item["type"] == "text":
            # 截断文本以适应token限制
            text = truncate_text(item["text"], max_tokens - total_tokens)
            if text:
                processed.append({
                    "type": "text",
                    "text": text
                })
                total_tokens += len(text)
        elif item["type"] == "image":
            # 图片内容直接添加
            processed.append(item)
            
    return processed

def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全的JSON解析
    
    Args:
        text: JSON字符串
        default: 解析失败时的默认值
        
    Returns:
        Any: 解析结果或默认值
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return default

def ensure_directory(path: str) -> bool:
    """确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        bool: 是否成功创建或已存在
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        return True
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")
        return False

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 文件大小(字节)
        
    Returns:
        str: 格式化后的大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f}TB"