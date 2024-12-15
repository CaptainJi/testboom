import os
import shutil
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.db.models import File
from src.storage.storage import get_storage_service
from loguru import logger
import uuid
from pathlib import Path
import zipfile
import tempfile

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
        try:
            # 检查文件类型
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                raise ValueError(f"不支持的文件类型: {file_ext}")
                
            # 确保存储目录存在
            os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
            os.makedirs(cls.TEMP_DIR, exist_ok=True)
            
            # 获取存储服务
            storage_service = get_storage_service()
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                # 将上传的文件内容写入临时文件
                shutil.copyfileobj(file.file, temp_file)
                temp_file_path = temp_file.name
            
            try:
                paths = []  # 存储所有文件路径
                
                if file_ext == '.zip':
                    # 验证并解压ZIP文件
                    try:
                        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                            # 创建临时解压目录
                            with tempfile.TemporaryDirectory() as temp_dir:
                                zip_ref.extractall(temp_dir)
                                
                                # 处理所有图片文件
                                for root, _, files in os.walk(temp_dir):
                                    for filename in files:
                                        if os.path.splitext(filename)[1].lower() in {'.png', '.jpg', '.jpeg'}:
                                            img_path = os.path.join(root, filename)
                                            if storage_service.enabled:
                                                # 上传到对象存储
                                                url = await storage_service.upload_file(img_path)
                                                paths.append(url)
                                            else:
                                                # 复制到本地存储
                                                unique_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
                                                dest_path = os.path.join(cls.UPLOAD_DIR, unique_name)
                                                shutil.copy2(img_path, dest_path)
                                                paths.append(unique_name)  # 存储相对路径
                                
                                if not paths:
                                    raise ValueError("ZIP文件中没有找到有效的图片文件")
                    except zipfile.BadZipFile:
                        raise ValueError("无效的ZIP文件")
                else:
                    # 处理单个图片文件
                    unique_name = f"{uuid.uuid4()}{file_ext}"
                    if storage_service.enabled:
                        # 上传到对象存储
                        url = await storage_service.upload_file(temp_file_path)
                        paths.append(url)
                    else:
                        # 移动到本地存储
                        dest_path = os.path.join(cls.UPLOAD_DIR, unique_name)
                        shutil.move(temp_file_path, dest_path)
                        paths.append(unique_name)  # 存储相对路径
                
                # 使用分号连接所有路径
                final_path = ';'.join(paths)
                
                # 创建文件记录
                db_file = File(
                    name=file.filename,
                    type="zip" if file_ext == ".zip" else "image",
                    path=final_path,
                    status="pending"
                )
                
                # 保存到数据库
                db.add(db_file)
                await db.commit()
                await db.refresh(db_file)
                
                return db_file
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            raise
    
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
        """获取文件路径
        
        Args:
            file: 文件记录
            force_download: 是否强制重新下载（已废弃）
            
        Returns:
            str: 文件路径，如果是多个文件则用分号分隔
        """
        return file.path
    
    @staticmethod
    def _path_to_list(path: str) -> List[str]:
        """将分号分隔的路径转换为列表"""
        return [p.strip() for p in path.split(";") if p.strip()] if path else []
    
    @classmethod
    async def get_files(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None
    ) -> tuple[List[dict], int]:
        """获取文件列表"""
        try:
            # 构建基础查询
            base_query = select(File)
            if status:
                base_query = base_query.where(File.status == status)
            
            # 获取总数
            count_query = select(func.count()).select_from(base_query.subquery())
            total = await db.scalar(count_query)
            
            # 获取分页数据
            query = base_query.offset(skip).limit(limit).order_by(File.id.desc())
            result = await db.execute(query)
            db_files = result.scalars().all()
            
            # 转换文件记录
            files = []
            for file in db_files:
                file_dict = {
                    "id": file.id,
                    "name": file.name,
                    "type": file.type,
                    "status": file.status,
                    "error": file.error,
                    "path": file.path,  # 不再转换为列表
                    "created_at": file.created_at,
                    "updated_at": file.updated_at
                }
                files.append(file_dict)
            
            logger.info(f"获取文件列表成功: {len(files)}/{total} 条记录")
            return files, total
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            raise