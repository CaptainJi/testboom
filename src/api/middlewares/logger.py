from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import time
from typing import Callable
from fastapi.routing import APIRoute
from starlette.responses import Response
import json

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
                content_type = request.headers.get("content-type", "")
                
                # 根据内容类型处理请求体
                if "application/json" in content_type:
                    try:
                        body_text = body.decode('utf-8')
                        body_json = json.loads(body_text)
                        logger.debug(f"Request body (JSON): {json.dumps(body_json, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON request body")
                elif "multipart/form-data" in content_type:
                    logger.debug("Request contains form data (not logged)")
                elif "application/x-www-form-urlencoded" in content_type:
                    try:
                        body_text = body.decode('utf-8')
                        logger.debug(f"Request body (form): {body_text}")
                    except UnicodeDecodeError:
                        logger.warning("Failed to decode form data")
                else:
                    logger.debug(f"Request body type: {content_type} (not logged)")
        except Exception as e:
            logger.warning(f"Failed to process request body: {str(e)}")
            
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