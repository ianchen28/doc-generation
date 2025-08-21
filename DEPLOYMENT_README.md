# AIDocGenerator 部署说明

## 环境要求

- Python 3.8+
- Redis 服务
- Conda 环境管理（推荐）

## 快速部署

### 1. 创建 Conda 环境

```bash
conda create -n ai-doc python=3.8
conda activate ai-doc
```

### 2. 安装依赖

```bash
# 安装服务依赖
cd service
pip install -r requirements.txt
pip install -e .

# 安装文件处理模块依赖
cd tools/file_module
pip install -r requirements.txt
```

### 3. 配置环境

1. 复制并配置环境变量文件
2. 确保 Redis 服务运行
3. 配置 Elasticsearch（如需要）

### 4. 启动服务

```bash
# 使用管理脚本启动
./manage.sh start 4 8081

# 或使用快速启动脚本
./quick_start_multi.sh 4 8081
```

### 5. 验证服务

```bash
# 健康检查
curl http://localhost:8081/health

# API 文档
http://localhost:8081/docs
```

## 目录结构

- `service/`: 主要服务代码
- `scripts/`: 管理脚本
- `docs/`: 文档
- `examples/`: 示例代码
- `tests/`: 测试代码
- `logs/`: 日志文件
- `output/`: 输出文件

## 管理命令

```bash
# 启动服务
./manage.sh start [worker_num] [port]

# 停止服务
./manage.sh stop

# 监控日志
./manage.sh monitor realtime

# 查看帮助
./manage.sh help
```

## 注意事项

1. 首次运行前请确保所有依赖已正确安装
2. 日志文件会自动轮转，避免磁盘空间不足
3. 多 worker 模式下建议使用负载均衡器
4. 生产环境请配置适当的安全设置
