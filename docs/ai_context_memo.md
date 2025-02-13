# AI 上下文备忘录

## 1. 项目当前状态

### 1.1 已实现的核心功能
1. AI 分析模块
   - 基于智谱AI的文档分析能力
   - 测试用例生成功能
   - PlantUML 导出支持

2. 数据管理
   - 文件上传和处理
   - 测试用例的CRUD操作
   - 修改历史记录

3. 系统架构
   - FastAPI 后端框架
   - SQLAlchemy 异步ORM
   - MinIO 对象存储
   - 日志和错误处理

### 1.2 项目结构
```
testboom/
├── src/                # 源代码目录
│   ├── ai_core/        # AI 核心功能
│   │   ├── chat_manager.py   # 对话管理
│   │   ├── zhipu_api.py     # 智谱AI接口
│   │   └── prompt_template.py # 提示词模板
│   ├── api/            # API 接口
│   │   ├── models/     # 数据模型
│   │   ├── routers/    # 路由处理
│   │   ├── services/   # 业务服务
│   │   └── middlewares/ # 中间件
│   ├── config/         # 配置管理
│   │   ├── settings.py # 配置定义
│   │   └── test_settings.py # 配置测试
│   ├── db/             # 数据库模块
│   │   ├── base.py     # 基础模型
│   │   ├── models.py   # 数据模型
│   │   └── session.py  # 会话管理
│   ├── doc_analyzer/   # 文档分析
│   │   ├── doc_analyzer.py # 文档分析器
│   │   └── file_processor.py # 文件处理
│   ├── logger/         # 日志模块
│   │   └── logger.py   # 日志配置
│   ├── storage/        # 存储模块
│   │   └── storage.py  # MinIO存储
│   └── utils/          # 工具模块
│       ├── common.py   # 通用工具
│       └── decorators.py # 装饰器
├── docs/               # 文档目录
├── resources/          # 资源文件
│   └── prompts/        # AI提示词模板
├── static/             # 静态资源
├── storage/            # 文件存储
├── data/               # 数据文件
├── logs/               # 日志文件
└── temp/               # 临时文件

配置文件：
- .env：环境配置
- .cursorrules：项目规范
- requirements.txt：依赖管理
- run.py：应用入口
```

### 1.3 核心模块说明
1. AI核心模块
   - chat_manager.py：对话管理，包括会话控制和响应处理
   - zhipu_api.py：智谱AI接口封装，支持对话和视觉模型
   - prompt_template.py：提示词模板管理

2. API模块
   - models/：数据模型定义，包括请求和响应模型
   - routers/：路由处理，包括用例、文件和任务管理
   - services/：业务逻辑实现
   - middlewares/：中间件，如日志记录

3. 配置模块
   - settings.py：配置加载和验证
   - test_settings.py：配置测试工具

4. 数据库模块
   - base.py：SQLAlchemy基础模型
   - models.py：数据模型定义
   - session.py：数据库会话管理

5. 文档分析模块
   - doc_analyzer.py：文档分析和用例生成
   - file_processor.py：文件处理和格式转换

6. 存储模块
   - storage.py：MinIO对象存储服务

7. 工具模块
   - common.py：通用工具函数
   - decorators.py：装饰器，如异常处理和重试

### 1.4 核心依赖
1. AI 相关
   - zhipuai>=2.1.5：智谱AI SDK
   - langchain>=0.0.350：LangChain框架
   - langchain-community>=0.0.10：社区扩展
   - langchain-core>=0.1.4：核心功能

2. Web框架
   - fastapi>=0.104.1：FastAPI框架
   - uvicorn>=0.24.0：ASGI服务器
   - python-multipart>=0.0.6：文件上传
   - httpx>=0.27.0：HTTP客户端

3. 数据存储
   - sqlalchemy>=2.0.23：ORM框架
   - alembic>=1.12.1：数据库迁移
   - aiosqlite>=0.19.0：异步SQLite
   - minio>=7.1.10：对象存储

4. 工具库
   - loguru>=0.7.2：日志管理
   - openpyxl>=3.1.2：Excel处理
   - pandas>=2.1.4：数据处理
   - jinja2>=3.1.2：模板引擎

### 1.4 数据模型关系
- TestCase -> TestCaseHistory (一对多)
- File -> TestCase (一对多)
- Task -> TestCase (一对多)

## 2. 待开发的测试执行引擎

### 2.1 核心组件设计
1. 执行引擎 (engine/)
   ```python
   class TestEngine:
       async def execute_test(self, test_case: TestCase):
           # 1. 准备执行环境
           # 2. 解析测试用例
           # 3. 执行测试步骤
           # 4. 收集执行结果
           pass
   ```

2. 页面对象模型 (page_objects/)
   ```python
   class BasePage:
       def __init__(self, page: Page):
           self.page = page
           
       async def wait_for_ready(self):
           # 等待页面就绪
           pass
   ```

3. 爬虫模块 (crawler/)
   ```python
   class DOMCollector:
       async def collect(self, page: Page):
           # 收集页面DOM结构
           # 分析可交互元素
           # 记录事件监听器
           pass
   ```

### 2.2 AI 分析提示词设计

1. DOM结构分析
   ```
   系统：你是一个专业的Web测试分析专家
   任务：分析页面DOM结构，识别关键功能组件
   输入：页面的DOM树结构
   输出：
   {
     "components": [...],
     "interactions": [...],
     "validations": [...]
   }
   ```

2. 测试步骤生成
   ```
   系统：你是一个专业的测试用例设计专家
   任务：基于页面模型生成测试步骤
   输入：页面模型和测试意图
   输出：详细的测试步骤序列
   ```

### 2.3 图数据库模型设计

1. 节点类型
   ```cypher
   CREATE (:Page {
     url: string,
     title: string,
     type: string
   })

   CREATE (:Component {
     selector: string,
     type: string,
     actions: list
   })

   CREATE (:TestCase {
     id: string,
     name: string,
     level: string
   })
   ```

2. 关系类型
   ```cypher
   // 页面包含组件
   (page:Page)-[:CONTAINS]->(component:Component)
   
   // 组件间的交互
   (component:Component)-[:TRIGGERS]->(component:Component)
   
   // 测试用例涉及的组件
   (testcase:TestCase)-[:USES]->(component:Component)
   ```

## 3. 开发注意事项

### 3.1 AI 交互设计
1. 保持提示词的一致性和可复用性
2. 结构化的输入和输出格式
3. 错误处理和重试机制
4. 结果验证和质量控制

### 3.2 性能优化
1. 使用连接池管理数据库连接
2. 实现缓存机制减少AI调用
3. 异步处理提高并发能力
4. 资源使用监控和限制

### 3.3 扩展性考虑
1. 插件化的测试工具适配器
2. 可配置的测试策略
3. 自定义的报告模板
4. 灵活的数据导入导出

## 4. 关键算法和策略

### 4.1 页面分析算法
```python
async def analyze_page(dom_tree: Dict):
    # 1. 提取页面结构
    structure = extract_structure(dom_tree)
    
    # 2. 识别功能组件
    components = identify_components(structure)
    
    # 3. 分析交互关系
    interactions = analyze_interactions(components)
    
    # 4. 生成页面模型
    return build_page_model(structure, components, interactions)
```

### 4.2 测试生成策略
```python
async def generate_test_steps(page_model: Dict, test_intent: str):
    # 1. 分析测试意图
    intent = analyze_intent(test_intent)
    
    # 2. 匹配所需组件
    components = match_components(page_model, intent)
    
    # 3. 生成操作序列
    steps = generate_steps(components, intent)
    
    # 4. 添加验证点
    return add_validations(steps, intent)
```

## 5. 代码规范和最佳实践

### 5.1 异步编程规范
```python
# 推荐的异步方法结构
async def process_task(self, task_id: str):
    try:
        # 1. 获取任务信息
        task = await self.get_task(task_id)
        
        # 2. 更新任务状态
        await self.update_status(task_id, "processing")
        
        # 3. 执行具体操作
        result = await self.execute(task)
        
        # 4. 处理执行结果
        await self.handle_result(task_id, result)
        
    except Exception as e:
        await self.handle_error(task_id, e)
```

### 5.2 错误处理模式
```python
# 装饰器方式的错误处理
def handle_exceptions(default_return=None):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} failed: {str(e)}")
                return default_return
        return wrapper
    return decorator
```

## 6. 测试用例模板

### 6.1 基本结构
```json
{
  "id": "TC_001",
  "name": "用户登录测试",
  "level": "P0",
  "steps": [
    {
      "action": "navigate",
      "target": "login_page",
      "params": {"url": "/login"}
    },
    {
      "action": "input",
      "target": "username_field",
      "value": "${username}"
    }
  ],
  "validations": [
    {
      "type": "element_visible",
      "target": "welcome_message",
      "expected": true
    }
  ]
}
```

### 6.2 执行上下文
```python
class TestContext:
    def __init__(self):
        self.variables = {}  # 变量存储
        self.screenshots = []  # 截图记录
        self.logs = []  # 执行日志
        self.artifacts = {}  # 测试产物
```

## 7. 后续开发建议

1. 优先级排序
   - 基础执行引擎
   - 页面对象框架
   - 爬虫功能
   - AI 分析集成

2. 技术验证
   - Playwright 性能测试
   - Neo4j 数据模型验证
   - AI 分析准确性评估
   - 并发执行压力测试

3. 文档完善
   - API 文档更新
   - 架构设计说明
   - 开发指南
   - 使用教程 

## 8. 资源文件组织

### 8.1 AI提示词模板 (resources/prompts/)
1. 需求分析相关
   - requirement_analysis：分析单个需求文档
   - requirement_summary：汇总多个需求分析结果
   - requirement_batch_summary：批量分析原型设计图

2. 测试用例相关
   - testcase_generation：基于需求生成测试用例
   - testcase_understanding：分析测试用例的覆盖范围

3. UI/UX分析
   - image_analysis：分析界面设计图
   ```json
   {
     "需求背景": {
       "项目背景": "",
       "业务目标": [],
       "主要痛点": [],
       "解决方案": []
     },
     "整体功能架构": {
       "系统模块": [],
       "功能结构": [],
       "核心功能": [],
       "辅助功能": []
     }
     // ... 其他字段
   }
   ```

### 8.2 静态资源 (static/)
- swagger-ui-bundle.js：Swagger UI 脚本
- swagger-ui.css：Swagger UI 样式
- 用于API文档的自动生成和展示

### 8.3 存储目录 (storage/)
- files/：上传文件的存储位置
- 使用MinIO对象存储服务
- 支持文件的上传、下载和管理

## 9. 开发规范

### 9.1 目录结构规范
```
testboom/
├── src/                # 源代码目录
├── resources/          # 资源文件
│   └── prompts/        # AI提示词模板
├── static/             # 静态资源
├── storage/            # 文件存储
├── data/               # 数据文件
├── logs/               # 日志文件
└── temp/               # 临时文件
```

### 9.2 资源管理规范
1. AI提示词
   - 统一存放在 resources/prompts/templates.json
   - 使用JSON格式，便于维护和扩展
   - 支持变量插值，使用 {{ variable }} 语法

2. 文件存储
   - 上传文件统一存储在 storage/files/
   - 使用MinIO进行对象存储
   - 支持文件元数据管理

3. 静态资源
   - API文档相关资源存放在 static/
   - 使用Swagger UI进行API文档展示
   - 支持API文档的自动生成 

## 10. 配置管理

### 10.1 环境配置 (.env)
1. AI配置
   ```
   AI_ZHIPU_API_KEY=your_api_key_here
   AI_ZHIPU_MODEL_CHAT=glm-4-flash
   AI_ZHIPU_MODEL_VISION=glm-4v-flash
   AI_MAX_TOKENS=6000
   AI_MAX_IMAGE_SIZE=10485760  # 10MB
   AI_RETRY_COUNT=3
   AI_RETRY_DELAY=5
   AI_RETRY_BACKOFF=2.0
   ```

2. 日志配置
   ```
   LOG_LEVEL=DEBUG
   LOG_FILE=logs/app.log
   LOG_FORMAT="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
   LOG_ROTATION=500 MB
   LOG_RETENTION=10 days
   ```

3. 数据库配置
   ```
   DB_URL=sqlite:///testboom.db
   DB_ECHO=false
   DB_POOL_SIZE=5
   DB_MAX_OVERFLOW=10
   ```

4. 存储配置
   ```
   STORAGE_ENABLED=false
   STORAGE_PROVIDER=minio
   STORAGE_ENDPOINT=your_endpoint
   STORAGE_ACCESS_KEY=your_key
   STORAGE_SECRET_KEY=your_secret
   STORAGE_BUCKET_NAME=your_bucket
   STORAGE_PUBLIC_URL=your_url
   ```

### 10.2 项目进度 (.cursorrules)
1. 已完成功能
   - AI分析PRD/需求文档图片
   - 自动生成Excel格式测试用例
   - 测试用例管理(CRUD)
   - 测试用例修改历史记录
   - 任务管理系统
   - 文件上传和处理
   - PlantUML导出支持

2. 待开发功能
   - 用例执行引擎
   - 测试报告生成
   - 批量用例处理
   - 用例模板管理
   - 用例依赖关系管理
   - 性能优化
   - 缓存系统
   - 监控告警
   - 权限管理
   - 数据备份

3. 版本规划
   - v0.1.0：基础框架和核心功能
   - v0.2.0：执行引擎和报告生成
   - v0.3.0：高级功能和系统优化

### 10.3 API测试 (test_api.sh)
```bash
# 健康检查
curl -X GET http://localhost:8000/health

# 用例生成
curl -X POST http://localhost:8000/api/v1/cases/generate \
  -H "Content-Type: application/json" \
  -d '{"doc_path": "test.docx", "module_name": "登录模块"}'

# 获取用例
curl -X GET http://localhost:8000/api/v1/cases/CASE001

# 用例列表
curl -X GET "http://localhost:8000/api/v1/cases?module=登录模块&level=P0"
``` 

## 11. 数据目录说明

### 11.1 数据存储 (data/)
- app.db：应用数据库文件
- files/：文件存储目录
- temp/：临时文件目录

### 11.2 输出文件 (output/)
1. 测试用例文件
   - 格式：testcases_{timestamp}.xlsx
   - 包含测试用例的详细信息
   - 按时间戳命名，便于追踪

2. PlantUML图表
   - 存放在 plantuml/ 子目录
   - 生成的流程图和时序图

### 11.3 日志文件 (logs/)
- app.log：应用主日志
  - 记录系统运行状态
  - 错误和异常信息
  - 关键操作日志

- api.log：API访问日志
  - 记录API调用情况
  - 请求和响应信息
  - 性能监控数据 