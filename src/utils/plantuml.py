from typing import Optional
import httpx
import base64
import zlib
from src.logger.logger import logger
from src.config.settings import settings

async def render_plantuml(plantuml_code: str, output_format: str = "svg") -> Optional[bytes]:
    """渲染 PlantUML 图表
    
    Args:
        plantuml_code: PlantUML 代码
        output_format: 输出格式 ("svg" 或 "png")
        
    Returns:
        Optional[bytes]: 渲染后的图片数据
    """
    try:
        # PlantUML 在线服务器地址
        server_url = settings.plantuml.PLANTUML_SERVER_URL
        if not server_url:
            server_url = "http://www.plantuml.com/plantuml"
        
        # 编码 PlantUML 代码
        zlibbed = zlib.compress(plantuml_code.encode("utf-8"))
        compressed = base64.b64encode(zlibbed)
        encoded = compressed.decode("ascii")
        
        # 构建请求 URL
        url = f"{server_url}/{output_format}/{encoded}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return response.content
            
    except Exception as e:
        logger.error(f"渲染 PlantUML 图表失败: {str(e)}")
        return None 