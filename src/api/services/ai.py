from typing import List, Dict, Any, Optional
from loguru import logger
import zhipuai
import json
import os
from PIL import Image
import base64

class AIService:
    """AI服务"""
    
    @classmethod
    async def analyze_image(
        cls,
        image_path: str,
        module_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """分析图片生成用例"""
        try:
            # 读取图片并转换为base64
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode()
            
            # 构建提示词
            system_prompt = """你是一个专业的测试工程师，擅长分析产品原型图并生成测试用例。
            请仔细分析图片内容，生成完整的测试用例。
            测试用例应包含：用例名称、用例等级(P0/P1/P2)、前置条件、测试步骤、预期结果。
            请以JSON格式返回结果。"""
            
            module_info = f"模块名称: {module_name}\n" if module_name else ""
            human_prompt = f"""
            {module_info}
            请分析图片并生成测试用例，要求：
            1. 覆盖所有关键功能点
            2. 包含正向和异常场景
            3. 步骤要详细且可执行
            4. 返回格式为JSON数组
            """
            
            # 调用智谱AI
            response = zhipuai.model_api.invoke(
                model="glm-4v",
                prompt=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": human_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                top_p=0.95,
            )
            
            # 检查响应状态
            if response['code'] != 200:
                logger.error(f"智谱AI调用失败: {response['msg']}")
                raise ValueError(f"智谱AI调用失败: {response['msg']}")
            
            # 解析响应
            try:
                cases = json.loads(response['data']['choices'][0]['content'])
                if not isinstance(cases, list):
                    cases = [cases]
                return cases
            except (json.JSONDecodeError, KeyError) as e:
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