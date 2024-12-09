# TestBoom

TestBoom是一个AI驱动的自动化测试项目,专注于通过AI技术提升测试效率。

## 主要功能

1. AI分析产品PRD/需求文档图片,自动生成Excel格式的测试用例
2. AI阅读和理解已有的测试用例
3. AI执行测试用例并输出测试结果

## 快速开始

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件,配置必要的环境变量
```

3. 运行测试
```bash
pytest -v -s
```

## 项目结构

```
testboom/
├── src/                 # 源代码
│   ├── doc_analyzer/    # 文档分析模块
│   ├── case_processor/  # 用例处理模块
│   ├── case_executor/   # 用例执行模块
│   ├── ai_core/        # AI核心模块
│   ├── config/         # 配置模块
│   ├── logger/         # 日志模块
│   └── utils/          # 通用工具
├── tests/              # 测试目录
├── docs/              # 文档目录
├── examples/          # 示例文件
└── resources/         # 资源文件
```

## 环���要求

- Python 3.10+
- 智谱AI API密钥
