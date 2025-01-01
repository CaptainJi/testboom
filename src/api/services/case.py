import json
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import TestCase, File
from src.api.services.file import FileService
from src.ai_core.chat_manager import ChatManager
from src.api.services.task import TaskManager
from src.db.session import AsyncSessionLocal
from src.storage.storage import get_storage_service
from loguru import logger
import zipfile
import os
import glob
import asyncio
from pathlib import Path
import uuid
import httpx
from sqlalchemy import func

class CaseService:
    """用例服务"""
    
    def __init__(self):
        """初始化用例服务"""
        self.chat_manager = ChatManager()
    
    @classmethod
    async def generate_cases_from_file(
        cls,
        file_id: str,
        project_name: str,
        module_name: Optional[str],
        db: AsyncSession
    ) -> str:
        """从文件生成测试用例
        
        Args:
            file_id: 文件ID
            project_name: 项目名称
            module_name: 模块名称
            db: 数据库会话
            
        Returns:
            str: 任务ID
        """
        try:
            # 创建任务
            task_id = TaskManager.create_task("generate_cases")
            
            # 启动后台任务，不等待
            TaskManager.run_background_task(
                task_id,
                cls._generate_cases,
                file_id,
                project_name,
                module_name,
                task_id
            )
            
            return task_id
            
        except Exception as e:
            logger.error(f"启动用例生成任务失败: {str(e)}")
            if 'task_id' in locals():
                TaskManager.update_task(
                    task_id,
                    status='failed',
                    error=str(e)
                )
            raise
    
    @classmethod
    async def _generate_cases(
        cls,
        file_id: str,
        project_name: str,
        module_name: str,
        task_id: str
    ) -> None:
        """生成测试用例
        
        Args:
            file_id: 文件ID
            project_name: 项目名称
            module_name: 模块名称
            task_id: 任务ID
        """
        try:
            # 获取文件信息
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(File).where(File.id == file_id)
                )
                file = result.scalar_one_or_none()
                
                if not file:
                    raise ValueError("文件不存在")
                
                # 生成测试用例
                cases = await cls._process_zip_file(
                    file_paths=file.path,
                    project_name=project_name,
                    module_name=module_name,
                    task_id=task_id,
                    file_id=file_id
                )
                
                if not cases:
                    raise ValueError("生成用例失败")
                
                # 更新任务状态 - 开始保存用例
                TaskManager.update_task(
                    task_id,
                    result={
                        'progress': '正在保存测试用例...'
                    }
                )
                
                # 保存测试用例
                for case in cases:
                    case.file_id = file_id
                    case.task_id = task_id
                    session.add(case)
                
                # 更新文件状态
                file.status = "success"
                file.error = None
                await session.commit()
                
                # 更新任务状态 - 完成
                TaskManager.update_task(
                    task_id,
                    status='completed',
                    result={
                        'progress': '测试用例生成完成',
                        'cases_count': len(cases)
                    }
                )
                
        except Exception as e:
            error_msg = f"AI处理失败: {str(e)}"
            logger.error(error_msg)
            
            # 更新文件状态
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(File).where(File.id == file_id)
                )
                file = result.scalar_one_or_none()
                if file:
                    file.status = "failed"
                    file.error = error_msg
                    await session.commit()
            
            # 更新任务状态 - 失败
            TaskManager.update_task(
                task_id,
                status='failed',
                error=error_msg
            )
            
            raise ValueError(error_msg)
    
    @classmethod
    async def _process_zip_file(
        cls,
        file_paths: str,
        project_name: str,
        module_name: Optional[str],
        task_id: str,
        file_id: Optional[str] = None
    ) -> List[TestCase]:
        """处理ZIP文件解压后的图片
        
        Args:
            file_paths: 分号分隔的图片路径列表
            project_name: 项目名称
            module_name: 模块名称
            task_id: 任务ID
            file_id: 文件ID
            
        Returns:
            List[TestCase]: 生成的测试用例列表
        """
        try:
            # 创建ChatManager实例
            chat_manager = ChatManager()
            
            # 分割路径列表
            paths = file_paths.split(';')
            if not paths:
                raise ValueError("未找到图片文件")
            
            # 处理每个路径
            image_files = []
            for path in paths:
                if path.startswith('http://') or path.startswith('https://'):
                    # 如果是URL，直接使用
                    image_files.append(path)
                else:
                    # 如果是相对路径，转换为完整的本地路径
                    full_path = os.path.join(FileService.UPLOAD_DIR, path)
                    # 检查文件是否存在
                    if not os.path.exists(full_path):
                        logger.warning(f"文件不存在，跳过: {path}")
                        continue
                    image_files.append(full_path)
            
            if not image_files:
                raise ValueError("没有有效的图片文件")
            
            try:
                # 更新任务状态 - 开始分析需求
                if task_id:
                    TaskManager.update_task(
                        task_id,
                        result={
                            'progress': f'正在分析需求文档 (共{len(image_files)}张图片)...'
                        }
                    )
                
                # 定义状态更新回调
                def update_progress(current: int, total: int, stage: str = 'analyze'):
                    if task_id:
                        if stage == 'analyze':
                            TaskManager.update_task(
                                task_id,
                                result={
                                    'progress': f'正在分析第 {current}/{total} 张图片...'
                                }
                            )
                        elif stage == 'generate':
                            TaskManager.update_task(
                                task_id,
                                result={
                                    'progress': f'正在生成测试用例...'
                                }
                            )
                
                # 分析需求并生成用例
                summary = await chat_manager.analyze_requirement(
                    content=f"模块名称: {module_name}" if module_name else "",
                    image_paths=image_files,
                    progress_callback=lambda c, t: update_progress(c, t, 'analyze')
                )
                
                if not summary:
                    raise ValueError("需求分析失败")
                
                # 更新任务状态 - 开始生成用例
                if task_id:
                    TaskManager.update_task(
                        task_id,
                        result={
                            'progress': '正在生成功能架构相关测试用例...'
                        }
                    )
                    
                # 生成测试用例
                testcases = await chat_manager.generate_testcases(
                    summary=summary,
                    details={
                        "images": [
                            {
                                "content": summary,
                                "features": {}
                            }
                        ]
                    },
                    progress_callback=lambda stage, _: update_progress(1, None, 'generate')
                )
                
                if not testcases:
                    raise ValueError("用例生成失败")
                
                # 更新任务状态 - 用例生成完成
                if task_id:
                    TaskManager.update_task(
                        task_id,
                        result={
                            'progress': '测试用例生成完成，准备保存...',
                            'cases_count': len(testcases)
                        }
                    )
                
            except Exception as e:
                # 捕获并重新抛出带有更多上下文的错误
                error_msg = f"AI处理失败: {str(e)}"
                if isinstance(e, httpx.ReadTimeout):
                    error_msg = "AI服务响应超时，请稍后重试"
                elif isinstance(e, httpx.HTTPError):
                    error_msg = f"AI服务请求失败: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 转换为TestCase对象
            cases = []
            for case_data in testcases:
                case = TestCase(
                    project=project_name,
                    module=module_name or case_data.get('module', '默认模块'),
                    name=case_data.get('name', '未命名用例'),
                    level=case_data.get('level', 'P2'),
                    status='ready',
                    content=json.dumps(case_data),
                    task_id=task_id,  # 设置任务ID
                    file_id=file_id   # 设置文件ID
                )
                cases.append(case)
                
            return cases
            
        except Exception as e:
            error_msg = str(e) if str(e) else "未知错误"
            logger.error(f"处理图片文件失败: {error_msg}")
            raise ValueError(error_msg)
    
    @classmethod
    async def _process_image_file(
        cls,
        file_path: str,
        project_name: str,
        module_name: Optional[str],
        task_id: Optional[str] = None,
        file_id: Optional[str] = None
    ) -> List[TestCase]:
        """处理图片文件
        
        Args:
            file_path: 文件路径
            project_name: 项目名称
            module_name: 模块名称
            task_id: 任务ID
            file_id: 文件ID
            
        Returns:
            List[TestCase]: 测试用例列表
        """
        # 创建ChatManager实例
        chat_manager = ChatManager()
        
        # 检查是否是对象存储URL
        if file_path.startswith('http://') or file_path.startswith('https://'):
            # 如果是URL，直接使用
            image_paths = [file_path]
        else:
            # 如果是相对路径，转换为完整的本地路径
            full_path = os.path.join(FileService.UPLOAD_DIR, file_path)
            # 检查文件是否存在
            if not os.path.exists(full_path):
                raise ValueError(f"文件不存在: {file_path}")
            image_paths = [full_path]
        
        # 分析需求并生成用例
        summary = await chat_manager.analyze_requirement(
            content=f"模块名称: {module_name}" if module_name else "",
            image_paths=image_paths
        )
        
        if not summary:
            raise ValueError("需求分析失败")
            
        # 生成测试用例
        testcases = await chat_manager.generate_testcases(
            summary=summary,
            details={
                "images": [
                    {
                        "content": summary,
                        "features": {}
                    }
                ]
            }
        )
        
        if not testcases:
            raise ValueError("用例生成失败")
        
        # 转换为TestCase对象
        cases = []
        for case_data in testcases:
            case = TestCase(
                project=project_name,
                module=module_name or case_data.get('module', '默认模块'),
                name=case_data.get('name', '未命名用例'),
                level=case_data.get('level', 'P2'),
                status='ready',
                content=json.dumps(case_data),
                task_id=task_id,  # 设置任务ID
                file_id=file_id  # 设置文件ID
            )
            cases.append(case)
            
        return cases
    
    @classmethod
    async def get_case_by_id(
        cls,
        case_id: str,
        db: AsyncSession
    ) -> Optional[TestCase]:
        """根据ID获取用例
        
        Args:
            case_id: 用例ID
            db: 数据库会话
            
        Returns:
            Optional[TestCase]: 用例对象，如果不存在返回None
        """
        try:
            # 查询用例
            result = await db.execute(
                select(TestCase).where(TestCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if case:
                logger.debug(f"获取到用例: {case.id}")
            else:
                logger.warning(f"未找到用例: {case_id}")
                
            return case
            
        except Exception as e:
            logger.error(f"获取用例失败: {str(e)}")
            raise
    
    @staticmethod
    async def list_cases(
        db: AsyncSession,
        project: Optional[str] = None,
        module: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[TestCase], int]:
        """获取测试用例列表
        
        Args:
            db: 数据库会话
            project: 项目名称过滤
            module: 模块名称过滤
            task_id: 任务ID过滤
            page: 页码(从1开始)
            page_size: 每页数量
            
        Returns:
            Tuple[List[TestCase], int]: 用例列表和总数
        """
        try:
            # 构建查询
            query = select(TestCase)
            
            # 添加过滤条件
            if project:
                query = query.where(TestCase.project == project)
            if module:
                query = query.where(TestCase.module == module)
            if task_id:
                query = query.where(TestCase.task_id == task_id)
            
            # 添加排序(按创建时间倒序)
            query = query.order_by(TestCase.created_at.desc())
            
            # 计算分页
            skip = (page - 1) * page_size
            
            # 获取总数
            total = await db.scalar(select(func.count()).select_from(query.subquery()))
            
            # 添加分页
            query = query.offset(skip).limit(page_size)
            
            # 执行查询
            result = await db.execute(query)
            cases = result.scalars().all()
            
            return cases, total
            
        except Exception as e:
            logger.error(f"获取用例列表失败: {str(e)}")
            raise
    
    @classmethod
    async def delete_case(
        cls,
        case_id: str,
        db: AsyncSession
    ) -> bool:
        """删除测试用例
        
        Args:
            case_id: 用例ID
            db: 数据库会话
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取用例信息
            result = await db.execute(
                select(TestCase).where(TestCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if not case:
                raise ValueError("用例不存在")
            
            # 删除用例
            await db.delete(case)
            await db.commit()
            
            logger.info(f"用例删除成功: {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"用例删除失败: {str(e)}")
            raise

    @classmethod
    async def batch_delete_cases(
        cls,
        case_ids: List[str],
        db: AsyncSession
    ) -> Dict[str, bool]:
        """批量删除测试用例
        
        Args:
            case_ids: 用例ID列表
            db: 数据库会话
            
        Returns:
            Dict[str, bool]: 每个用例的删除结果
        """
        results = {}
        for case_id in case_ids:
            try:
                success = await cls.delete_case(case_id, db)
                results[case_id] = success
            except Exception as e:
                logger.error(f"删除用例失败 {case_id}: {str(e)}")
                results[case_id] = False
        return results

    @classmethod
    async def update_case(
        cls,
        case_id: str,
        project: Optional[str] = None,
        module: Optional[str] = None,
        name: Optional[str] = None,
        level: Optional[str] = None,
        status: Optional[str] = None,
        content: Optional[Dict] = None,
        db: AsyncSession = None
    ) -> Optional[TestCase]:
        """更新测试用例信息
        
        Args:
            case_id: 用例ID
            project: 项目名称
            module: 模块名称
            name: 用例名称
            level: 用例等级
            status: 用例状态
            content: 用例内容
            db: 数据库会话
            
        Returns:
            Optional[TestCase]: 更新后的用例信息
        """
        try:
            # 获取用例信息
            result = await db.execute(
                select(TestCase).where(TestCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if not case:
                raise ValueError("用例不存在")
            
            # 更新字段
            if project is not None:
                case.project = project
            if module is not None:
                case.module = module
            if name is not None:
                case.name = name
            if level is not None:
                case.level = level
            if status is not None:
                case.status = status
            if content is not None:
                case.content = json.dumps(content)
            
            # 保存更新
            await db.commit()
            await db.refresh(case)
            
            logger.info(f"用例信息更新成功: {case_id}")
            return case
            
        except Exception as e:
            logger.error(f"用例信息更新失败: {str(e)}")
            raise
    
    @classmethod
    async def _process_generate_cases_task(cls, task_id: str, file_id: str, project_name: str, module_name: Optional[str] = None):
        """处理用例生成任务"""
        try:
            # 更新任务状态为处理中
            TaskManager.update_task(task_id, status="processing", progress=10)
            
            # 获取文件内容
            file_service = FileService()
            file_content = await file_service.get_file_content(file_id)
            if not file_content:
                TaskManager.update_task(
                    task_id,
                    status="failed",
                    error="获取文件内容失败"
                )
                return
            
            TaskManager.update_task(task_id, progress=30)
            
            # 分析需求文档
            chat_manager = ChatManager()
            analysis_result = await chat_manager.analyze_requirement(
                content=file_content.get("content", ""),
                image_paths=file_content.get("image_paths", [])
            )
            
            if not analysis_result:
                TaskManager.update_task(
                    task_id,
                    status="failed",
                    error="需求分析失败"
                )
                return
            
            TaskManager.update_task(task_id, progress=60)
            
            # 生成测试用例
            testcases = await chat_manager.generate_testcases(
                summary=analysis_result
            )
            
            if not testcases:
                TaskManager.update_task(
                    task_id,
                    status="failed",
                    error="用例生成失败"
                )
                return
            
            TaskManager.update_task(task_id, progress=80)
            
            # 生成PlantUML思维导图
            plantuml_code = await chat_manager.export_testcases_to_plantuml(
                testcases,
                "mindmap"
            )
            
            if not plantuml_code:
                TaskManager.update_task(
                    task_id,
                    status="failed",
                    error="生成思维导图失败"
                )
                return
            
            # 保存测试用例
            async with AsyncSessionLocal() as db:
                saved_cases = []
                for case in testcases:
                    case_model = await cls.create_case(
                        project=project_name,
                        module=module_name or case.get("module", "默认模块"),
                        name=case.get("name", ""),
                        level=case.get("level", ""),
                        content=case,
                        task_id=task_id,
                        db=db
                    )
                    if case_model:
                        saved_cases.append(case_model)
            
            if not saved_cases:
                TaskManager.update_task(
                    task_id,
                    status="failed",
                    error="保存用例失败"
                )
                return
            
            # 只更新一次任务状态，包含所有信息
            TaskManager.update_task(
                task_id,
                status="completed",
                progress=100,
                result={
                    "progress": "测试用例生成完成",
                    "cases_count": len(saved_cases),
                    "cases": [
                        {
                            "id": case.id,
                            "project": case.project,
                            "module": case.module,
                            "name": case.name,
                            "level": case.level,
                            "status": case.status,
                            "content": json.loads(case.content)
                        }
                        for case in saved_cases
                    ],
                    "plantuml_code": plantuml_code
                }
            )
            
        except Exception as e:
            logger.error(f"处理用例生成任务失败: {str(e)}")
            TaskManager.update_task(
                task_id,
                status="failed",
                error=str(e)
            )
    