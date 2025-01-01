# TestBoom PlantUML 思维导图接口使用指南

## 重要更新说明 (2024-01-01)

### 分页问题修复
我们发现在生成思维导图时，由于分页限制导致部分测试用例（如 TC_01 到 TC_09）未被包含在结果中。现已修复此问题：

1. 后端修改：
   - 将默认分页大小调整为 1000，确保一次性获取所有测试用例
   - 添加了不分页的处理方式

2. 前端适配：
   - 如果您的测试用例可能超过 10 条，请在请求时添加分页参数
   - 建议使用以下请求方式：
   ```typescript
   const fetchDiagram = useCallback(async () => {
     setLoading(true);
     try {
       // 添加 page_size=1000 确保获取所有用例
       const response = await axios.get(`/api/v1/cases/plantuml/status/${taskId}?page_size=1000`);
       if (response.data.code === 200 && response.data.data) {
         setPlantUmlCode(response.data.data);
         setError('');
       } else {
         throw new Error(response.data.message || '获取思维导图失败');
       }
     } catch (err) {
       const errorMessage = err.response?.data?.detail || err.message;
       setError(errorMessage);
       message.error(errorMessage);
       onError?.(err);
     } finally {
       setLoading(false);
     }
   }, [taskId, onError]);
   ```

## 接口说明

### 1. 获取思维导图数据
```typescript
GET /api/v1/cases/plantuml/status/{task_id}
```

**请求参数：**
- `task_id`: 任务ID，路径参数（从用例生成接口返回的任务ID）

**响应格式：**
```typescript
interface PlantUMLResponse {
  code: number;      // 状态码，200 表示成功
  message: string;   // 响应消息
  data: string;      // PlantUML 代码
}
```

**响应示例：**
```json
{
  "code": 200,
  "message": "获取PlantUML思维导图成功",
  "data": "@startmindmap\n* 测试用例集\n** 首页\n..."
}
```

**注意事项：**
1. 调用时机：
   - 在用例生成完成后调用（任务状态为 completed）
   - 建议先通过任务状态接口确认用例生成完成
2. 错误处理：
   - 404: 任务不存在或未找到相关测试用例
   - 400: 任务未完成
   - 500: 生成思维导图失败

## 渲染实现方案

### 方案一：使用 PlantUML 在线服务器（推荐）

1. 安装依赖：
```bash
npm install plantuml-encoder
```

2. 实现渲染组件：
```typescript
import plantumlEncoder from 'plantuml-encoder';

interface PlantUMLViewerProps {
  code: string;
  width?: string | number;
  height?: string | number;
  className?: string;
}

const PlantUMLViewer: React.FC<PlantUMLViewerProps> = ({ 
  code,
  width = '100%',
  height = 'auto',
  className = ''
}) => {
  // 编码 PlantUML 代码
  const encoded = plantumlEncoder.encode(code);
  
  // 生成图片 URL
  const imageUrl = `http://www.plantuml.com/plantuml/svg/${encoded}`;
  
  return (
    <div className={`plantuml-viewer ${className}`}>
      <img 
        src={imageUrl} 
        alt="PlantUML Diagram"
        style={{ width, height }}
        onError={(e) => {
          console.error('PlantUML 图片加载失败', e);
        }}
      />
    </div>
  );
};
```

3. 完整使用示例：
```typescript
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { message } from 'antd';  // 假设使用 Ant Design

interface TestCaseMindMapProps {
  taskId: string;
  onError?: (error: Error) => void;
}

const TestCaseMindMap: React.FC<TestCaseMindMapProps> = ({ taskId, onError }) => {
  const [plantUmlCode, setPlantUmlCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [retryCount, setRetryCount] = useState(0);

  const fetchDiagram = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/cases/plantuml/status/${taskId}`);
      if (response.data.code === 200 && response.data.data) {
        setPlantUmlCode(response.data.data);
        setError('');
      } else {
        throw new Error(response.data.message || '获取思维导图失败');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      setError(errorMessage);
      message.error(errorMessage);
      onError?.(err);
    } finally {
      setLoading(false);
    }
  }, [taskId, onError]);

  // 自动重试逻辑
  useEffect(() => {
    if (error && error.includes('任务未完成') && retryCount < 3) {
      const timer = setTimeout(() => {
        setRetryCount(prev => prev + 1);
        fetchDiagram();
      }, 3000);  // 3秒后重试
      return () => clearTimeout(timer);
    }
  }, [error, retryCount, fetchDiagram]);

  useEffect(() => {
    fetchDiagram();
  }, [fetchDiagram]);

  const handleRetry = () => {
    setError('');
    setRetryCount(0);
    fetchDiagram();
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Spin tip="正在加载思维导图..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <Alert
          type="error"
          message="加载失败"
          description={error}
          action={
            <Button type="primary" onClick={handleRetry}>
              重试
            </Button>
          }
        />
      </div>
    );
  }

  if (!plantUmlCode) {
    return <Empty description="暂无思维导图数据" />;
  }

  return (
    <PlantUMLViewer 
      code={plantUmlCode}
      className="test-case-mindmap"
    />
  );
};

export default TestCaseMindMap;
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
        dark: false,
        renderAsObject: true,
        includeMetadata: true
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
  min-height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.plantuml-viewer img {
  max-width: 100%;
  height: auto;
  transition: transform 0.3s ease;
}

/* 添加缩放效果 */
.plantuml-viewer img:hover {
  transform: scale(1.02);
}

/* 加载状态样式 */
.loading-container {
  width: 100%;
  height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 错误状态样式 */
.error-container {
  width: 100%;
  padding: 20px;
  border-radius: 8px;
  background: #fff;
}
```

2. 响应式布局：
```css
@media (max-width: 768px) {
  .plantuml-viewer {
    padding: 10px;
  }
  
  .plantuml-viewer img {
    max-width: 100vw;
  }
}

@media print {
  .plantuml-viewer {
    box-shadow: none;
    padding: 0;
  }
}
```

## 最佳实践

### 1. 错误处理和重试机制
```typescript
// 定义重试配置
const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 3000,  // 3秒
  retryableErrors: ['任务未完成', '网络错误']
};

// 实现重试逻辑
const withRetry = async (fn: () => Promise<any>) => {
  let retries = 0;
  while (retries < RETRY_CONFIG.maxRetries) {
    try {
      return await fn();
    } catch (err) {
      if (!RETRY_CONFIG.retryableErrors.some(e => err.message.includes(e))) {
        throw err;
      }
      retries++;
      if (retries === RETRY_CONFIG.maxRetries) {
        throw err;
      }
      await new Promise(resolve => setTimeout(resolve, RETRY_CONFIG.retryDelay));
    }
  }
};
```

### 2. 缓存处理
```typescript
const usePlantUMLCache = () => {
  const [cache] = useState(() => new Map<string, {
    code: string;
    timestamp: number;
  }>());
  
  const CACHE_DURATION = 5 * 60 * 1000;  // 5分钟缓存
  
  const getCachedCode = (taskId: string) => {
    const cached = cache.get(taskId);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return cached.code;
    }
    return null;
  };
  
  const setCachedCode = (taskId: string, code: string) => {
    cache.set(taskId, {
      code,
      timestamp: Date.now()
    });
  };
  
  return { getCachedCode, setCachedCode };
};
```

## 注意事项

### 1. 性能优化
- 使用 `loading` 骨架屏减少页面抖动
- 实现图片懒加载
- 添加合适的缓存策略
- 大图可以考虑分段加载

### 2. 兼容性
- 测试主流浏览器（Chrome、Firefox、Safari、Edge）
- 移动端适配（触摸缩放、横屏优化）
- 提供图片加载失败的降级方案

### 3. 安全性
- 验证 PlantUML 代码来源
- 对用户输入进行转义
- 使用 HTTPS 加载在线服务
- 注意敏感信息保护

## 调试建议

1. 网络请求检查：
```typescript
// 开发环境添加请求拦截器
axios.interceptors.request.use(config => {
  console.log('PlantUML Request:', config);
  return config;
});

axios.interceptors.response.use(response => {
  console.log('PlantUML Response:', response);
  return response;
});
```

2. 图片加载监控：
```typescript
const handleImageLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
  console.log('图片加载成功:', event.currentTarget.src);
};

const handleImageError = (event: React.SyntheticEvent<HTMLImageElement>) => {
  console.error('图片加载失败:', event.currentTarget.src);
  // 可以尝试重新加载或显示错误提示
};
```

如果遇到问题，请检查：
1. 网络请求状态和响应数据
2. PlantUML 代码格式是否正确
3. 图片加载是否成功
4. 浏览器控制台错误信息

需要其他帮助或有任何问题，请随时联系后端团队。 