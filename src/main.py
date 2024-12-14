from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from loguru import logger
from src.api.middlewares.logger import LoggerMiddleware
from src.api.models.base import ResponseModel
from src.api.routers import case, file
from src.db import init_db
import os

# 创建FastAPI应用实例
app = FastAPI(
    title="TestBoom API",
    description="AI驱动的自动化测试平台API",
    version="1.0.0",
    docs_url=None,  # 禁用默认的docs路由
    redoc_url=None  # 禁用默认的redoc路由
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(LoggerMiddleware)

# 注册路由
app.include_router(case.router)
app.include_router(file.router)

# 自定义OpenAPI文档路由
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return ResponseModel(data={"status": "ok"})

# 异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    logger.error(f"HTTP error occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseModel(
            code=exc.status_code,
            message=exc.detail,
            data=None
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    logger.error(f"Unexpected error occurred: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ResponseModel(
            code=500,
            message="Internal server error",
            data=None
        ).model_dump()
    )

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的事件处理"""
    # 初始化数据库
    await init_db()
    logger.info("Database initialized")

if __name__ == "__main__":
    # 标记为主进程
    os.environ["RELOAD_PROCESS"] = "0"
    
    import uvicorn
    # 配置日志
    logger.add(
        "logs/api.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO"
    )
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000) 