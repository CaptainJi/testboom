# TestBoom PlantUML 思维导图接口使用指南

## 接口说明

### 1. 获取思维导图数据
```typescript
GET /api/v1/cases/plantuml/status/{task_id}
```

**请求参数：**
- `task_id`: 任务ID，路径参数

**响应格式：**
```typescript
interface PlantUMLResponse {
  code: number;      // 状态码，200 表示成功
  message: string;   // 响应消息
  data: string;      // PlantUML 代码
}
```

**示例响应：**
```json
{
  "code": 200,
  "message": "获取PlantUML思维导图成功",
  "data": "@startmindmap\n* 测试用例集\n** 首页\n..."
}
```

## 渲染实现方案

### 方案一：使用 PlantUML 在线服务器（推荐）

1. 安装依赖：
```bash
npm install plantuml-encoder
```

2. 实现渲染组件：
```typescript
import plantumlEncoder from 'plantuml-encoder';

const PlantUMLViewer: React.FC<{ code: string }> = ({ code }) => {
  // 编码 PlantUML 代码
  const encoded = plantumlEncoder.encode(code);
  
  // 生成图片 URL
  const imageUrl = `http://www.plantuml.com/plantuml/svg/${encoded}`;
  
  return (
    <div className="plantuml-viewer">
      <img src={imageUrl} alt="PlantUML Diagram" />
    </div>
  );
};
```

3. 使用示例：
```typescript
import { useState, useEffect } from 'react';
import axios from 'axios';

const TestCaseMindMap: React.FC<{ taskId: string }> = ({ taskId }) => {
  const [plantUmlCode, setPlantUmlCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchDiagram = async () => {
      setLoading(true);
      try {
        const response = await axios.get(`/api/v1/cases/plantuml/status/${taskId}`);
        if (response.data.code === 200) {
          setPlantUmlCode(response.data.data);
        }
      } catch (err) {
        setError('获取思维导图失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDiagram();
  }, [taskId]);

  if (loading) return <div>加载中...</div>;
  if (error) return <div>{error}</div>;
  if (!plantUmlCode) return <div>暂无数据</div>;

  return <PlantUMLViewer code={plantUmlCode} />;
};
```

### 方案二：使用本地渲染库

如果不想依赖在线服务，可以使用 `react-plantuml` 库在本地渲染：

1. 安装依赖：
```bash
npm install react-plantuml
```

2. 使用示例：
```typescript
import { PlantumlComponent } from 'react-plantuml';

const TestCaseMindMap: React.FC<{ taskId: string }> = ({ taskId }) => {
  // ... 获取数据的代码同上 ...

  return (
    <PlantumlComponent
      uml={plantUmlCode}
      opts={{
        zoom: 1,
        dark: false, // 是否使用暗色主题
      }}
    />
  );
};
```

## 样式建议

1. 容器样式：
```css
.plantuml-viewer {
  width: 100%;
  overflow: auto;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.plantuml-viewer img {
  max-width: 100%;
  height: auto;
}
```

2. 响应式布局：
```css
@media (max-width: 768px) {
  .plantuml-viewer {
    padding: 10px;
  }
}
```

## 最佳实践

### 1. 错误处理
```typescript
const handleRetry = () => {
  setError('');
  fetchDiagram();
};

// 在渲染时
if (error) {
  return (
    <div className="error-container">
      <p>{error}</p>
      <button onClick={handleRetry}>重试</button>
    </div>
  );
}
```

### 2. 加载状态
```typescript
import { Skeleton } from 'antd';  // 使用 Ant Design 的示例

if (loading) {
  return (
    <div className="loading-container">
      <Skeleton active />
    </div>
  );
}
```

### 3. 缓存处理
```typescript
const [cache, setCache] = useState<Map<string, string>>(new Map());

const fetchDiagram = async () => {
  if (cache.has(taskId)) {
    setPlantUmlCode(cache.get(taskId)!);
    return;
  }
  
  // ... 获取数据的代码 ...
  
  setCache(prev => new Map(prev).set(taskId, response.data.data));
};
```

## 注意事项

### 1. 性能优化
- 大型图表可能需要延迟加载
- 考虑实现图表缩放功能
- 添加图表导出功能

### 2. 兼容性
- 确保在主流浏览器中正常工作
- 提供降级方案
- 处理移动设备的显示

### 3. 安全性
- 验证 PlantUML 代码来源
- 避免 XSS 攻击
- 处理敏感信息

## 调试建议

1. 使用浏览器开发工具检查网络请求
2. 确认 PlantUML 代码格式是否正确
3. 检查图片加载是否成功
4. 验证编码/解码过程

如果遇到问题，请检查：
- 网络请求状态
- 响应数据格式
- PlantUML 代码语法
- 渲染组件配置

需要其他帮助或有任何问题，请随时联系后端团队。 