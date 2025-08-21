#!/usr/bin/env python3
"""
启动脚本 - 从NACOS配置中读取worker数量并启动FastAPI服务
"""

import uvicorn
from doc_agent.core.config import settings
from doc_agent.core.logger import logger


def main():
    """主函数"""
    try:
        # 获取服务器配置
        server_config = settings.server_config
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8081)
        workers = server_config.get('workers', 8)
        
        logger.info(f"从配置中读取到服务器配置: host={host}, port={port}, workers={workers}")
        
        # 启动服务
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        # 使用默认配置启动
        logger.info("使用默认配置启动服务")
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8081,
            workers=8,
            log_level="info"
        )


if __name__ == "__main__":
    main()
