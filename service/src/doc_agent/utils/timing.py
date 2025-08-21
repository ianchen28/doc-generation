# service/src/doc_agent/utils/timing.py
import time
from functools import wraps
from doc_agent.core import logger


class CodeTimer:
    """
    一个简单的代码计时器，可以用作装饰器或上下文管理器。
    """

    def __init__(self,
                 name: str,
                 state: dict = None,
                 metrics_key: str = "performance_metrics"):
        self.name = name
        self.state = state
        self.metrics_key = metrics_key

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        logger.debug(f"⏱️  '{self.name}' executed in: {elapsed_time:.4f}s")
        if self.state is not None:
            if self.metrics_key not in self.state:
                self.state[self.metrics_key] = {}

            if self.name not in self.state[self.metrics_key]:
                self.state[self.metrics_key][self.name] = []

            self.state[self.metrics_key][self.name].append(elapsed_time)


def timeit(name: str):
    """
    一个装饰器，用于包装函数并记录其执行时间。
    """

    def decorator(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.debug(f"⏱️  '{name}' executed in: {elapsed_time:.4f}s")
            # 注意：装饰器版本无法轻易地将耗时写回 state，主要用于日志记录
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.debug(f"⏱️  '{name}' executed in: {elapsed_time:.4f}s")
            return result

        # 根据函数的异步/同步特性选择合适的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
