# 服务器配置说明

## 概述

本项目已将Dockerfile中硬编码的worker数量改为从NACOS配置中动态读取，实现了配置化管理。

## 配置结构

### NACOS配置

在NACOS配置文件中添加以下配置项：

```json
{
  "server": {
    "workers": 8,
    "host": "0.0.0.0",
    "port": 8081
  }
}
```

### 环境变量

可以通过以下环境变量配置NACOS连接：

```bash
ENV=dev
NACOS_NAMESPACE=hdec-llm
NACOS_GROUP=DEFAULT_GROUP
NACOS_DATA_ID=doc-generation.json
NACOS_SERVER_ADDRESSES=nacos.common.svc.cluster.local:8848
```

## 启动方式

### 1. 使用启动脚本（推荐）

```bash
python start_server.py
```

启动脚本会自动：
- 从NACOS配置中读取服务器配置
- 使用配置的worker数量启动服务
- 如果配置读取失败，使用默认配置

### 2. 直接使用uvicorn

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8081 --workers 8
```

### 3. Docker容器启动

容器会自动使用启动脚本，无需手动指定worker数量。

## 配置优先级

1. NACOS配置（最高优先级）
2. 环境变量
3. 默认配置（最低优先级）

## 默认配置

如果所有配置都不可用，系统将使用以下默认值：

- workers: 8
- host: 0.0.0.0
- port: 8081

## 故障排除

### 配置读取失败

如果NACOS配置读取失败，系统会：
1. 记录警告日志
2. 使用默认配置启动
3. 继续正常运行

### 日志查看

启动时会显示实际使用的配置：

```
INFO: 从配置中读取到服务器配置: host=0.0.0.0, port=8081, workers=8
```

## 动态配置更新

修改NACOS配置后，需要重启服务才能生效。未来可以考虑实现热重载功能。
