import json
from typing import List, Optional, Dict, Any
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
    
    @classmethod
    async def list_cases(
        cls,
        db: AsyncSession,
        project: Optional[str] = None,
        module: Optional[str] = None,
        level: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> List[TestCase]:
        """获取用例列表
        
        Args:
            db: 数据库会话
            project: 项目名称
            module: 模块名称
            level: 用例等级
            task_id: 任务ID
            
        Returns:
            List[TestCase]: 用例列表
        """
        try:
            # 构建基础查询
            query = select(TestCase)
            
            # 添加查询条件
            conditions = []
            
            if project:
                # 记录查询条件
                logger.info(f"查询项目: {project}")
                conditions.append(TestCase.project == project)
                
            if module:
                logger.info(f"查询模块: {module}")
                conditions.append(TestCase.module == module)
                
            if level:
                logger.info(f"查询等级: {level}")
                conditions.append(TestCase.level == level)
                
            if task_id:
                logger.info(f"查询任务: {task_id}")
                conditions.append(TestCase.task_id == task_id)
                
            # 组合所有条件
            if conditions:
                query = query.where(*conditions)
                
            # 执行查询
            result = await db.execute(query)
            cases = result.scalars().all()
            
            # 记录查询结果
            logger.info(f"查询到 {len(cases)} 条用例")
            for case in cases:
                logger.debug(f"用例内容: {case.content}")
                
            return cases
            
        except Exception as e:
            logger.error(f"查询用例失败: {str(e)}")
            return []
    