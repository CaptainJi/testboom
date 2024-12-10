from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class FileBase(BaseModel):
    """文件基础模型"""
    name: str
    type: str
    status: str

class FileCreate(FileBase):
    """文件创建模型"""
    pass

class FileInfo(FileBase):
    """文件信息模型"""
    id: str
    path: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FileStatus(BaseModel):
    """文件状态模型"""
    id: str
    status: str
    error: Optional[str] = None 