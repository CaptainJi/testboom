import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# 现在可以导入项目模块
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.db.models import Base

# 设置测试环境变量
os.environ["STORAGE_ENABLED"] = "false"  # 禁用对象存储
os.environ["DB_URL"] = "sqlite+aiosqlite:///:memory:"  # 使用内存数据库

# 创建测试数据库引擎
test_engine = create_async_engine(
    os.environ["DB_URL"],
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True
)

# 创建测试会话工厂
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """设置测试数据库"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()