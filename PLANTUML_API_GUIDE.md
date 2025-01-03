# TestBoom 思维导图接口升级说明

## 接口变更 (2024-01-15)

思维导图接口新增按模块筛选功能,现在可以指定一个或多个模块来获取对应的测试用例思维导图。

### 接口说明

```typescript
GET /api/v1/cases/plantuml/status/{task_id}?modules=模块1,模块2,模块3
```

**参数说明:**
- `task_id`: 任务ID (必填,路径参数)
- `modules`: 模块名称列表 (可选,查询参数,多个模块用逗号分隔)

**响应格式:**
```json
{
  "code": 200,
  "message": "获取PlantUML思维导图成功",
  "data": "思维导图PlantUML代码"
}
```

### 使用示例

```typescript
// 获取指定模块的思维导图
const fetchDiagram = async () => {
  const modules = ['读者入馆', '借阅管理'];
  const modulesParam = encodeURIComponent(modules.join(','));
  const url = `/api/v1/cases/plantuml/status/${taskId}?modules=${modulesParam}`;
  
  const response = await axios.get(url);
  if (response.data.code === 200) {
    setPlantUmlCode(response.data.data);
  }
};
```

### 注意事项

1. 中文模块名称需要进行URL编码
2. 不传modules参数时返回所有模块的用例
3. 模块名称大小写敏感
4. 返回404表示任务不存在
5. 返回400表示任务未完成

### 错误码说明

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 404 | 任务不存在 | 检查任务ID是否正确 |
| 400 | 任务未完成 | 等待任务完成后重试 |
| 500 | 生成失败 | 联系后端排查原因 |

如有其他问题,请联系后端开发团队。 