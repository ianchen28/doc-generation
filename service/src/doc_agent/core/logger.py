#!/usr/bin/env python3
"""
统一日志模块
整个项目使用统一的日志配置
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

# 检查是否已经配置了日志系统
if not logger._core.handlers:
    # 如果没有配置，使用默认配置
    from .logging_config import setup_logging
    from .config import settings

    # 设置统一日志配置
    setup_logging(settings)


def get_logger(name: str = None):
    """
    获取统一配置的logger实例
    
    Args:
        name: 模块名称，用于标识日志来源
        
    Returns:
        loguru.logger: 配置好的日志器实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 确保logger对象具有所有loguru的方法
# 这些方法在loguru.logger中已经存在，但为了明确性，我们在这里确保它们可用
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
success = logger.success
exception = logger.exception

# 导出统一的logger实例和所有日志方法
__all__ = [
    'logger', 'get_logger', 'debug', 'info', 'warning', 'error', 'critical',
    'success', 'exception'
]
