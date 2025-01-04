# TestBoom 项目结构说明

## 目录结构

```
testboom/
├── src/                    # 源代码目录
│   ├── ai_core/           # AI核心模块
│   │   ├── chat_manager.py     # AI对话管理器
│   │   ├── prompt_template.py  # 提示词模板管理
│   │   └── zhipu_api.py       # 智谱AI API封装
│   │
│   ├── api/               # API接口模块
│   │   ├── models/        # 数据模型定义
│   │   │   ├── base.py         # 基础模型
│   │   │   ├── case.py         # 测试用例模型
│   │   │   └── task.py         # 任务模型
│   │   │
│   │   ├── routers/      # 路由处理
│   │   │   └── case.py         # 测试用例路由
│   │   │
│   │   └── services/     # 业务逻辑服务
│   │       ├── case.py         # 测试用例服务
│   │       ├── file.py         # 文件处理服务
│   │       └── task.py         # 任务管理服务
│   │
│   ├── config/           # 配置模块
│   │   └── settings.py        # 系统配置
│   │
│   ├── db/               # 数据库模块
│   │   ├── base.py           # 数据库基类
│   │   ├── models.py         # 数据库模型
│   │   ├── session.py        # 会话管理
│   │   └── __init__.py       # 数据库初始化
│   │
│   ├── doc_analyzer/     # 文档分析模块
│   │   └── doc_analyzer.py   # 文档分析器
│   │
│   ├── logger/           # 日志模块
│   │   └── logger.py         # 日志配置
│   │
│   ├── storage/          # 存储模块
│   │   └── storage.py        # 存储服务
│   │
│   ├── utils/            # 工具模块
│   │   ├── common.py         # 通用工具
│   │   ├── decorators.py     # 装饰器
│   │   └── plantuml.py       # PlantUML工具
│   │
│   └── main.py          # 应用入口
│
├── tests/               # 测试目录
│   ├── test_ai_core/        # AI核心测试
│   ├── test_api/           # API测试
│   └── test_utils/         # 工具测试
│
├── resources/           # 资源文件
│   └── prompts/            # 提示词模板
│
├── output/             # 输出目录
│   ├── excel/             # Excel文件
│   └── plantuml/          # PlantUML图片
│
└── docs/               # 文档目录
```

## 核心模块说明

### 1. AI核心模块 (src/ai_core/)
- `chat_manager.py`: AI对话管理器，负责与AI模型的交互和对话上下文管理
- `prompt_template.py`: 提示词模板管理，维护和加载各类提示词模板
- `zhipu_api.py`: 智谱AI API的封装，处理API调用和响应

### 2. API接口模块 (src/api/)
#### 模型定义 (models/)
- `base.py`: 基础数据模型，定义通用模型结构
- `case.py`: 测试用例模型，定义用例数据结构
- `task.py`: 任务模型，定义任务数据结构

#### 路由处理 (routers/)
- `case.py`: 测试用例相关的路由处理，包括用例的CRUD操作

#### 业务服务 (services/)
- `case.py`: 测试用例服务，处理用例相关的业务逻辑
- `file.py`: 文件处理服务，处理文件上传和管理
- `task.py`: 任务管理服务，处理异步任务和状态管理

### 3. 数据库模块 (src/db/)
- `base.py`: 数据库基类，定义ORM基础类
- `models.py`: 数据库模型定义
- `session.py`: 数据库会话管理
- `__init__.py`: 数据库初始化和配置

### 4. 文档分析模块 (src/doc_analyzer/)
- `doc_analyzer.py`: 文档分析器，处理需求文档和生成测试用例

### 5. 存储模块 (src/storage/)
- `storage.py`: 存储服务，处理文件存储和管理

### 6. 工具模块 (src/utils/)
- `common.py`: 通用工具函数
- `decorators.py`: 装饰器定义
- `plantuml.py`: PlantUML相关工具

## 配置文件说明

### 1. 环境配置
- `.env`: 环境变量配置文件
- `.env.example`: 环境变量示例文件

### 2. 项目文档
- `README.md`: 项目说明文档
- `PLANTUML_API_GUIDE.md`: PlantUML API使用指南
- `PLANTUML_GUIDE.md`: PlantUML使用指南

### 3. 依赖管理
- `requirements.txt`: Python依赖包列表

## 资源目录说明

### 1. 提示词模板 (resources/prompts/)
- `templates.json`: 提示词模板定义
- `templates.json.bak`: 提示词模板备份

### 2. 输出目录 (output/)
- `excel/`: Excel文件输出目录
- `plantuml/`: PlantUML图片输出目录

## 测试目录说明

### 1. 测试模块 (tests/)
- `test_ai_core/`: AI核心模块测试
- `test_api/`: API接口测试
- `test_utils/`: 工具模块测试

## 文件命名规范

1. Python文件：
   - 小写字母
   - 下划线分隔
   - 有意义的名称
   - 避免test_前缀（测试文件除外）

2. 测试文件：
   - test_开头
   - 对应源文件名
   - 清晰表达测试内容

3. 资源文件：
   - 类型前缀
   - 版本信息
   - 日期信息
   - 清晰分类 