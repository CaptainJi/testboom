import os
import shutil
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import File
from src.storage.storage import get_storage_service
from loguru import logger
import uuid
from pathlib import Path
from sqlalchemy import func

class FileService:
    """文件服务"""
    
    BASE_DIR = "data"  # 基础目录
    UPLOAD_DIR = "data/files"  # 本地文件存储目录
    TEMP_DIR = "data/temp"  # 临时文件目录
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
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, unique_filename)
        
        # 保存文件到本地
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            raise
            
        # 上传到对象存储
        storage_url = None
        try:
            storage_service = get_storage_service()
            if storage_service.enabled:
                storage_url = await storage_service.upload_file(file_path)
                logger.info(f"文件已上传到对象存储: {storage_url}")
        except Exception as e:
            logger.error(f"文件上传到对象存储失败: {str(e)}")
            # 这里我们不抛出异常，因为本地存储已经成功
            
        # 创建文件记录
        db_file = File(
            name=file.filename,
            type="zip" if file_ext == ".zip" else "image",
            path=file_path,  # 使用本地文件路径
            storage_url=storage_url,  # 记录对象存储URL
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
    
    @classmethod
    async def get_local_file_path(
        cls,
        file: File,
        force_download: bool = False
    ) -> str:
        """获取文件本地路径"""
        # 直接返回本地路径
        return file.path
    
    @classmethod
    async def get_files(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None
    ) -> tuple[List[File], int]:
        """获取文件列表
        
        Args:
            db: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status: 文件状态过滤
            
        Returns:
            tuple[List[File], int]: (文件列表, 总记录数)
        """
        try:
            # 构建基础查询
            base_query = select(File)
            if status:
                base_query = base_query.where(File.status == status)
            
            # 获取总数
            count_query = select(func.count()).select_from(base_query.subquery())
            total = await db.scalar(count_query)
            
            # 获取分页数据
            query = base_query.offset(skip).limit(limit).order_by(File.created_at.desc())
            result = await db.execute(query)
            files = result.scalars().all()
            
            logger.info(f"获取文件列表成功: {len(files)}/{total} 条记录")
            return files, total
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            raise