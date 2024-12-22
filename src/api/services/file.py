import os
import shutil
from typing import Optional, List, Dict, Tuple
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
                                                # 上传��对象存储
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
                        # 移动本地存储
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
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None
    ) -> Tuple[List[File], int]:
        """获取文件列表
        
        Args:
            db: 数据库会话
            page: 页码(从1开始)
            page_size: 每页数量
            status: 文件状态过滤
            
        Returns:
            Tuple[List[File], int]: 文件列表和总数
        """
        try:
            # 构建查询
            query = select(File)
            
            # 添加状态过滤
            if status:
                query = query.where(File.status == status)
            
            # 添加排序(按创建时间倒序)
            query = query.order_by(File.created_at.desc())
            
            # 计算分页
            skip = (page - 1) * page_size
            
            # 获取总数
            total = await db.scalar(select(func.count()).select_from(query.subquery()))
            
            # 添加分页
            query = query.offset(skip).limit(page_size)
            
            # 执行查询
            result = await db.execute(query)
            files = result.scalars().all()
            
            return files, total
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            raise
    
    @classmethod
    async def delete_file(
        cls,
        file_id: str,
        db: AsyncSession
    ) -> bool:
        """删除文件
        
        Args:
            file_id: 文件ID
            db: 数据库会话
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取文件信息
            file = await cls.get_file_by_id(file_id, db)
            if not file:
                raise ValueError("文件不存在")
            
            # 获取存储服务
            storage_service = get_storage_service()
            
            # 删除存储中的文件
            if storage_service.enabled:
                # 处理可能存在的多个文件路径
                for path in cls._path_to_list(file.path):
                    if path.startswith('http://') or path.startswith('https://'):
                        # 从URL中提取对象名称
                        object_name = path.split('/')[-1]
                        await storage_service.delete_file(object_name)
            else:
                # 删除本地文件
                for path in cls._path_to_list(file.path):
                    full_path = os.path.join(cls.UPLOAD_DIR, path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
            
            # 删除数据库记录
            await db.delete(file)
            await db.commit()
            
            logger.info(f"文件删除成功: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}")
            raise

    @classmethod
    async def batch_delete_files(
        cls,
        file_ids: List[str],
        db: AsyncSession
    ) -> Dict[str, bool]:
        """批量删除文件
        
        Args:
            file_ids: 文件ID列表
            db: 数据库会话
            
        Returns:
            Dict[str, bool]: 每个文件的删除结果
        """
        results = {}
        for file_id in file_ids:
            try:
                success = await cls.delete_file(file_id, db)
                results[file_id] = success
            except Exception as e:
                logger.error(f"删除文件失败 {file_id}: {str(e)}")
                results[file_id] = False
        return results

    @classmethod
    async def update_file(
        cls,
        file_id: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        error: Optional[str] = None,
        db: AsyncSession = None
    ) -> Optional[File]:
        """更新文件信息
        
        Args:
            file_id: 文件ID
            name: 新的文件名
            status: 新的状态
            error: 错误信息
            db: 数据库会话
            
        Returns:
            Optional[File]: 更新后的文件信息
        """
        try:
            # 获取文件信息
            file = await cls.get_file_by_id(file_id, db)
            if not file:
                raise ValueError("文件不存在")
            
            # 更新字段
            if name is not None:
                file.name = name
            if status is not None:
                file.status = status
            if error is not None:
                file.error = error
            
            # 保存更新
            await db.commit()
            await db.refresh(file)
            
            logger.info(f"文件信息更新成功: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"文件信息更新失败: {str(e)}")
            raise