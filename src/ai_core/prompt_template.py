from typing import Dict, Any, Optional
from string import Template
from pathlib import Path
import json
from ..logger.logger import logger
from ..utils.common import safe_file_read, safe_file_write

class PromptTemplate:
    """Prompt模板管理"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """初始化Prompt模板管理器
        
        Args:
            template_dir: 模板文件目录,默认为resources/prompts
        """
        self.template_dir = Path(template_dir) if template_dir else Path("resources/prompts")
        self.templates: Dict[str, str] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板文件"""
        try:
            # 确保模板目录存在
            self.template_dir.mkdir(parents=True, exist_ok=True)
            
            # 加载所有json文件
            for file_path in self.template_dir.glob("*.json"):
                content = safe_file_read(file_path)
                if content:
                    self.templates = json.loads(content)
                    logger.info(f"加载模板: {', '.join(self.templates.keys())}")
        except Exception as e:
            logger.error(f"加载模板文件失败: {str(e)}")
    
    def get_template(self, name: str) -> Optional[Template]:
        """获取指定名称的模板
        
        Args:
            name: 模板名称
            
        Returns:
            Optional[Template]: 模板对象
        """
        template_str = self.templates.get(name)
        if template_str:
            return Template(template_str)
        return None
    
    def render(self, template_name: str, **kwargs) -> Optional[str]:
        """渲染指定模板
        
        Args:
            template_name: 模板名称
            **kwargs: 模板参数
            
        Returns:
            Optional[str]: 渲染后的文本
        """
        template = self.get_template(template_name)
        if template:
            try:
                return template.safe_substitute(**kwargs)
            except Exception as e:
                logger.error(f"渲染模板失败: {str(e)}")
                return None
        return None
    
    def add_template(self, name: str, template: str) -> bool:
        """添加新模板
        
        Args:
            name: 模板名称
            template: 模板内容
            
        Returns:
            bool: 是否添加成功
        """
        try:
            self.templates[name] = template
            return True
        except Exception as e:
            logger.error(f"添加模板失败: {str(e)}")
            return False
    
    def save_templates(self) -> bool:
        """保存所有模板到文件"""
        try:
            # 确保模板目录存在
            self.template_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存到文件
            return safe_file_write(
                self.template_dir / "templates.json",
                json.dumps(self.templates, ensure_ascii=False, indent=2)
            )
        except Exception as e:
            logger.error(f"保存模板失败: {str(e)}")
            return False
