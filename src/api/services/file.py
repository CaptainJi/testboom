import os
import shutil
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import File
from loguru import logger
import uuid

class FileService:
    """文件服务"""
    
    UPLOAD_DIR = "storage/files"  # 文件存储目录
    ALLOWED_EXTENSIONS = {".zip", ".png", ".jpg", ".jpeg"}  # 允许的文件类型
    
    @classmethod
    async def save_upload_file(
        cls,
        file: UploadFile,
        db: AsyncSession
    ) -> File:
        """保存上传的文件"""
        # 检查文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {file_ext}")
            
        # 确保存储目录存在
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, unique_filename)
        
        # 保存文件
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            raise
            
        # 创建文件记录
        db_file = File(
            name=file.filename,
            type="zip" if file_ext == ".zip" else "image",
            path=file_path,
            status="pending"
        )
        
        # 保存到数据库
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    @classmethod
    async def get_file_by_id(
        cls,
        file_id: str,
        db: AsyncSession
    ) -> Optional[File]:
        """根据ID获取文件信息"""
        result = await db.execute(
            select(File).where(File.id == file_id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def update_file_status(
        cls,
        file: File,
        status: str,
        error: Optional[str] = None,
        db: AsyncSession = None
    ) -> File:
        """更新文件状态"""
        file.status = status
        if error:
            file.error = error
        
        if db:
            await db.commit()
            await db.refresh(file)
        
        return file 