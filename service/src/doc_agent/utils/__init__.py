# service/src/doc_agent/utils/__init__.py
"""
工具模块包
"""

from .content_processor import (
    expand_content,
    extract_key_points,
    process_research_data,
    summarize_content,
)

# redis_client 中的全局实例 redis_meta_client
from .redis_client import redis_meta_client
from .timing import (
    CodeTimer,
    timeit,
)

__all__ = [
    'summarize_content', 'extract_key_points', 'expand_content',
    'process_research_data', 'CodeTimer', 'timeit', 'redis_meta_client'
]
