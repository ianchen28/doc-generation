#!/usr/bin/env python3
"""
测试服务器配置读取
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from doc_agent.core.config import settings
from doc_agent.core.logger import logger


def test_server_config():
    """测试服务器配置读取"""
    try:
        print("=== 服务器配置测试 ===")
        
        # 获取服务器配置
        server_config = settings.server_config
        print(f"服务器配置: {server_config}")
        
        # 获取具体配置项
        workers = server_config.get('workers', 8)
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8081)
        
        print(f"Workers数量: {workers}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        
        # 验证配置
        if isinstance(workers, int) and workers > 0:
            print("✅ Workers配置验证通过")
        else:
            print("❌ Workers配置验证失败")
            
        if isinstance(port, int) and 1024 <= port <= 65535:
            print("✅ Port配置验证通过")
        else:
            print("❌ Port配置验证失败")
            
        print("\n=== 配置测试完成 ===")
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        logger.error(f"配置测试失败: {e}")


if __name__ == "__main__":
    test_server_config()
