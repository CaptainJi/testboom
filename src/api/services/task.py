from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from loguru import logger
import uuid

class TaskManager:
    """任务管理器"""
    
    # 存储任务信息
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_task(cls, task_type: str) -> str:
        """创建任务"""
        task_id = str(uuid.uuid4())
        cls._tasks[task_id] = {
            'id': task_id,
            'type': task_type,
            'status': 'pending',
            'progress': 0,
            'result': None,
            'error': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return task_id
    
    @classmethod
    def get_task_info(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return cls._tasks.get(task_id)
    
    @classmethod
    def update_task(
        cls,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> None:
        """更新任务状态"""
        if task_id not in cls._tasks:
            return
            
        task = cls._tasks[task_id]
        if status:
            task['status'] = status
        if progress is not None:
            task['progress'] = progress
        if result is not None:
            task['result'] = result
        if error is not None:
            task['error'] = error
            
        task['updated_at'] = datetime.utcnow()
    
    @classmethod
    async def run_background_task(
        cls,
        task_id: str,
        coro,
        *args,
        **kwargs
    ) -> None:
        """运行后台任务"""
        try:
            # 更新任务状态为运行中
            cls.update_task(task_id, status='running', progress=0)
            
            # 执行任务
            result = await coro(*args, **kwargs)
            
            # 更新任务状态为完成
            cls.update_task(
                task_id,
                status='completed',
                progress=100,
                result=result
            )
            
        except Exception as e:
            # 更新任务状态为失败
            logger.error(f"Task {task_id} failed: {str(e)}")
            cls.update_task(
                task_id,
                status='failed',
                error=str(e)
            )
            raise 