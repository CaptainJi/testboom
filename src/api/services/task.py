from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
from loguru import logger
import uuid
import threading
from threading import Event

class TaskManager:
    """任务管理器
    
    负责管理异步任务的生命周期，包括：
    1. 任务创建和状态管理
    2. 后台任务执行
    3. 进度更新
    4. 结果处理
    """
    
    # 存储任务信息
    _tasks: Dict[str, Dict[str, Any]] = {}
    # 后台任务事件循环
    _background_loop = None
    # 后台线程
    _background_thread = None
    # 事件循环就绪事件
    _loop_ready = Event()
    
    @classmethod
    def _ensure_background_loop(cls) -> None:
        """确保后台事件循环存在并运行
        
        使用Event机制确保事件循环创建完成
        """
        if cls._background_loop is None:
            def run_background_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                cls._background_loop = loop
                cls._loop_ready.set()  # 通知事件循环已就绪
                loop.run_forever()
            
            # 创建并启动后台线程
            cls._background_thread = threading.Thread(
                target=run_background_loop,
                daemon=True,
                name="TaskManager-Background"
            )
            cls._background_thread.start()
            
            # 等待事件循环就绪
            cls._loop_ready.wait()
    
    @classmethod
    def create_task(cls, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        """创建任务
        
        Args:
            task_type: 任务类型
            params: 任务参数
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        cls._tasks[task_id] = {
            'id': task_id,
            'type': task_type,
            'status': 'pending',
            'progress': 0,
            'result': {
                'progress': '任务已创建，等待处理...',
                **(params or {})  # 合并任务参数
            },
            'error': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return task_id
    
    @classmethod
    def get_task_info(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务信息
        """
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
        task = cls._tasks.get(task_id)
        if not task:
            logger.warning(f"尝试更新不存在的任务: {task_id}")
            return
            
        # 原子更新任务状态
        updates = {}
        if status:
            updates['status'] = status
        if progress is not None:
            updates['progress'] = progress
        if error is not None:
            updates['error'] = error
        if result is not None:
            logger.info(f"更新任务结果，任务ID: {task_id}, 结果: {result}")
            # 处理结果数据
            if isinstance(result, list):
                processed_result = []
                for item in result:
                    if isinstance(item, dict):
                        # 确保ID字段为字符串
                        item_copy = item.copy()
                        if 'id' in item_copy:
                            item_copy['id'] = str(item_copy['id'])
                        if 'content' in item_copy and isinstance(item_copy['content'], dict):
                            if 'id' in item_copy['content']:
                                item_copy['content']['id'] = str(item_copy['content']['id'])
                        processed_result.append(item_copy)
                    else:
                        processed_result.append(item)
                updates['result'] = processed_result
            elif isinstance(result, dict):
                # 如果是字典，保留原有的项目和模块信息
                current_result = task.get('result', {})
                if isinstance(current_result, dict):
                    project_name = current_result.get('project_name', '')
                    module_name = current_result.get('module_name', '')
                    if not result.get('project_name'):
                        result['project_name'] = project_name
                    if not result.get('module_name'):
                        result['module_name'] = module_name
                updates['result'] = result
                logger.info(f"更新后的结果: {result}")
            else:
                updates['result'] = result
        
        # 更新时间戳
        updates['updated_at'] = datetime.utcnow()
        
        # 应用更新
        task.update(updates)
    
    @classmethod
    def list_tasks(
        cls,
        type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取任务列表
        
        Args:
            type: 任务类型过滤
            status: 任务状态过滤
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        try:
            # 获取所有任务
            tasks = list(cls._tasks.values())
            
            # 应用过滤条件
            if type:
                tasks = [t for t in tasks if t.get('type') == type]
            if status:
                tasks = [t for t in tasks if t.get('status') == status]
            
            # 按更新时间倒序排序
            tasks.sort(key=lambda x: x.get('updated_at', datetime.min), reverse=True)
            
            # 应用分页
            start = min(skip, len(tasks))
            end = min(start + limit, len(tasks))
            
            return tasks[start:end]
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return []
    
    @classmethod
    def run_background_task(
        cls,
        task_id: str,
        coro,
        *args,
        **kwargs
    ) -> None:
        """运行后台任务
        
        Args:
            task_id: 任务ID
            coro: 异步协程
            args: 位置参数
            kwargs: 关键字参数
        """
        cls._ensure_background_loop()
        
        async def _run_task():
            try:
                # 获取当前任务信息
                task = cls._tasks.get(task_id)
                if not task:
                    logger.error(f"任务不存在: {task_id}")
                    return
                
                # 保留原有的 result 内容
                current_result = task.get('result', {})
                if isinstance(current_result, dict):
                    current_result['progress'] = '任务开始执行...'
                else:
                    current_result = {'progress': '任务开始执行...'}
                
                # 更新任务状态为运行中，保留原有的 result 内容
                cls.update_task(
                    task_id,
                    status='running',
                    progress=0,
                    result=current_result
                )
                
                # 执行任务
                result = await coro(*args, **kwargs)
                
                # 更新任务状态为完成
                if isinstance(result, dict):
                    # 如果结果是字典，合并原有的项目和模块信息
                    result = {
                        **result,
                        'project_name': current_result.get('project_name', ''),
                        'module_name': current_result.get('module_name', '')
                    }
                
                cls.update_task(
                    task_id,
                    status='completed',
                    progress=100,
                    result=result
                )
                
            except Exception as e:
                logger.error(f"任务执行失败[{task_id}]: {str(e)}")
                cls.update_task(
                    task_id,
                    status='failed',
                    error=str(e)
                )
                logger.exception(e)
        
        # 在后台事件循环中运行任务
        asyncio.run_coroutine_threadsafe(_run_task(), cls._background_loop)