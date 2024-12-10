from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import time
from typing import Callable
from fastapi.routing import APIRoute
from starlette.responses import Response

class LoggerMiddleware(BaseHTTPMiddleware):
    """日志中间件,用于记录请求和响应信息"""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        logger.info(f"Request started: {request.method} {request.url}")
        
        # 获取请求体
        try:
            body = await request.body()
            if body:
                logger.debug(f"Request body: {body.decode()}")
        except Exception as e:
            logger.warning(f"Failed to read request body: {str(e)}")
            
        # 处理请求
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"Request failed: {str(exc)}")
            raise exc
            
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 记录响应信息
        logger.info(
            f"Request completed: {request.method} {request.url} "
            f"- Status: {response.status_code} "
            f"- Process time: {process_time:.3f}s"
        )
        
        return response

class LoggerRoute(APIRoute):
    """带有日志记录功能的路由类"""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # 记录请求开始时间
            start_time = time.time()
            
            # 记录请求信息
            logger.info(f"API Route: {request.method} {request.url}")
            
            # 处理请求
            try:
                response = await original_route_handler(request)
            except Exception as exc:
                logger.error(f"API Route failed: {str(exc)}")
                raise exc
                
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"API Route completed: {request.method} {request.url} "
                f"- Status: {getattr(response, 'status_code', '?')} "
                f"- Process time: {process_time:.3f}s"
            )
            
            return response
            
        return custom_route_handler 