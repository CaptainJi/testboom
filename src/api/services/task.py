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
    # 存储项目信息
    _project_info: Dict[str, Dict[str, str]] = {}
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
        """创建任务"""
        task_id = str(uuid.uuid4())
        logger.info(f"创建任务 - TaskID: {task_id}, Type: {task_type}, Params: {params}")
        
        # 保存项目信息
        project_name = params.get('project_name', '') if params else ''
        module_name = params.get('module_name', '') if params else ''
        cls._project_info[task_id] = {
            'project_name': project_name,
            'module_name': module_name
        }
        logger.info(f"保存项目信息 - TaskID: {task_id}, Project: {project_name}, Module: {module_name}")
        
        # 初始化结果，先处理其他参数
        result = {}
        if params:
            result.update({k: v for k, v in params.items() if k not in ['project_name', 'module_name']})
        
        # 设置基本信息，确保不会被覆盖
        result.update({
            'progress': '任务已创建，等待处理...',
            'project_name': project_name,
            'module_name': module_name
        })
        logger.info(f"初始化任务结果 - TaskID: {task_id}, Result: {result}")
        
        cls._tasks[task_id] = {
            'id': task_id,
            'type': task_type,
            'status': 'pending',
            'progress': 0,
            'result': result,
            'error': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        logger.info(f"任务创建完成 - TaskID: {task_id}, Task: {cls._tasks[task_id]}")
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
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Optional[Dict]:
        """更新任务状态"""
        try:
            logger.info(f"开始更新任务 - TaskID: {task_id}, Status: {status}, Progress: {progress}, Result: {result}, Error: {error}")
            
            if task_id not in cls._tasks:
                logger.error(f"任务不存在 - TaskID: {task_id}")
                return None
            
            task = cls._tasks[task_id]
            logger.info(f"当前任务状态 - Task: {task}")
            
            if status:
                task['status'] = status
            if progress is not None:
                task['progress'] = progress
            if error is not None:
                task['error'] = error
            
            # 更新结果
            if result:
                logger.info(f"更新任务结果，任务ID: {task_id}, 结果: {result}")
                
                # 获取保存的项目信息
                project_info = cls._project_info.get(task_id, {})
                project_name = project_info.get('project_name', '')
                module_name = project_info.get('module_name', '')
                logger.info(f"获取保存的项目信息 - TaskID: {task_id}, Project: {project_name}, Module: {module_name}")
                
                # 初始化新结果，使用保存的项目信息
                new_result = {
                    'project_name': project_name,
                    'module_name': module_name
                }
                logger.info(f"初始化新结果 - TaskID: {task_id}, New Result: {new_result}")
                
                # 合并其他字段
                for key, value in result.items():
                    if key not in ['project_name', 'module_name']:
                        new_result[key] = value
                logger.info(f"合并新字段后 - TaskID: {task_id}, Updated Result: {new_result}")
                
                logger.info(f"最终结果 - TaskID: {task_id}, Final Result: {new_result}")
                task['result'] = new_result
            
            # 更新时间戳
            task['updated_at'] = datetime.utcnow()
            
            # 应用更新
            cls._tasks[task_id] = task
            logger.info(f"任务更新完成 - TaskID: {task_id}, Updated Task: {task}")
            
            return task
            
        except Exception as e:
            logger.error(f"更新任务失败: {str(e)}")
            return None
    
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
                
                # 从 _project_info 获取项目信息
                project_info = cls._project_info.get(task_id, {})
                project_name = project_info.get('project_name', '')
                module_name = project_info.get('module_name', '')
                logger.info(f"获取保存的项目信息 - TaskID: {task_id}, Project: {project_name}, Module: {module_name}")
                
                # 更新任务状态为运行中
                cls.update_task(
                    task_id,
                    status='running',
                    progress=0,
                    result={
                        'project_name': project_name,
                        'module_name': module_name,
                        'progress': '任务开始执行...'
                    }
                )
                
                # 执行任务
                result = await coro(*args, **kwargs)
                
                # 更新任务状态为完成
                if isinstance(result, dict):
                    # 确保保留项目和模块信息
                    final_result = {
                        'project_name': project_name,
                        'module_name': module_name
                    }
                    # 合并其他字段
                    for key, value in result.items():
                        if key not in ['project_name', 'module_name']:
                            final_result[key] = value
                else:
                    final_result = result
                
                cls.update_task(
                    task_id,
                    status='completed',
                    progress=100,
                    result=final_result
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