# TestBoom API 接口文档

## 用例管理接口

### 1. 更新测试用例

#### 接口描述
更新指定测试用例的信息，支持全量更新和部分字段更新。每次更新都会记录修改历史。

#### 请求信息
- 请求方法: PUT
- 请求路径: `/api/v1/cases/{case_id}`
- Content-Type: application/json

#### 请求参数

##### 路径参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| case_id | string | 是 | 测试用例ID |

##### 请求体参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| project | string | 否 | 项目名称 |
| module | string | 否 | 模块名称 |
| name | string | 否 | 用例名称 |
| level | string | 否 | 用例等级(P0/P1/P2/P3) |
| status | string | 否 | 用例状态(draft/ready/testing/passed/failed/blocked) |
| content | object | 否 | 用例内容 |
| remark | string | 否 | 修改说明 |

#### 响应信息

##### 成功响应
```json
{
    "code": 200,
    "message": "用例信息更新成功",
    "data": {
        "case_id": "xxx",
        "project": "项目名称",
        "module": "模块名称",
        "name": "用例名称",
        "level": "P1",
        "status": "testing",
        "content": {
            "steps": ["步骤1", "步骤2"],
            "expected": "预期结果"
        },
        "history": [
            {
                "field": "status",
                "old_value": "ready",
                "new_value": "testing",
                "remark": "开始测试",
                "created_at": "2024-01-04T10:00:00"
            }
        ]
    }
}
```

##### 错误响应
```json
{
    "code": 400/404/500,
    "message": "错误信息",
    "data": null
}
```

#### 错误码说明
| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误，如用例等级或状态值无效 |
| 404 | 用例不存在 |
| 500 | 服务器内部错误 |

### 2. 获取测试用例详情

#### 接口描述
获取指定测试用例的详细信息，包括修改历史记录。

#### 请求信息
- 请求方法: GET
- 请求路径: `/api/v1/cases/{case_id}`

#### 请求参数

##### 路径参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| case_id | string | 是 | 测试用例ID |

#### 响应信息

##### 成功响应
```json
{
    "code": 200,
    "message": "获取用例信息成功",
    "data": {
        "case_id": "xxx",
        "project": "项目名称",
        "module": "模块名称",
        "name": "用例名称",
        "level": "P1",
        "status": "testing",
        "content": {
            "steps": ["步骤1", "步骤2"],
            "expected": "预期结果"
        },
        "history": [
            {
                "field": "status",
                "old_value": "ready",
                "new_value": "testing",
                "remark": "开始测试",
                "created_at": "2024-01-04T10:00:00"
            }
        ]
    }
}
```

### 3. 获取测试用例列表

#### 接口描述
获取测试用例列表，支持分页和筛选。

#### 请求信息
- 请求方法: GET
- 请求路径: `/api/v1/cases`

#### 请求参数

##### 查询参数
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| project | string | 否 | 项目名称 |
| module | string | 否 | 模块名称 |
| level | string | 否 | 用例等级 |
| status | string | 否 | 用例状态 |
| page | integer | 否 | 页码，默认1 |
| size | integer | 否 | 每页数量，默认20 |

#### 响应信息

##### 成功响应
```json
{
    "code": 200,
    "message": "获取用例列表成功",
    "data": {
        "total": 100,
        "items": [
            {
                "case_id": "xxx",
                "project": "项目名称",
                "module": "模块名称",
                "name": "用例名称",
                "level": "P1",
                "status": "testing",
                "content": {
                    "steps": ["步骤1", "步骤2"],
                    "expected": "预期结果"
                }
            }
        ]
    }
}
```

## 注意事项

1. 用例等级说明：
   - P0: 核心功能，每次迭代必测
   - P1: 重要功能，建议每次迭代测试
   - P2: 一般功能，可根据时间安排测试
   - P3: 边缘功能，可选测试

2. 用例状态说明：
   - draft: 草稿
   - ready: 就绪
   - testing: 测试中
   - passed: 通过
   - failed: 失败
   - blocked: 阻塞

3. 修改历史：
   - 每次更新用例时，只记录实际发生变化的字段
   - 修改历史按时间倒序排列
   - 建议每次修改都填写修改说明

4. 接口调用建议：
   - 建议使用 TypeScript 定义接口类型
   - 实现错误重试机制
   - 添加请求超时处理
   - 实现数据缓存机制

## 前端开发建议

1. 用例编辑页面：
   - 实现表单验证
   - 添加必填字段提示
   - 支持取消编辑
   - 显示修改历史记录
   - 添加保存确认提示

2. 用例列表页面：
   - 实现分页控件
   - 添加筛选条件
   - 支持批量操作
   - 显示用例状态标签
   - 添加刷新功能

3. 数据处理：
   - 实现数据本地缓存
   - 添加乐观更新
   - 处理并发请求
   - 实现数据预加载

4. UI/UX建议：
   - 使用加载状态提示
   - 添加操作成功/失败提示
   - 实现表单自动保存
   - 支持键盘快捷操作
   - 添加数据导出功能 