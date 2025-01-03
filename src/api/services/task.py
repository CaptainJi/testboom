from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime
import asyncio
from loguru import logger
import uuid
import threading
from threading import Event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from ..models.task import Task
from src.db.session import AsyncSessionLocal

class TaskManager:
    """任务管理器"""
    
    # 将_tasks改为类变量
    _tasks = {}
    _background_thread = None
    _background_loop = None
    _background_event = None
    
    @classmethod
    def _ensure_background_loop(cls):
        """确保后台事件循环在运行"""
        if cls._background_thread is None or not cls._background_thread.is_alive():
            cls._background_event = threading.Event()
            cls._background_loop = asyncio.new_event_loop()
            
            def run_background_loop():
                asyncio.set_event_loop(cls._background_loop)
                loop = asyncio.get_event_loop()
                loop.run_forever()
            
            cls._background_thread = threading.Thread(
                target=run_background_loop,
                daemon=True,
                name="TaskManager-Background"
            )
            cls._background_thread.start()
    
    @classmethod
    def run_background_task(cls, task_id: str, coro: Callable, *args, **kwargs):
        """在后台运行任务
        
        Args:
            task_id: 任务ID
            coro: 协程函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        cls._ensure_background_loop()
        
        async def wrapped_task():
            try:
                await cls._run_task(task_id, coro, *args, **kwargs)
            except Exception as e:
                logger.error(f"任务执行失败[{task_id}]: {str(e)}")
                await cls.update_task(
                    task_id,
                    status='failed',
                    error=str(e)
                )
                raise
        
        asyncio.run_coroutine_threadsafe(wrapped_task(), cls._background_loop)
    
    @classmethod
    async def create_task(cls, task_type: str, params: dict = None) -> str:
        """创建任务
        
        Args:
            task_type: 任务类型
            params: 任务参数
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        logger.info(f"创建任务 - TaskID: {task_id}, Type: {task_type}, Params: {params}")
        
        # 创建任务记录
        async with AsyncSessionLocal() as session:
            task = Task(
                id=task_id,
                type=task_type,
                status='pending',
                progress=0,
                result={
                    'progress': '任务已创建，等待处理...',
                    'project_name': params.get('project_name', ''),
                    'module_name': params.get('module_name', '')
                },
                project_name=params.get('project_name', ''),
                module_name=params.get('module_name', '')
            )
            session.add(task)
            await session.commit()
            
            # 刷新以获取完整的任务对象
            await session.refresh(task)
            
        logger.info(f"任务创建完成 - TaskID: {task_id}")
        return task_id
    
    @classmethod
    async def get_task_info(cls, task_id: str) -> Optional[Dict]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict]: 任务信息
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                return {
                    'id': task.id,
                    'type': task.type,
                    'status': task.status,
                    'progress': task.progress,
                    'result': task.result,
                    'error': task.error,
                    'project_name': task.project_name,
                    'module_name': task.module_name,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at
                }
            return None
    
    @classmethod
    async def update_task(
        cls,
        task_id: str,
        status: str = None,
        progress: int = None,
        result: dict = None,
        error: str = None
    ):
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 任务状态
            progress: 任务进度
            result: 任务结果
            error: 错误信息
        """
        logger.info(f"开始更新任务 - TaskID: {task_id}, Status: {status}, Progress: {progress}, Result: {result}, Error: {error}")
        
        async with AsyncSessionLocal() as session:
            result_query = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result_query.scalar_one_or_none()
            
            if task:
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if result is not None:
                    # 保留原有的project_name和module_name
                    if isinstance(task.result, dict):
                        new_result = task.result.copy()
                    else:
                        new_result = {}
                    new_result.update(result)
                    task.result = new_result
                if error is not None:
                    task.error = error
                    
                task.updated_at = datetime.now()
                await session.commit()
                await session.refresh(task)
    
    @classmethod
    async def list_tasks(
        cls,
        task_type: str = None,
        status: str = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Dict], int]:
        """获取任务列表
        
        Args:
            task_type: 任务类型
            status: 任务状态
            page: 页码
            page_size: 每页数量
            
        Returns:
            Tuple[List[Dict], int]: 任务列表和总数
        """
        async with AsyncSessionLocal() as session:
            query = select(Task)
            
            if task_type:
                query = query.where(Task.type == task_type)
            if status:
                query = query.where(Task.status == status)
                
            # 按更新时间倒序排序
            query = query.order_by(Task.updated_at.desc())
            
            # 分页
            result = await session.execute(query.limit(page_size).offset((page - 1) * page_size))
            tasks = result.scalars().all()
            
            # 获取总数
            count_query = select(func.count()).select_from(Task)
            if task_type:
                count_query = count_query.where(Task.type == task_type)
            if status:
                count_query = count_query.where(Task.status == status)
                
            result = await session.execute(count_query)
            total = result.scalar()
            
            return [
                {
                    'id': task.id,
                    'type': task.type,
                    'status': task.status,
                    'progress': task.progress,
                    'result': task.result,
                    'error': task.error,
                    'project_name': task.project_name,
                    'module_name': task.module_name,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at
                }
                for task in tasks
            ], total
    
    @classmethod
    async def _run_task(cls, task_id: str, coro: Callable, *args, **kwargs):
        """运行任务
        
        Args:
            task_id: 任务ID
            coro: 协程函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        try:
            # 更新任务状态为运行中
            await cls.update_task(
                task_id,
                status='running',
                progress=0,
                result={'progress': '任务开始执行...'}
            )
            
            # 执行任务
            result = await coro(*args, **kwargs)
            
            # 更新任务状态为完成
            await cls.update_task(
                task_id,
                status='completed',
                progress=100,
                result={'progress': '任务执行完成'}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"任务执行失败[{task_id}]: {str(e)}")
            # 更新任务状态为失败
            await cls.update_task(
                task_id,
                status='failed',
                error=str(e)
            )
            raise
    
    @classmethod
    async def delete_task(
        cls,
        task_id: str,
        delete_cases: bool = False,
        db: AsyncSession = None
    ) -> bool:
        """删除任务
        
        Args:
            task_id: 任务ID
            delete_cases: 是否同时删除关联的用例
            db: 数据库会话（用于删除关联用例）
            
        Returns:
            bool: 是否删除成功
        """
        try:
            async with AsyncSessionLocal() as session:
                # 查询任务
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if not task:
                    return False
                    
                # 如果需要删除关联的用例
                if delete_cases and db:
                    from ..services.case import CaseService
                    await CaseService.delete_cases_by_task_id(task_id, db)
                
                # 删除任务
                await session.delete(task)
                await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"删除任务失败[{task_id}]: {str(e)}")
            return False