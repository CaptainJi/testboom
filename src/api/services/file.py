import os
import shutil
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import File
from src.storage.storage import get_storage_service
from loguru import logger
import uuid
from pathlib import Path

class FileService:
    """文件服务"""
    
    UPLOAD_DIR = "storage/files"  # 本地文件存储目录
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
        
        # 保存文件到本地
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            raise
            
        # 获取存储服务
        storage_service = get_storage_service()
        storage_url = None
        
        if storage_service.enabled:
            try:
                # 上传到对象存储
                storage_url = await storage_service.upload_file(file_path)
                if storage_url:
                    logger.info(f"文件已上传到对象存储: {storage_url}")
            except Exception as e:
                logger.error(f"上传到对象存储失败: {str(e)}")
                # 继续使用本地文件
        
        # 创建文件记录
        db_file = File(
            name=file.filename,
            type="zip" if file_ext == ".zip" else "image",
            path=storage_url if storage_url else file_path,  # 如果有对象存储URL则使用URL
            status="pending"
        )
        
        # 保存到数据库
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        # 如果已上传到对象存储，删除本地文件
        if storage_url:
            try:
                os.remove(file_path)
                logger.info(f"本地临时文件已删除: {file_path}")
            except Exception as e:
                logger.warning(f"删除本地临时文件失败: {str(e)}")
        
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
        """
        获取文件路径
        
        Args:
            file: 文件记录
            force_download: 是否强制下载到本地
            
        Returns:
            str: 如果force_download为True返回本地路径，否则可能返回URL
        """
        storage_service = get_storage_service()
        
        # 如果是本地文件，直接返回路径
        if not storage_service.enabled or not file.path.startswith(('http://', 'https://')):
            return file.path
            
        # 如果不需要强制下载，直接返回URL
        if not force_download:
            return file.path
            
        # 如果需要下载，下载到本地
        try:
            # 创建临时目录
            temp_dir = Path(cls.UPLOAD_DIR) / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成临时文件路径
            file_ext = os.path.splitext(file.name)[1]
            temp_file = temp_dir / f"{uuid.uuid4()}{file_ext}"
            
            # 下载文件
            success = await storage_service.download_file(file.path, temp_file)
            if not success:
                raise Exception("文件下载失败")
            
            return str(temp_file)
            
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            raise