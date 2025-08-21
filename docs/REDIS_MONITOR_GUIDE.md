# Redis 流持续监控工具指南

## 🚀 概述

提供了三个不同版本的Redis流持续监控脚本，支持实时监控Redis Streams直到手动停止。

## 📋 脚本列表

### 1. `simple_redis_monitor.sh` - 简化版Shell脚本
**特点**: 简单易用，基础功能完整
**适用**: 快速监控单个流

### 2. `continuous_redis_monitor.sh` - 完整版Shell脚本  
**特点**: 功能丰富，支持多种选项
**适用**: 需要高级功能的用户

### 3. `redis_stream_monitor.py` - Python版本
**特点**: 功能最强大，支持JSON解析和美化输出
**适用**: 需要详细分析和调试

## 🔧 使用方法

### 简化版Shell脚本

```bash
# 监控默认任务
./simple_redis_monitor.sh

# 监控指定任务
./simple_redis_monitor.sh my_job_123

# 显示帮助
./simple_redis_monitor.sh -h
```

### 完整版Shell脚本

```bash
# 监控默认任务
./continuous_redis_monitor.sh

# 监控指定任务
./continuous_redis_monitor.sh my_job_123

# 监控所有流
./continuous_redis_monitor.sh -a

# 使用美化输出
./continuous_redis_monitor.sh -p my_job_123

# 设置超时和消息数
./continuous_redis_monitor.sh -t 10000 -c 20 my_job_123

# 显示帮助
./continuous_redis_monitor.sh -h
```

### Python版本

```bash
# 监控默认任务
python3 redis_stream_monitor.py

# 监控指定任务
python3 redis_stream_monitor.py my_job_123

# 监控所有流
python3 redis_stream_monitor.py -a

# 使用美化输出
python3 redis_stream_monitor.py -p my_job_123

# 设置超时时间
python3 redis_stream_monitor.py -t 10000 my_job_123

# 自定义Redis连接
python3 redis_stream_monitor.py --host 192.168.1.100 --port 6379 --password mypassword my_job_123

# 显示帮助
python3 redis_stream_monitor.py -h
```

## 📊 功能对比

| 功能 | Shell简化版 | Shell完整版 | Python版 |
|------|-------------|-------------|----------|
| 基础监控 | ✅ | ✅ | ✅ |
| 多流监控 | ❌ | ✅ | ✅ |
| 美化输出 | ❌ | ✅ | ✅ |
| JSON解析 | ❌ | ❌ | ✅ |
| 参数配置 | 基础 | 完整 | 完整 |
| 错误处理 | 基础 | 完整 | 完整 |
| 心跳显示 | ✅ | ✅ | ✅ |
| 优雅停止 | ✅ | ✅ | ✅ |

## 🎯 推荐使用场景

### 使用Shell简化版当：
- 快速测试单个流
- 只需要基础监控功能
- 系统资源有限

### 使用Shell完整版当：
- 需要监控多个流
- 需要自定义超时和消息数
- 需要美化输出

### 使用Python版当：
- 需要详细分析消息内容
- 需要JSON数据解析
- 需要自定义Redis连接参数
- 需要最完整的错误处理

## 🔍 监控示例

### 1. 启动监控
```bash
# 使用Python版本监控指定任务
python3 redis_stream_monitor.py my_job_123
```

### 2. 提交测试任务
```bash
# 在另一个终端提交任务
curl -X POST "http://localhost:8000/api/v1/jobs/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "my_job_123",
    "taskPrompt": "请为我生成一份关于人工智能的详细大纲",
    "isOnline": true,
    "contextFiles": []
  }'
```

### 3. 观察输出
```
🚀 Redis 流持续监控工具
==================================================
服务器: 10.215.149.74:26379
任务ID: my_job_123
流: job_events:my_job_123
超时: 5000ms
输出格式: 美化

🔍 检查Redis连接...
✅ Redis连接正常
⚠️  流 job_events:my_job_123 不存在或为空
💡 等待新消息...

🔍 开始监控流: job_events:my_job_123
按 Ctrl+C 停止监控

============================================================
📨 新消息
流: job_events:my_job_123
ID: 1703123456789-0
时间: 2023-12-21 15:30:45

事件类型: task_started
数据:
{
  "job_id": "my_job_123",
  "status": "started",
  "timestamp": "2023-12-21T15:30:45Z"
}
============================================================
```

## 🛑 停止监控

所有脚本都支持使用 `Ctrl+C` 优雅停止：

```
🛑 正在停止监控...
✅ 监控已停止
```

## 🔧 配置说明

### Redis连接配置
所有脚本都使用以下默认配置：
- **主机**: 10.215.149.74
- **端口**: 26379
- **密码**: xJrhp*4mnHxbBWN2grqq
- **数据库**: 0

### 超时设置
- **默认超时**: 5000ms (5秒)
- **建议范围**: 1000-30000ms
- **超时过长**: 响应慢，但减少网络请求
- **超时过短**: 响应快，但增加网络请求

### 消息数量
- **默认数量**: 10条
- **建议范围**: 1-100条
- **数量过大**: 可能丢失消息
- **数量过小**: 处理频繁

## 🐛 故障排除

### 1. 连接失败
```bash
# 检查Redis服务
redis-cli -h 10.215.149.74 -p 26379 -a "xJrhp*4mnHxbBWN2grqq" ping

# 检查网络连接
ping 10.215.149.74
```

### 2. 没有消息
```bash
# 检查流是否存在
redis-cli -h 10.215.149.74 -p 26379 -a "xJrhp*4mnHxbBWN2grqq" KEYS "job_events:*"

# 检查流长度
redis-cli -h 10.215.149.74 -p 26379 -a "xJrhp*4mnHxbBWN2grqq" XLEN "job_events:my_job_123"
```

### 3. 权限问题
```bash
# 添加执行权限
chmod +x *.sh

# 检查Python依赖
pip install redis
```

## 📝 日志记录

所有脚本都会在控制台输出监控信息，建议重定向到文件：

```bash
# 保存监控日志
python3 redis_stream_monitor.py my_job_123 > monitor.log 2>&1

# 实时查看日志
tail -f monitor.log
```

## 🔄 持续监控

对于生产环境，建议使用 `nohup` 或 `screen` 进行后台监控：

```bash
# 后台运行
nohup python3 redis_stream_monitor.py my_job_123 > monitor.log 2>&1 &

# 查看进程
ps aux | grep redis_stream_monitor

# 停止监控
kill <PID>
``` 