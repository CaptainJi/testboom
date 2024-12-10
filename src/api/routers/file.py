from fastapi import APIRouter, UploadFile, File as FastAPIFile, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models.base import ResponseModel
from src.api.models.file import FileInfo, FileStatus
from src.api.services.file import FileService
from src.db.session import get_db
from loguru import logger

router = APIRouter(prefix="/api/v1/files", tags=["files"])

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
                error=db_file.error
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件状态失败") 