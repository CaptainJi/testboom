from typing import Optional, Union
from pathlib import Path
import minio
from minio.error import S3Error
import os
import base64
from src.config.settings import settings
from src.logger.logger import logger
import mimetypes

class StorageService:
    """存储服务类，处理文件上传和管理"""
    
    def __init__(self):
        """初始化存储服务"""
        self.enabled = settings.storage.STORAGE_ENABLED
        if not self.enabled:
            logger.info("存储服务未启用")
            return
            
        try:
            self.client = minio.Minio(
                settings.storage.STORAGE_ENDPOINT,
                access_key=settings.storage.STORAGE_ACCESS_KEY,
                secret_key=settings.storage.STORAGE_SECRET_KEY,
                secure=settings.storage.STORAGE_PUBLIC_URL.startswith("https"),
                region=settings.storage.STORAGE_REGION or None
            )
            
            # 确保存储桶存在
            if not self.client.bucket_exists(settings.storage.STORAGE_BUCKET_NAME):
                self.client.make_bucket(settings.storage.STORAGE_BUCKET_NAME)
                logger.info(f"创建存储桶: {settings.storage.STORAGE_BUCKET_NAME}")
            
            logger.info("存储服务初始化成功")
        except Exception as e:
            logger.error(f"存储服务初始化失败: {str(e)}")
            raise
    
    async def upload_file(self, file_path: Union[str, Path], object_name: Optional[str] = None) -> Optional[str]:
        """
        上传文件到对象存储
        
        Args:
            file_path: 本地文件路径
            object_name: 对象存储中的文件名，如果不指定则使用文件名
            
        Returns:
            str: 文件的公共访问URL，如果存储服务未启用则返回None
        """
        if not self.enabled:
            logger.info("存储服务未启用，跳过文件上传")
            return None
            
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            # 如果未指定object_name，使用文件名
            if not object_name:
                object_name = file_path.name
                
            logger.info(f"开始上传文件: {file_path} -> {object_name}")
            
            # 上传文件
            self.client.fput_object(
                settings.storage.STORAGE_BUCKET_NAME,
                object_name,
                str(file_path)
            )
            
            # 构建公共访问URL
            url = f"{settings.storage.STORAGE_PUBLIC_URL}/{settings.storage.STORAGE_BUCKET_NAME}/{object_name}"
            logger.info(f"文件上传成功: {url}")
            
            # 记录存储详情
            logger.debug(f"存储详情: bucket={settings.storage.STORAGE_BUCKET_NAME}, "
                        f"object={object_name}, size={file_path.stat().st_size}, "
                        f"content_type={mimetypes.guess_type(str(file_path))[0]}")
            
            return url
            
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            raise
    
    async def get_file_url(self, object_name: str) -> Optional[str]:
        """
        获取文件的公共访问URL
        
        Args:
            object_name: 对象存储中的文件名
            
        Returns:
            str: 文件的公共访问URL，如果存储服务未启用则返回None
        """
        if not self.enabled:
            return None
            
        return f"{settings.storage.STORAGE_PUBLIC_URL}/{settings.storage.STORAGE_BUCKET_NAME}/{object_name}"
    
    async def delete_file(self, object_name: str) -> bool:
        """
        删除对象存储中的文件
        
        Args:
            object_name: 对象存储中的文件名
            
        Returns:
            bool: 删除是否成功，如果存储服务未启用则返回False
        """
        if not self.enabled:
            return False
            
        try:
            self.client.remove_object(settings.storage.STORAGE_BUCKET_NAME, object_name)
            logger.info(f"文件删除成功: {object_name}")
            return True
        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}")
            return False
    
    async def get_file_content(self, file_path: Union[str, Path]) -> Union[str, None]:
        """
        获取文件内容
        如果存储服务启用，返回文件URL
        如果存储服务未启用，返回文件的base64编码
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            str: 文件URL或base64编码
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        if self.enabled:
            # 上传文件并返回URL
            return await self.upload_file(file_path)
        else:
            # 返回文件的base64编码
            with open(file_path, "rb") as f:
                file_content = f.read()
                return base64.b64encode(file_content).decode('utf-8')
    
    async def download_file(self, url: str, local_path: Union[str, Path]) -> bool:
        """
        从对象存储下载文件到本地
        
        Args:
            url: 文件URL
            local_path: 本地保存路径
            
        Returns:
            bool: 下载是否成功
        """
        if not self.enabled:
            return False
            
        try:
            # 从URL中提取对象名称
            object_name = url.split('/')[-1]
            
            # 下载文件
            self.client.fget_object(
                settings.storage.STORAGE_BUCKET_NAME,
                object_name,
                str(local_path)
            )
            
            logger.info(f"文件下载成功: {url} -> {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件下载失败: {str(e)}")
            return False

# 全局存储服务实例
_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    """获取存储服务实例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service 