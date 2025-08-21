# API测试文件说明

本目录包含了AI文档生成器API的完整测试工具集合。

## 📁 文件说明

### 1. `test_curl_commands.txt`
- **用途**: 包含所有API端点的详细curl命令
- **特点**: 每个命令都有详细注释和示例
- **使用**: 可以复制粘贴单个命令进行测试

### 2. `run_api_tests.sh`
- **用途**: 完整的API测试脚本
- **特点**: 
  - 自动检查服务状态
  - 测试所有端点
  - 显示详细的响应信息
  - 包含状态码和耗时统计
- **使用**: `./run_api_tests.sh`

### 3. `quick_test.sh`
- **用途**: 快速API测试脚本
- **特点**: 
  - 快速验证核心功能
  - 使用jq格式化输出
  - 适合日常开发测试
- **使用**: `./quick_test.sh`

## 🚀 使用方法

### 前置条件
1. 确保服务已启动: `./start_dev_server.sh`
2. 确保服务运行在: `http://localhost:8000`

### 快速开始
```bash
# 进入测试目录
cd test_case

# 运行快速测试
./quick_test.sh

# 运行完整测试
./run_api_tests.sh
```

## 📋 API端点列表

### 1. 健康检查
- **端点**: `GET /api/v1/health`
- **用途**: 检查API服务状态
- **响应**: `{"status": "healthy", "message": "API服务运行正常"}`

### 2. AI文本编辑 (流式响应)
- **端点**: `POST /api/v1/actions/edit`
- **用途**: 文本润色、扩写、总结、续写、自定义编辑
- **特点**: 返回Server-Sent Events格式
- **支持操作**: `polish`, `expand`, `summarize`, `continue_writing`, `custom`

### 3. 大纲生成
- **端点**: `POST /api/v1/jobs/outline`
- **用途**: 根据用户指令生成文档大纲
- **返回**: `taskId`, `sessionId`, `redisStreamKey`
- **特点**: 支持在线搜索和上下文文件

### 4. 文档生成 (从大纲对象)
- **端点**: `POST /api/v1/jobs/document`
- **用途**: 根据结构化大纲对象生成文档
- **输入**: 完整的大纲对象结构

### 5. 文档生成 (从大纲JSON字符串)
- **端点**: `POST /api/v1/jobs/document-from-outline`
- **用途**: 根据大纲JSON字符串生成文档
- **输入**: 大纲的JSON序列化字符串

### 6. 模拟文档生成
- **端点**: `POST /api/v1/jobs/document-from-outline/mock`
- **用途**: 模拟文档生成过程，立即开始发布Redis流事件
- **特点**: 用于测试Redis流事件监听

### 7. 根端点
- **端点**: `GET /`
- **用途**: 基础服务信息
- **响应**: 服务名称、状态、版本信息

## 🔧 响应格式

所有API响应都使用驼峰命名法 (camelCase):

```json
{
  "taskId": "1754537230406003516",
  "sessionId": "123456789",
  "redisStreamKey": "1754537230406003516",
  "status": "accepted",
  "message": "任务已提交"
}
```

## 📡 Redis流事件

大纲生成和文档生成任务会发布事件到Redis流:

- **流名称**: 使用`taskId`作为流名称
- **事件格式**: JSON格式，包含`redisId`, `eventType`, `taskType`等字段
- **监听工具**: 使用`test_mock_endpoint.py`监听流事件

## 🛠️ 故障排除

### 常见问题

1. **服务未启动**
   ```bash
   # 启动服务
   ./start_dev_server.sh
   ```

2. **端口被占用**
   ```bash
   # 检查端口
   lsof -i :8000
   # 停止服务
   ./stop_dev_server.sh
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis配置
   ./config_redis.sh
   ```

4. **权限问题**
   ```bash
   # 添加执行权限
   chmod +x *.sh
   ```

## 📝 测试建议

1. **开发阶段**: 使用`quick_test.sh`进行快速验证
2. **集成测试**: 使用`run_api_tests.sh`进行完整测试
3. **流事件测试**: 使用`test_mock_endpoint.py`监听Redis事件
4. **手动测试**: 使用`test_curl_commands.txt`中的单个命令

## 🔗 相关文件

- `../start_dev_server.sh`: 启动开发服务器
- `../test_mock_endpoint.py`: Redis流事件监听测试
- `../service/api/endpoints.py`: API端点定义
- `../service/src/doc_agent/schemas.py`: 数据模型定义
