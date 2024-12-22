from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models.base import ResponseModel
from src.api.services.case import CaseService
from src.api.services.task import TaskManager
from src.db.session import get_db
from fastapi.responses import FileResponse
from pathlib import Path
from loguru import logger
import json
import time
import os

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

class CaseGenerateRequest(BaseModel):
    """用例生成请求模型"""
    file_id: str
    project_name: str
    module_name: Optional[str] = None

class CaseInfo(BaseModel):
    """用例信息模型"""
    case_id: str
    project: str
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
    result: Optional[Union[Dict[str, Any], List[CaseInfo]]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class ExportRequest(BaseModel):
    """导出请求模型"""
    case_ids: Optional[List[str]] = None
    project_name: Optional[str] = None
    module_name: Optional[str] = None
    task_id: Optional[str] = None

class CaseUpdate(BaseModel):
    """用例更新请求模型"""
    project: Optional[str] = None
    module: Optional[str] = None
    name: Optional[str] = None
    level: Optional[str] = None
    status: Optional[str] = None
    content: Optional[Dict[str, Any]] = None

class BatchDeleteCasesRequest(BaseModel):
    """批量删除用例请求模型"""
    case_ids: List[str]

@router.post("/export/excel")
async def export_cases_excel(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """导出测试用例到Excel
    
    Args:
        request: 导出请求参数
        db: 数据库会话
        
    Returns:
        FileResponse: Excel文件下载响应
    """
    try:
        cases = []
        
        # 根据不同的导出条件获取用例
        if request.case_ids:
            # 导出指定ID的用例
            for case_id in request.case_ids:
                case = await CaseService.get_case_by_id(case_id, db)
                if case:
                    case_data = json.loads(case.content)
                    cases.append(case_data)
        elif request.task_id:
            # 根据任务ID导出用例
            cases_from_db = await CaseService.list_cases(
                db,
                task_id=request.task_id
            )
            for case in cases_from_db:
                case_data = json.loads(case.content)
                cases.append(case_data)
        else:
            # 根据项目或模块导出用例
            cases_from_db = await CaseService.list_cases(
                db,
                project=request.project_name,
                module=request.module_name
            )
            for case in cases_from_db:
                case_data = json.loads(case.content)
                cases.append(case_data)
                
        if not cases:
            raise HTTPException(status_code=400, detail="未找到有效的测试用例")
            
        # 确保输出目录存在
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        filename_parts = []
        if request.project_name:
            filename_parts.append(request.project_name)
        if request.module_name:
            filename_parts.append(request.module_name)
        if request.task_id:
            filename_parts.append(f"task_{request.task_id}")
        filename_parts.append(str(int(time.time())))
        
        filename = f"testcases_{'_'.join(filename_parts)}.xlsx"
        excel_path = output_dir / filename
        
        # 导出Excel
        from src.doc_analyzer.doc_analyzer import DocAnalyzer
        analyzer = DocAnalyzer()
        analyzer._export_testcases_to_excel(cases, str(excel_path))
        
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=500, detail="Excel文件生成失败")
        
        # 返回文件下载响应
        return FileResponse(
            path=str(excel_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")

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
            request.project_name,
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

@router.get("/tasks")
async def list_tasks(
    type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量")
) -> ResponseModel[List[TaskInfo]]:
    """获取任务列表
    
    Args:
        type: 任务类型过滤
        status: 任务状态过滤
        page: 页码(从1开始)
        page_size: 每页数量
        
    Returns:
        ResponseModel[List[TaskInfo]]: 任务列表
    """
    try:
        # 计算skip和limit
        skip = (page - 1) * page_size
        limit = page_size
            
        # 获取任务列表
        tasks = TaskManager.list_tasks(
            type=type, 
            status=status, 
            skip=skip,
            limit=limit
        )
        
        # 转换为响应模型
        task_infos = []
        for task in tasks:
            # 转换任务结果
            result = None
            if task.get('result'):
                if isinstance(task['result'], dict) and task['result'].get('progress'):
                    result = task['result']
                else:
                    result = task['result']
            
            task_info = TaskInfo(
                task_id=task['id'],
                type=task['type'],
                status=task['status'],
                progress=task['progress'],
                result=result,
                error=task.get('error'),
                created_at=task['created_at'].isoformat(),
                updated_at=task['updated_at'].isoformat()
            )
            task_infos.append(task_info)
            
        return ResponseModel(data=task_infos)
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")

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
        if task.get('result'):
            if isinstance(task['result'], dict) and task['result'].get('progress'):
                # 处理进度信息
                result = task['result'].copy()
                # 如果有 path 字段，将其转换为列表
                if 'path' in result and isinstance(result['path'], str):
                    result['path'] = result['path'].split(';') if result['path'] else []
            else:
                # 处理用例列表
                result = []
                for case in task['result']:
                    # 记录每个用例的ID
                    case_id = case.get('id') or case.get('content', {}).get('id')
                    logger.debug(f"处理用例: id={case_id}")
                    
                    try:
                        case_info = CaseInfo(
                            case_id=case_id,
                            project=case.get('project', ''),
                            module=case.get('module', ''),
                            name=case.get('name', ''),
                            level=case.get('level', ''),
                            status=case.get('status', ''),
                            content=case.get('content', {})
                        )
                        result.append(case_info)
                        logger.debug(f"转换后的用例信息: {case_info}")
                    except Exception as e:
                        logger.error(f"转换用例信息失败: {str(e)}, 用例数据: {case}")
                        continue

        task_info = TaskInfo(
            task_id=task['id'],
            type=task['type'],
            status=task['status'],
            progress=task['progress'],
            result=result,
            error=task['error'],
            created_at=task['created_at'].isoformat(),
            updated_at=task['updated_at'].isoformat()
        )
            
        return ResponseModel(data=task_info)
        
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
    """获取单个用例详情
    
    Args:
        case_id: 用例ID
        db: 数据库会话
        
    Returns:
        ResponseModel[CaseInfo]: 用例详情
    """
    try:
        # ���取用例
        case = await CaseService.get_case_by_id(case_id, db)
        if not case:
            raise HTTPException(status_code=404, detail="用例不存在")
            
        # 解析用例内容
        try:
            content = json.loads(case.content)
        except json.JSONDecodeError:
            logger.error(f"解析用例内容失败: {case.content}")
            raise HTTPException(status_code=500, detail="用例内容格式错误")
            
        # 转换为响应模型
        case_info = CaseInfo(
            case_id=case.id,
            project=content.get('project', ''),
            module=case.module,
            name=case.name,
            level=case.level,
            status=case.status,
            content=content
        )
        
        return ResponseModel(data=case_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用例详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用例详情失败")

@router.get("/")
async def list_cases(
    project: Optional[str] = Query(default=None, description="项目名称过滤"),
    module: Optional[str] = Query(default=None, description="模块名称过滤"),
    task_id: Optional[str] = Query(default=None, description="任务ID过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[List[CaseInfo]]:
    """获取测试用例列表
    
    Args:
        project: 项目名称过滤
        module: 模块名称过滤
        task_id: 任务ID过滤
        page: 页码(从1开始)
        page_size: 每页数量
        db: 数据库会话
        
    Returns:
        ResponseModel[List[CaseInfo]]: 用例列表响应
    """
    try:
        cases, total = await CaseService.list_cases(
            db,
            project=project,
            module=module,
            task_id=task_id,
            page=page,
            page_size=page_size
        )
        
        # 转换为响应模型
        case_infos = []
        for case in cases:
            try:
                content = json.loads(case.content)
            except json.JSONDecodeError:
                logger.error(f"解析用例内容失败: {case.content}")
                raise HTTPException(status_code=500, detail="用例内容格式错误")
                
            case_info = CaseInfo(
                case_id=case.id,
                project=case.project,
                module=case.module,
                name=content.get("name", ""),
                level=content.get("level", ""),
                status=case.status,
                content=content
            )
            case_infos.append(case_info)
            
        return ResponseModel(
            data={
                "total": total,
                "items": case_infos
            }
        )
        
    except Exception as e:
        logger.error(f"获取用例列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用例列表失败")

@router.delete("/{case_id}")
async def delete_case(
    case_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[bool]:
    """删除测试用例"""
    try:
        success = await CaseService.delete_case(case_id, db)
        return ResponseModel(
            message="用例删除成功" if success else "用例删除失败",
            data=success
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"用例删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用例删除失败")

@router.delete("")
async def batch_delete_cases(
    request: BatchDeleteCasesRequest,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[Dict[str, bool]]:
    """批量删除测试用例"""
    try:
        results = await CaseService.batch_delete_cases(request.case_ids, db)
        return ResponseModel(
            message="批量删除完成",
            data=results
        )
    except Exception as e:
        logger.error(f"批量删除用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量删��用例失败")

@router.put("/{case_id}")
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[CaseInfo]:
    """更新测试用例信息"""
    try:
        updated_case = await CaseService.update_case(
            case_id=case_id,
            project=case_update.project,
            module=case_update.module,
            name=case_update.name,
            level=case_update.level,
            status=case_update.status,
            content=case_update.content,
            db=db
        )
        if not updated_case:
            raise HTTPException(status_code=404, detail="用例不存在")
            
        return ResponseModel(
            message="用例信息更新成功",
            data=CaseInfo.model_validate(updated_case)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"用例信息更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用例信息更新失败") 