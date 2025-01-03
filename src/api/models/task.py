from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, JSON, DateTime
from src.db.base import Base

class Task(Base):
    """任务模型"""
    
    __tablename__ = "task"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False, comment="任务类型")
    status = Column(String(20), nullable=False, comment="任务状态")
    progress = Column(Integer, default=0, comment="任务进度")
    result = Column(JSON, nullable=True, comment="任务结果")
    error = Column(String(500), nullable=True, comment="错误信息")
    project_name = Column(String(100), nullable=True, comment="项目名称")
    module_name = Column(String(100), nullable=True, comment="模块名称")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间") 