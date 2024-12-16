from typing import Dict, Optional
from pathlib import Path
import json
from ..logger.logger import logger
from ..utils.common import safe_file_read, safe_file_write
from jinja2 import Template, Environment, BaseLoader

class PromptTemplate:
    """Prompt模板管理"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """初始化Prompt模板管理器"""
        self.template_dir = Path(template_dir or "resources/prompts")
        self.templates = {}
        self.env = Environment(loader=BaseLoader())
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载所有模板文件"""
        try:
            self.template_dir.mkdir(parents=True, exist_ok=True)
            content = safe_file_read(self.template_dir / "templates.json")
            if content:
                self.templates = json.loads(content)
        except Exception as e:
            logger.error(f"加载模板文件失败: {str(e)}")
    
    def get_template(self, name: str) -> Optional[Template]:
        """获取指定名称的模板"""
        template_str = self.templates.get(name)
        return self.env.from_string(template_str) if template_str else None
    
    def render(self, template_name: str, **kwargs) -> Optional[str]:
        """渲染指定模板"""
        template = self.get_template(template_name)
        try:
            return template.render(**kwargs) if template else None
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            return None
    
    def add_template(self, name: str, template: str) -> bool:
        """添加新模板"""
        try:
            self.templates[name] = template
            return True
        except Exception as e:
            logger.error(f"添加模板失败: {str(e)}")
            return False
    
    def save_templates(self) -> bool:
        """保存所有模板到文件"""
        try:
            self.template_dir.mkdir(parents=True, exist_ok=True)
            return safe_file_write(
                self.template_dir / "templates.json",
                json.dumps(self.templates, ensure_ascii=False, indent=2)
            )
        except Exception as e:
            logger.error(f"保存模板失败: {str(e)}")
            return False
