from fastapi import APIRouter, UploadFile, File as FastAPIFile, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models.base import ResponseModel
from src.api.models.file import FileInfo, FileStatus, FileList
from src.api.services.file import FileService
from src.db.session import get_db
from loguru import logger
from typing import Optional, List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/files", tags=["files"])

class FileUpdate(BaseModel):
    """文件更新请求模型"""
    name: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None

class BatchDeleteRequest(BaseModel):
    """批量删除请求模型"""
    file_ids: List[str]

@router.get("/")
async def get_files(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(default=None, description="文件状态过滤"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[FileList]:
    """获取文件列表
    
    Args:
        page: 页码(从1开始)
        page_size: 每页数量
        status: 文件状态过滤
        db: 数据库会话
        
    Returns:
        ResponseModel[FileList]: 文件列表响应
    """
    try:
        files, total = await FileService.get_files(db, page, page_size, status)
        return ResponseModel(
            data=FileList(
                total=total,
                items=[FileInfo.model_validate(file) for file in files]
            )
        )
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件列表失败")

@router.post("/upload")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[FileInfo]:
    """上传文件(支持zip和图片)"""
    try:
        # 保存文件
        db_file = await FileService.save_upload_file(file, db)
        return ResponseModel(
            message="文件上传成功",
            data=FileInfo.model_validate(db_file)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件上传失败")

@router.get("/{file_id}")
async def get_file_status(
    file_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[FileStatus]:
    """获取文件状态"""
    try:
        # 获取文件信息
        db_file = await FileService.get_file_by_id(file_id, db)
        if not db_file:
            raise HTTPException(status_code=404, detail="文件不存在")
            
        return ResponseModel(
            data=FileStatus(
                id=db_file.id,
                status=db_file.status,
                storage_url=db_file.storage_url,
                error=db_file.error
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件状态失败")

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[bool]:
    """删除文件"""
    try:
        success = await FileService.delete_file(file_id, db)
        return ResponseModel(
            message="文件删除成功" if success else "文件删除失败",
            data=success
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"文件删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件删除失败")

@router.delete("")
async def batch_delete_files(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[Dict[str, bool]]:
    """批量删除文件"""
    try:
        results = await FileService.batch_delete_files(request.file_ids, db)
        return ResponseModel(
            message="批量删除完成",
            data=results
        )
    except Exception as e:
        logger.error(f"批量删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量删除文件失败")

@router.put("/{file_id}")
async def update_file(
    file_id: str,
    file_update: FileUpdate,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[FileInfo]:
    """更新文件信息"""
    try:
        updated_file = await FileService.update_file(
            file_id=file_id,
            name=file_update.name,
            status=file_update.status,
            error=file_update.error,
            db=db
        )
        if not updated_file:
            raise HTTPException(status_code=404, detail="文件不存在")
            
        return ResponseModel(
            message="文件信息更新成功",
            data=FileInfo.model_validate(updated_file)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"文件信息更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件信息更新失败") 