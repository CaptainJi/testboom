from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.models.base import ResponseModel
from src.api.services.case import CaseService
from src.api.services.task import TaskManager
from src.db.session import get_db
from fastapi.responses import FileResponse, Response
from pathlib import Path
from loguru import logger
import json
import time
import os
from src.ai_core.chat_manager import ChatManager
from src.utils.plantuml import render_plantuml
import asyncio
from datetime import datetime
from sqlalchemy import select
from src.db.models import TestCaseHistory

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
    remark: Optional[str] = None  # 添加修改说明字段

class CaseHistoryInfo(BaseModel):
    """用例修改历史信息"""
    field: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    remark: Optional[str]
    created_at: datetime

class CaseDetailInfo(CaseInfo):
    """用例详细信息，包含修改历史"""
    history: List[CaseHistoryInfo]
    
    class Config:
        from_attributes = True

class BatchDeleteCasesRequest(BaseModel):
    """批量删除用例请求模型"""
    case_ids: List[str]

class CaseList(BaseModel):
    """用例列表响应模型"""
    total: int
    items: List[CaseInfo]

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
            cases_from_db, _ = await CaseService.list_cases(
                db,
                task_id=request.task_id,
                page=1,
                page_size=1000  # 设置较大的页面大小以获取所有用例
            )
            for case in cases_from_db:
                case_data = json.loads(case.content)
                cases.append(case_data)
        else:
            # 根据项目或模块导出用例
            cases_from_db, _ = await CaseService.list_cases(
                db,
                project=request.project_name,
                module=request.module_name,
                page=1,
                page_size=1000  # 设置较大的页面大小以获取所有用例
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
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[List[TaskInfo]]:
    """获取任务列表"""
    try:
        # 获取任务列表
        tasks, total = await TaskManager.list_tasks(
            task_type=task_type, 
            status=status, 
            page=page,
            page_size=page_size
        )
        
        # 转换为响应模型
        task_infos = []
        for task in tasks:
            result = task.get('result')
            
            # 如果有结果且包含进度信息
            if isinstance(result, dict) and result.get('progress'):
                # 获取所有相关用例的模块名称
                cases, _ = await CaseService.list_cases(
                    db=db,
                    task_id=task['id'],
                    page=1,
                    page_size=1000
                )
                # 提取所有不重复的模块名称
                module_names = sorted(list(set(case.module for case in cases if case.module)))
                result['module_names'] = module_names
            
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
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)) -> ResponseModel[TaskInfo]:
    """获取任务状态"""
    try:
        # 获取任务信息
        task = await TaskManager.get_task_info(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        # 转换任务结果
        result = task.get('result')
        if isinstance(result, dict) and result.get('progress'):
            # 获取所有相关用例的模块名称
            cases, _ = await CaseService.list_cases(
                db=db,
                task_id=task_id,
                page=1,
                page_size=1000
            )
            # 提取所有不重复的模块名称
            module_names = sorted(list(set(case.module for case in cases if case.module)))
            result['module_names'] = module_names
            
            # 如果有 path 字段，将其转换为列表
            if 'path' in result and isinstance(result['path'], str):
                result['path'] = result['path'].split(';') if result['path'] else []
        
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
        # 取用例
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
    modules: Optional[List[str]] = Query(None, description="模块名称列表，多个模块用逗号分隔"),
    task_id: Optional[str] = Query(default=None, description="任务ID过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[CaseList]:
    """获取测试用例列表
    
    Args:
        project: 项目名称过滤
        module: 模块名称过滤（单个模块）
        modules: 模块名称列表过滤（多个模块）
        task_id: 任务ID过滤
        page: 页码(从1开始)
        page_size: 每页数量
        db: 数据库会话
        
    Returns:
        ResponseModel[CaseList]: 用例列表响应
    """
    try:
        cases, total = await CaseService.list_cases(
            db,
            project=project,
            module=module,
            modules=modules,
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
            data=CaseList(
                total=total,
                items=case_infos
            )
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
        raise HTTPException(status_code=500, detail="批量删除用例失败")

@router.put("/{case_id}")
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[CaseDetailInfo]:
    """更新测试用例信息"""
    try:
        # 验证用例等级
        if case_update.level and case_update.level not in ["P0", "P1", "P2", "P3"]:
            raise HTTPException(
                status_code=400,
                detail="无效的用例等级，必须是 P0、P1、P2 或 P3"
            )
            
        # 验证用例状态
        valid_statuses = ["draft", "ready", "testing", "passed", "failed", "blocked"]
        if case_update.status and case_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的用例状态，必须是以下之一: {', '.join(valid_statuses)}"
            )
        
        # 更新用例
        updated_case = await CaseService.update_case(
            case_id=case_id,
            project=case_update.project,
            module=case_update.module,
            name=case_update.name,
            level=case_update.level,
            status=case_update.status,
            content=case_update.content,
            remark=case_update.remark,
            db=db
        )
        
        if not updated_case:
            raise HTTPException(status_code=404, detail="用例不存在")
            
        # 查询修改历史
        history_result = await db.execute(
            select(TestCaseHistory)
            .where(TestCaseHistory.case_id == case_id)
            .order_by(TestCaseHistory.created_at.desc())
        )
        history_records = history_result.scalars().all()
        
        # 转换为响应模型
        history = [
            CaseHistoryInfo(
                field=h.field,
                old_value=json.loads(h.old_value) if h.old_value else None,
                new_value=json.loads(h.new_value) if h.new_value else None,
                remark=h.remark,
                created_at=h.created_at
            )
            for h in history_records
        ]
        
        return ResponseModel(
            message="用例信息更新成功",
            data=CaseDetailInfo(
                case_id=updated_case.id,
                project=updated_case.project,
                module=updated_case.module,
                name=updated_case.name,
                level=updated_case.level,
                status=updated_case.status,
                content=json.loads(updated_case.content),
                history=history
            )
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用例信息更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用例信息更新失败")

@router.get("/{case_id}/plantuml")
async def export_case_plantuml(
    case_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[str]:
    """导出测试用例为PlantUML思维导图代码"""
    try:
        # 获取测试用例
        case = await CaseService.get_case_by_id(case_id, db)
        if not case:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        
        # 解析用例内容
        try:
            content = json.loads(case.content)
        except json.JSONDecodeError:
            logger.error(f"解析用例内容失败: {case.content}")
            raise HTTPException(status_code=500, detail="用例内容格式错误")
        
        # 生成PlantUML代码
        chat_manager = ChatManager()
        plantuml_code = await chat_manager.export_testcases_to_plantuml(
            [content],  # 传入单个用例的内容
            "mindmap"   # 固定生成思维导图
        )
        if not plantuml_code:
            raise HTTPException(status_code=500, detail="生成PlantUML失败")
        
        return ResponseModel(
            message="生成PlantUML思维导图成功",
            data=plantuml_code
        )
        
    except Exception as e:
        logger.error(f"导出PlantUML失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{case_id}/plantuml/async")
async def generate_plantuml_async(
    case_id: str,
    diagram_type: str = Query("mindmap", enum=["mindmap", "sequence"]),
    format: str = Query("svg", enum=["svg", "png"]),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[str]:
    """异步生成PlantUML图表"""
    try:
        # 获取测试用例
        case = await CaseService.get_case_by_id(case_id, db)
        if not case:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        
        # 解析用例内容
        try:
            content = json.loads(case.content)
        except json.JSONDecodeError:
            logger.error(f"解析用例内容失败: {case.content}")
            raise HTTPException(status_code=500, detail="用例内容格式错误")
        
        # 创建异步任务
        task_id = await TaskManager.create_task(
            task_type="plantuml_generation",  # 修改任务类型
            params={
                "case_id": case_id,
                "case_content": content,  # 直接传入用例内容
                "diagram_type": diagram_type,
                "format": format
            }
        )
        
        # 启动异步处理
        asyncio.create_task(process_plantuml_task(task_id, content, diagram_type, format))
        
        return ResponseModel(
            message="PlantUML生成任务已创建",
            data=task_id
        )
        
    except Exception as e:
        logger.error(f"创建PlantUML生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_plantuml_task(
    task_id: str,
    case_content: Dict[str, Any],
    diagram_type: str,
    format: str
):
    """处理PlantUML生成任务"""
    try:
        # 更新任务状态为处理中
        await TaskManager.update_task(task_id, status="processing", progress=10)
        
        # 生成PlantUML代码
        chat_manager = ChatManager()
        plantuml_code = await chat_manager.export_testcases_to_plantuml(
            [case_content],
            diagram_type
        )
        if not plantuml_code:
            await TaskManager.update_task(
                task_id,
                status="failed",
                error="生成PlantUML代码失败"
            )
            return
            
        await TaskManager.update_task(task_id, progress=50)
        
        # 渲染图片
        image_data = await render_plantuml(plantuml_code, format)
        if not image_data:
            await TaskManager.update_task(
                task_id,
                status="failed",
                error="渲染图片失败"
            )
            return
            
        # 保存图片到临时文件
        output_dir = Path("output/plantuml")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{task_id}.{format}"
        with open(output_path, "wb") as f:
            f.write(image_data)
            
        # 更新任务状态为完成
        await TaskManager.update_task(
            task_id,
            status="completed",
            progress=100,
            result={
                "file_path": str(output_path),
                "format": format,
                "diagram_type": diagram_type
            }
        )
        
    except Exception as e:
        logger.error(f"处理PlantUML任务失败: {str(e)}")
        await TaskManager.update_task(
            task_id,
            status="failed",
            error=str(e)
        )

@router.get("/plantuml/tasks/{task_id}")
async def get_plantuml_task_status(task_id: str) -> ResponseModel[Dict[str, Any]]:
    """获取PlantUML生成任务状态"""
    try:
        # 获取任务信息
        task = await TaskManager.get_task_info(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        if task["type"] != "plantuml_generation":
            raise HTTPException(status_code=400, detail="不是PlantUML生成任务")
            
        # 如果任务完成且有结果，添加文件下载链接
        if task["status"] == "completed" and task.get("result"):
            file_path = task["result"].get("file_path")
            if file_path and os.path.exists(file_path):
                task["result"]["download_url"] = f"/api/v1/cases/plantuml/download/{task_id}"
            
        return ResponseModel(
            data={
                "status": task["status"],
                "progress": task["progress"],
                "result": task.get("result"),
                "error": task.get("error")
            }
        )
        
    except Exception as e:
        logger.error(f"获取PlantUML生成任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plantuml/download/{task_id}")
async def download_plantuml(task_id: str) -> FileResponse:
    """下载生成的PlantUML图片"""
    try:
        # 获取任务信息
        task = await TaskManager.get_task_info(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        if task["type"] != "plantuml_generation":
            raise HTTPException(status_code=400, detail="不是PlantUML生成任务")
            
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="任务未完成")
            
        result = task.get("result", {})
        file_path = result.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
            
        return FileResponse(
            path=file_path,
            filename=f"plantuml_{task_id}.{result.get('format', 'svg')}",
            media_type=f"image/{result.get('format', 'svg')}"
        )
        
    except Exception as e:
        logger.error(f"下载PlantUML图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plantuml/status/{task_id}")
async def get_task_plantuml(
    task_id: str,
    modules: Optional[str] = Query(None, description="模块名称列表，多个模块用逗号分隔"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[str]:
    """获取任务生成的PlantUML思维导图结果"""
    try:
        # 获取任务信息
        task = await TaskManager.get_task_info(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查任务状态
        if task["status"] != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"任务尚未完成，当前状态: {task['status']}"
            )
        
        # 处理模块列表
        module_list = None
        if modules:
            module_list = [m.strip() for m in modules.split(',') if m.strip()]
        
        # 获取该任务相关的所有测试用例（不分页）
        cases, total = await CaseService.list_cases(
            task_id=task_id,
            page=1,
            page_size=1000,
            db=db,
            modules=module_list
        )
        
        if not cases:
            raise HTTPException(status_code=404, detail="未找到相关测试用例")
        
        # 提取用例内容并生成 PlantUML 代码
        chat_manager = ChatManager()
        testcases = [json.loads(case.content) for case in cases]
        plantuml_code = await chat_manager.export_testcases_to_plantuml(
            testcases,
            "mindmap"
        )
        
        if not plantuml_code:
            raise HTTPException(status_code=500, detail="生成思维导图失败")
        
        return ResponseModel(
            message="获取PlantUML思维导图成功",
            data=plantuml_code
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务PlantUML失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    delete_cases: bool = Query(False, description="是否同时删除关联的用例"),
    db: AsyncSession = Depends(get_db)
) -> ResponseModel[bool]:
    """删除任务
    
    Args:
        task_id: 任务ID
        delete_cases: 是否同时删除关联的用例
        db: 数据库会话
        
    Returns:
        ResponseModel[bool]: 删除结果
    """
    try:
        success = await TaskManager.delete_task(task_id, delete_cases, db)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或删除失败")
            
        return ResponseModel(
            message="任务删除成功",
            data=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除任务失败") 