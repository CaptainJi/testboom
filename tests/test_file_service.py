import pytest
import pytest_asyncio
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.services.file import FileService
from src.db.models import File
import os
import tempfile
from pathlib import Path

@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话"""
    from src.db.session import get_db
    async for session in get_db():
        yield session
        await session.rollback()

@pytest.fixture
def test_image():
    """创建测试图片文件"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'fake image content')
        return Path(f.name)

@pytest.fixture
def test_zip():
    """创建测试ZIP文件"""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        f.write(b'fake zip content')
        return Path(f.name)

@pytest.mark.asyncio
async def test_save_upload_file(db_session: AsyncSession, test_image: Path):
    """测试保存上传文件"""
    # 创建测试文件
    file_content = test_image.read_bytes()
    file_name = test_image.name
    
    # 创建UploadFile对象
    upload_file = UploadFile(
        filename=file_name,
        file=open(test_image, 'rb')
    )
    
    try:
        # 保存文件
        db_file = await FileService.save_upload_file(upload_file, db_session)
        
        # 验证结果
        assert db_file is not None
        assert db_file.name == file_name
        assert db_file.type == "image"
        assert db_file.status == "pending"
        assert db_file.path is not None
        
    finally:
        # 清理测试文件
        upload_file.file.close()
        os.unlink(test_image)

@pytest.mark.asyncio
async def test_get_file_by_id(db_session: AsyncSession):
    """测试通过ID获取文件"""
    # 创建测试文件记录
    test_file = File(
        name="test.jpg",
        type="image",
        path="test/path",
        status="pending"
    )
    db_session.add(test_file)
    await db_session.commit()
    
    # 获取文件
    file = await FileService.get_file_by_id(test_file.id, db_session)
    
    # 验证结果
    assert file is not None
    assert file.id == test_file.id
    assert file.name == "test.jpg"
    assert file.type == "image"
    assert file.path == "test/path"
    assert file.status == "pending"

@pytest.mark.asyncio
async def test_delete_file(db_session: AsyncSession):
    """测试删除文件"""
    # 创建测试文件记录
    test_file = File(
        name="test.jpg",
        type="image",
        path="test/path",
        status="pending"
    )
    db_session.add(test_file)
    await db_session.commit()
    
    # 删除文件
    success = await FileService.delete_file(test_file.id, db_session)
    
    # 验证结果
    assert success is True
    
    # 验证文件已被删除
    deleted_file = await FileService.get_file_by_id(test_file.id, db_session)
    assert deleted_file is None

@pytest.mark.asyncio
async def test_update_file(db_session: AsyncSession):
    """测试更新文件信息"""
    # 创建测试文件记录
    test_file = File(
        name="test.jpg",
        type="image",
        path="test/path",
        status="pending"
    )
    db_session.add(test_file)
    await db_session.commit()
    
    # 更新文件信息
    updated_file = await FileService.update_file(
        file_id=test_file.id,
        name="updated.jpg",
        status="success",
        error="test error",
        db=db_session
    )
    
    # 验证结果
    assert updated_file is not None
    assert updated_file.name == "updated.jpg"
    assert updated_file.status == "success"
    assert updated_file.error == "test error"

@pytest.mark.asyncio
async def test_batch_delete_files(db_session: AsyncSession):
    """测试批量删除文件"""
    # 创建测试文件记录
    test_files = []
    for i in range(3):
        test_file = File(
            name=f"test{i}.jpg",
            type="image",
            path=f"test/path{i}",
            status="pending"
        )
        db_session.add(test_file)
        test_files.append(test_file)
    await db_session.commit()
    
    # 批量删除文件
    file_ids = [f.id for f in test_files]
    results = await FileService.batch_delete_files(file_ids, db_session)
    
    # 验证结果
    assert len(results) == 3
    for file_id in file_ids:
        assert results[file_id] is True
        # 验证文件已被删除
        deleted_file = await FileService.get_file_by_id(file_id, db_session)
        assert deleted_file is None