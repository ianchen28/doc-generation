# AI文档生成器 API 使用指南

## 🚀 快速开始

### 1. 启动服务

首先确保安装了所有依赖：

```bash
cd service
pip install -r requirements.txt
```

启动Redis服务：
```bash
redis-server
```

启动API服务：
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 健康检查

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health
```

## 📋 完整的大纲交互流程

### 第一步：创建上下文（可选）

如果有相关文档需要参考，可以先创建上下文：

```bash
curl -X POST "http://localhost:8000/api/v1/contexts" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {
        "file_id": "doc-001",
        "file_name": "参考文档.pdf",
        "storage_url": "s3://bucket/reference.pdf"
      }
    ]
  }'
```

响应：
```json
{
  "context_id": "ctx-abc123",
  "status": "PENDING"
}
```

### 第二步：创建作业

创建文档生成作业：

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "context_id": "ctx-abc123",
    "task_prompt": "写一份关于机器学习基础知识的教程"
  }'
```

响应：
```json
{
  "job_id": "job-xyz789",
  "status": "CREATED",
  "created_at": "2025-07-14T10:30:00Z"
}
```

### 第三步：生成大纲

触发大纲生成：

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/job-xyz789/outline"
```

响应：
```json
{
  "job_id": "job-xyz789",
  "outline_status": "GENERATING"
}
```

### 第四步：获取大纲

等待生成完成后，获取大纲：

```bash
curl "http://localhost:8000/api/v1/jobs/job-xyz789/outline"
```

响应：
```json
{
  "job_id": "job-xyz789",
  "outline_status": "READY",
  "outline": {
    "title": "关于'写一份关于机器学习基础知识的教程'的文档",
    "nodes": [
      {
        "id": "node_1",
        "title": "概述与背景",
        "content_summary": "介绍写一份关于机器学习基础知识的教程的基本概念和重要性",
        "children": []
      },
      {
        "id": "node_2",
        "title": "核心内容分析",
        "content_summary": "深入分析写一份关于机器学习基础知识的教程的关键要素",
        "children": []
      },
      {
        "id": "node_3",
        "title": "应用与实践",
        "content_summary": "探讨写一份关于机器学习基础知识的教程的实际应用场景",
        "children": []
      }
    ]
  }
}
```

### 第五步：更新大纲并开始最终生成

用户可以修改大纲，然后提交：

```bash
curl -X PUT "http://localhost:8000/api/v1/jobs/job-xyz789/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "outline": {
      "title": "机器学习基础教程（修订版）",
      "nodes": [
        {
          "id": "intro",
          "title": "机器学习导论",
          "content_summary": "介绍机器学习的定义、历史和应用",
          "children": []
        },
        {
          "id": "algorithms",
          "title": "核心算法详解",
          "content_summary": "详细讲解主要的机器学习算法",
          "children": []
        },
        {
          "id": "practice",
          "title": "实战案例分析",
          "content_summary": "通过实际案例展示机器学习应用",
          "children": []
        }
      ]
    }
  }'
```

响应：
```json
{
  "job_id": "job-xyz789",
  "message": "大纲更新成功，最终文档生成已开始"
}
```

## 🔧 API端点详解

### 上下文管理

| 端点 | 方法 | 描述 | 状态码 |
|------|------|-----|--------|
| `/api/v1/contexts` | POST | 创建文件上下文 | 202 |

### 作业管理

| 端点 | 方法 | 描述 | 状态码 |
|------|------|-----|--------|
| `/api/v1/jobs` | POST | 创建文档生成作业 | 201 |

### 大纲交互

| 端点 | 方法 | 描述 | 状态码 |
|------|------|-----|--------|
| `/api/v1/jobs/{job_id}/outline` | POST | 触发大纲生成 | 202 |
| `/api/v1/jobs/{job_id}/outline` | GET | 获取生成的大纲 | 200 |
| `/api/v1/jobs/{job_id}/outline` | PUT | 更新大纲并开始最终生成 | 200 |

## 🧪 运行演示

我们提供了一个完整的API演示脚本：

```bash
python examples/api_demo.py
```

该脚本会执行完整的流程：
1. 健康检查
2. 创建上下文
3. 创建作业
4. 生成大纲
5. 等待完成
6. 修改大纲
7. 触发最终生成

## 🧪 运行测试

运行API端点测试：

```bash
cd tests
python test_api_endpoints.py
```

或使用pytest：

```bash
pytest tests/test_api_endpoints.py -v
```

## 📊 状态说明

### 大纲状态
- `PENDING`: 尚未开始生成
- `GENERATING`: 正在生成中
- `READY`: 生成完成
- `FAILED`: 生成失败

### 作业状态
- `CREATED`: 作业已创建
- `processing`: 正在处理中
- `completed`: 处理完成
- `failed`: 处理失败

## ⚠️ 注意事项

1. **Redis服务**: 确保Redis服务正在运行，API依赖Redis存储状态信息
2. **异步操作**: 大纲生成和文档生成都是异步操作，需要轮询状态或使用事件流
3. **错误处理**: 所有端点都包含完整的错误处理和日志记录
4. **并发安全**: 支持多个作业并发处理

## 🚧 开发计划

未来版本将支持：
- [ ] Server-Sent Events (SSE) 事件流
- [ ] 文档内容流式输出
- [ ] 批量作业处理
- [ ] 作业状态查询端点
- [ ] 上下文状态查询端点 