from .base import Base
from .models import File, TestCase
from .session import get_db, engine

__all__ = [
    "Base",
    "File",
    "TestCase",
    "get_db",
    "engine"
]

# 创建数据库表
async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 