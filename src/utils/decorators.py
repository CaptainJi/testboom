from functools import wraps
import time
import traceback
from typing import Any, Callable, Optional, TypeVar, ParamSpec
from src.logger.logger import logger

P = ParamSpec("P")
R = TypeVar("R")

def handle_exceptions(
    default_return: Any = None,
    log_level: str = "ERROR"
) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]:
    """异常处理装饰器
    
    Args:
        default_return: 发生异常时的返回值
        log_level: 日志级别
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[P, R]) -> Callable[P, Optional[R]]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[R]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取异常信息
                exc_info = {
                    "函数名": func.__name__,
                    "异常类型": type(e).__name__,
                    "异常信息": str(e),
                    "堆栈信息": traceback.format_exc()
                }
                
                # 记录异常
                logger.log(
                    log_level,
                    "函数执行异常:\n{}\n{}\n{}\n{}\n",
                    f"函数名: {exc_info['函数名']}",
                    f"异常类型: {exc_info['异常类型']}",
                    f"异常信息: {exc_info['异常信息']}",
                    f"堆栈信息:\n{exc_info['堆栈信息']}"
                )
                
                return default_return
        return wrapper
    return decorator

def log_function_call(level: str = "DEBUG") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """函数调用日志装饰器
    
    Args:
        level: 日志级别
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # 记录开始时间
            start_time = time.time()
            
            # 记录函数开始
            logger.log(level, "开始执行函数: {}", func.__name__)
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 计算执行时间
                execution_time = time.time() - start_time
                
                # 记录函数完成
                logger.log(level, "函数 {} 执行完成, 耗时: {:.3f}秒", func.__name__, execution_time)
                
                return result
            except Exception as e:
                # 计算执行时间
                execution_time = time.time() - start_time
                
                # 记录异常
                logger.log(
                    "ERROR",
                    "函数 {} 执行异常:\n耗时: {:.3f}秒\n异常信息: {}\n",
                    func.__name__,
                    execution_time,
                    str(e)
                )
                
                # 重新抛出异常
                raise
        return wrapper
    return decorator

def retry(
    max_retries: int = 3,
    delay: int = 1,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间(秒)
        backoff: 延迟时间的增长倍数
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            retry_count = 0
            current_delay = delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        logger.error(
                            "函数 {} 重试 {} 次后仍然失败:\n{}",
                            func.__name__,
                            max_retries,
                            str(e)
                        )
                        raise
                    
                    logger.warning(
                        "函数 {} 执行失败，{}/{} 次重试，等待 {} 秒:\n{}",
                        func.__name__,
                        retry_count,
                        max_retries,
                        current_delay,
                        str(e)
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator 