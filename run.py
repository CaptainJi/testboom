import sys
from pathlib import Path

# 添加项目根目录到Python路径
root_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(root_dir))

import uvicorn
from src.main import app

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",  # 使用模块路径
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式下启用热重载
    ) 