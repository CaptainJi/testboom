from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from loguru import logger
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

class TaskManager:
    """任务管理器"""
    
    # 存储任务信息
    _tasks: Dict[str, Dict[str, Any]] = {}
    # 线程池
    _executor = ThreadPoolExecutor(max_workers=3)
    # 后台任务事件循环
    _background_loop = None
    # 后台线程
    _background_thread = None
    
    @classmethod
    def _ensure_background_loop(cls):
        """确保后台事件循环存在并运行"""
        if cls._background_loop is None:
            def run_background_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                cls._background_loop = loop
                loop.run_forever()
            
            # 创建并启动后台线程
            cls._background_thread = threading.Thread(
                target=run_background_loop,
                daemon=True
            )
            cls._background_thread.start()
            
            # 等待事件循环创建完成
            while cls._background_loop is None:
                pass
    
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
            # 确保result是列表类型
            if isinstance(result, list):
                # 记录调试信息
                logger.debug(f"更新任务结果: {result}")
                
                # 确保每个case的id是字符串类型
                for case in result:
                    if isinstance(case, dict):
                        # 确保case_id存在且为字符串
                        if 'id' in case:
                            case['id'] = str(case['id'])
                        # 确保content中的id也是字符串
                        if 'content' in case and isinstance(case['content'], dict):
                            if 'id' in case['content']:
                                case['content']['id'] = str(case['content']['id'])
                        logger.debug(f"处理后的用例: {case}")
                        
            task['result'] = result
        if error is not None:
            task['error'] = error
            
        task['updated_at'] = datetime.utcnow()
    
    @classmethod
    def run_background_task(
        cls,
        task_id: str,
        coro,
        *args,
        **kwargs
    ) -> None:
        """运行后台任务，不使用await调用此方法"""
        cls._ensure_background_loop()
        
        async def _run_task():
            try:
                # 更新任务状态为运行中
                cls.update_task(task_id, status='running', progress=0)
                
                # 在线程池中执行协程
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
        
        # 在后台事件循环中运行任务
        asyncio.run_coroutine_threadsafe(_run_task(), cls._background_loop)