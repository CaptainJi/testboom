from typing import Optional
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class File(Base):
    """文件模型"""
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))  # zip/image
    path: Mapped[str] = mapped_column(String(1024))  # 文件路径或对象存储URL(多个URL用;分隔)
    status: Mapped[str] = mapped_column(String(50))  # pending/processing/completed/failed
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 关联关系
    cases: Mapped[list["TestCase"]] = relationship(back_populates="file", cascade="all, delete-orphan")

class TestCase(Base):
    """测试用例模型"""
    
    # 基本信息
    project: Mapped[str] = mapped_column(String(100))
    module: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(50))  # pending/ready/running/passed/failed
    content: Mapped[str] = mapped_column(Text)  # JSON格式存储用例详情
    
    # 关联关系
    file_id: Mapped[str] = mapped_column(ForeignKey("file.id"))
    file: Mapped["File"] = relationship(back_populates="cases") 