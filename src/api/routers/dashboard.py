from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from src.api.models.base import ResponseModel
from src.db.session import get_db
from src.db.models import File, TestCase
from loguru import logger
from typing import Dict, Any
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[Dict[str, Any]]:
    """获取仪表盘数据
    
    Returns:
        ResponseModel[Dict[str, Any]]: 仪表盘数据，包括：
        - total_files: 文件总数
        - total_cases: 用例总数
        - recent_files: 最近上传的文件数（7天内）
        - recent_cases: 最近生成的用例数（7天内）
        - case_stats: 用例统计信息（按等级和状态分类）
        - file_stats: 文件统计信息（按类型和状态分类）
    """
    try:
        # 获取当前时间和7天前的时间
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        
        # 统计文件数据
        total_files = await db.scalar(select(func.count()).select_from(File))
        recent_files = await db.scalar(
            select(func.count())
            .select_from(File)
            .where(File.created_at >= seven_days_ago)
        )
        
        # 统计用例数据
        total_cases = await db.scalar(select(func.count()).select_from(TestCase))
        recent_cases = await db.scalar(
            select(func.count())
            .select_from(TestCase)
            .where(TestCase.created_at >= seven_days_ago)
        )
        
        # 按等级统计用例
        case_level_stats = await db.execute(
            select(TestCase.level, func.count())
            .group_by(TestCase.level)
        )
        case_level_stats = dict(case_level_stats.all())
        
        # 按状态统计用例
        case_status_stats = await db.execute(
            select(TestCase.status, func.count())
            .group_by(TestCase.status)
        )
        case_status_stats = dict(case_status_stats.all())
        
        # 按类型统计文件
        file_type_stats = await db.execute(
            select(File.type, func.count())
            .group_by(File.type)
        )
        file_type_stats = dict(file_type_stats.all())
        
        # 按状态统计文件
        file_status_stats = await db.execute(
            select(File.status, func.count())
            .group_by(File.status)
        )
        file_status_stats = dict(file_status_stats.all())
        
        # 组装返回数据
        dashboard_data = {
            "total_files": total_files or 0,
            "total_cases": total_cases or 0,
            "recent_files": recent_files or 0,
            "recent_cases": recent_cases or 0,
            "case_stats": {
                "by_level": case_level_stats,
                "by_status": case_status_stats
            },
            "file_stats": {
                "by_type": file_type_stats,
                "by_status": file_status_stats
            }
        }
        
        return ResponseModel(data=dashboard_data)
        
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取仪表盘数据失败") 