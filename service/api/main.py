from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.endpoints import router
from doc_agent.core.logger import logger
from doc_agent.core.redis_health_check import close_redis_pool, init_redis_pool
from doc_agent.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("FastAPI应用正在启动...")
    # 初始化Redis连接池
    init_redis_pool()
    yield
    # 关闭
    logger.info("FastAPI应用正在关闭...")
    # 关闭Redis连接池
    close_redis_pool()


# 创建FastAPI应用实例
app = FastAPI(title="AI文档生成器API",
              description="AI驱动的文档生成服务API",
              version="1.0.0",
              lifespan=lifespan)

# 包含API路由器，设置prefix为/api/v1
app.include_router(router, prefix="/api/v1", tags=["API v1"])


def get_server_config():
    """获取服务器配置"""
    try:
        server_config = settings.server_config
        return {
            'host': server_config.get('host', '0.0.0.0'),
            'port': server_config.get('port', 8081),
            'workers': server_config.get('workers', 8)
        }
    except Exception as e:
        logger.warning(f"获取服务器配置失败，使用默认配置: {e}")
        return {
            'host': '0.0.0.0',
            'port': 8081,
            'workers': 8
        }


@app.get("/")
async def root():
    """根端点 - 健康检查"""
    logger.info("根端点被访问")
    return {"message": "AI文档生成器API服务", "status": "运行中", "version": "1.0.0"}


@app.get("/health")
async def health():
    """健康检查端点"""
    logger.info("健康检查端点被访问")
    return {"status": "healthy", "service": "AI文档生成器API"}


if __name__ == "__main__":
    server_config = get_server_config()
    logger.info(f"服务器配置: {server_config}")
    import uvicorn
    uvicorn.run(app, host=server_config['host'], port=server_config['port'], workers=server_config['workers'])