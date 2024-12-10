from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models.base import ResponseModel
from src.api.services.case import CaseService
from src.api.services.task import TaskManager
from src.db.session import get_db
from loguru import logger
import json

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

class CaseGenerateRequest(BaseModel):
    """用例生成请求模型"""
    file_id: str
    module_name: Optional[str] = None

class CaseInfo(BaseModel):
    """用例信息模型"""
    case_id: str
    module: str
    name: str
    level: str
    status: str
    content: dict
    
    class Config:
        from_attributes = True

class TaskInfo(BaseModel):
    """任务信息模型"""
    task_id: str
    type: str
    status: str
    progress: int
    result: Optional[List[CaseInfo]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

@router.post("/generate")
async def generate_cases(
    request: CaseGenerateRequest,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[str]:
    """生成测试用例
    
    返回任务ID，用于后续查询生成结果
    """
    try:
        # 启动用例生成任务
        task_id = await CaseService.generate_cases_from_file(
            request.file_id,
            request.module_name,
            db
        )
        
        return ResponseModel(
            message="用例生成任务已启动",
            data=task_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用例生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用例生成失败")

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> ResponseModel[TaskInfo]:
    """获取任务状态"""
    try:
        # 获取任务信息
        task = TaskManager.get_task_info(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        # 转换任务结果
        result = None
        if task['result']:
            result = [
                CaseInfo(
                    case_id=case['id'],
                    module=case['module'],
                    name=case['name'],
                    level=case['level'],
                    status=case['status'],
                    content=case['content']
                )
                for case in task['result']
            ]
            
        return ResponseModel(
            data=TaskInfo(
                task_id=task['id'],
                type=task['type'],
                status=task['status'],
                progress=task['progress'],
                result=result,
                error=task['error'],
                created_at=task['created_at'].isoformat(),
                updated_at=task['updated_at'].isoformat()
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务状态失败")

@router.get("/{case_id}")
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[CaseInfo]:
    """获取用例详情"""
    try:
        # 获取用例
        case = await CaseService.get_case_by_id(case_id, db)
        if not case:
            raise HTTPException(status_code=404, detail="用例不存在")
            
        return ResponseModel(
            data=CaseInfo(
                case_id=case.id,
                module=case.module,
                name=case.name,
                level=case.level,
                status=case.status,
                content=json.loads(case.content)
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用例失败")

@router.get("/")
async def list_cases(
    module: Optional[str] = None,
    level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[List[CaseInfo]]:
    """获取用例列表"""
    try:
        # 获取用例列表
        cases = await CaseService.list_cases(db, module, level)
        
        # 转换为响应模型
        case_infos = [
            CaseInfo(
                case_id=case.id,
                module=case.module,
                name=case.name,
                level=case.level,
                status=case.status,
                content=json.loads(case.content)
            )
            for case in cases
        ]
        
        return ResponseModel(data=case_infos)
    except Exception as e:
        logger.error(f"获取用例列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用例列表失败") 