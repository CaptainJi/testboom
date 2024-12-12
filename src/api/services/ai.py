from typing import List, Dict, Any, Optional
from loguru import logger
from src.ai_core.chat_manager import ChatManager

class AIService:
    """AI服务"""
    
    def __init__(self):
        """初始化AI服务"""
        self.chat_manager = ChatManager()
    
    @classmethod
    async def analyze_image(
        cls,
        image_path: str,
        module_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """分析图片生成用例"""
        try:
            # 构建提示词
            module_info = f"模块名称: {module_name}\n" if module_name else ""
            message = f"""
            {module_info}
            请分析图片并生成测试用例，要求：
            1. 覆盖所有关键功能点
            2. 包含正向和异常场景
            3. 步骤要详细且可执行
            4. 返回格式为JSON数组
            """
            
            # 使用ChatManager处理图片分析
            chat_manager = ChatManager()
            response = chat_manager.chat_with_images(message, [image_path])
            if not response:
                raise ValueError("AI分析失败")
            
            # 解析响应
            try:
                cases = chat_manager.ai.parse_response(response)
                if not isinstance(cases, list):
                    cases = [cases]
                return cases
            except Exception as e:
                logger.error(f"AI响应解析失败: {str(e)}")
                raise ValueError("AI响应格式错误")
                
        except Exception as e:
            logger.error(f"AI分析图片失败: {str(e)}")
            raise
    
    @classmethod
    async def analyze_images(
        cls,
        image_paths: List[str],
        module_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """分析多张图片生成用例"""
        all_cases = []
        for image_path in image_paths:
            cases = await cls.analyze_image(image_path, module_name)
            all_cases.extend(cases)
        return all_cases 