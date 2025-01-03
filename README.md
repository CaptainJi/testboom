# TestBoom

TestBoom是一个AI驱动的自动化测试平台，专注于通过AI技术提升测试效率。

## 项目进展

### 已完成功能

#### 1. 核心功能
- [x] AI分析产品PRD/需求文档图片
- [x] 自动生成Excel格式的测试用例
- [x] 测试用例的增删改查管理
- [x] 任务管理系统（创建、查询、删除）
- [x] PlantUML思维导图生成
- [x] 异步任务处理机制

#### 2. 文件处理
- [x] 文件上传与管理
- [x] ZIP文件解压处理
- [x] 图片文件处理
- [x] Excel导出功能

#### 3. 系统功能
- [x] 异步任务队列
- [x] 状态追踪和进度更新
- [x] 错误处理和日志记录
- [x] 数据持久化

### 待开发功能
- [ ] 用例执行功能
- [ ] 测试报告生成
- [ ] 用户认证和权限管理
- [ ] 项目管理功能
- [ ] 团队协作功能

## 技术栈

- 后端框架：FastAPI
- 数据库：SQLite + SQLAlchemy
- AI能力：智谱AI API
- 异步处理：Python asyncio
- 文件存储：本地文件系统
- 文档格式：Excel、PlantUML

## 项目结构

```
testboom/
├── src/                 # 源代码
│   ├── ai_core/         # AI核心模块
│   ├── api/             # API接口
│   │   ├── models/      # 数据模型
│   │   ├── routers/     # 路由处理
│   │   └── services/    # 业务逻辑
│   ├── db/              # 数据库相关
│   └── utils/           # 工具函数
├── tests/               # 测试代码
├── docs/                # 文档
└── output/              # 输出文件
```

## 主要功能说明

### 1. 测试用例生成
- 支持上传PRD/需求文档图片
- AI分析需求内容
- 自动生成结构化测试用例
- 支持Excel格式导出

### 2. 任务管理
- 异步任务处理
- 实时进度追踪
- 支持任务取消和删除
- 关联资源的清理

### 3. 可视化展示
- PlantUML思维导图生成
- 支持SVG/PNG格式
- 异步渲染处理
- 文件下载功能

## 开发规范

### 代码规范
- 遵循PEP 8规范
- 类型注解
- 详细的文档字符串
- 统一的错误处理

### API规范
- RESTful设计
- 统一的响应格式
- 详细的接口文档
- 错误码规范

### 数据库规范
- 模型关系清晰
- 字段类型合理
- 索引优化
- 事务处理

## 部署说明

### 环境要求
- Python 3.10+
- 操作系统：Linux/Windows/MacOS
- 内存：4GB+
- 存储：10GB+

### 安装步骤
1. 克隆项目
```bash
git clone https://github.com/your-repo/testboom.git
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，配置必要的环境变量
```

4. 运行项目
```bash
python run.py
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 版本历史

### v0.1.0 (2024-01-03)
- 完成基础框架搭建
- 实现核心AI功能
- 完成任务管理系统
- 实现文件处理功能
- 添加PlantUML支持

## 联系方式

- 项目负责人：[Your Name]
- 邮箱：[Your Email]
- 项目地址：[Repository URL]

## 许可证

MIT License
