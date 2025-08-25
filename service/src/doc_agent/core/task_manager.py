# service/src/doc_agent/core/task_manager.py

import asyncio
import json
import os
import time
from typing import Optional

import redis.asyncio as redis

from doc_agent.core.config import settings
from doc_agent.core.logger import logger

# --- 全局变量 ---
# Redis 键名
RUNNING_TASKS_KEY = "doc_agent:running_tasks"
# Redis Pub/Sub 频道名
CANCELLATION_CHANNEL = "doc_agent:cancellation_channel"


class TaskManager:
    """
    使用 Redis 在多个 worker 之间管理任务状态和取消信号。
    这是一个单例模式的实现。
    """
    _instance = None
    _redis_client: Optional[redis.Redis] = None
    _pubsub_listener_task: Optional[asyncio.Task] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, running_tasks_in_worker: dict[str, asyncio.Task]):
        if not hasattr(self, '_initialized'):
            self.worker_id = str(os.getpid())
            self.running_tasks_in_worker = running_tasks_in_worker
            self._initialized = True
            logger.info(
                f"[TaskManager] Initialized for Worker PID: {self.worker_id}")

    @classmethod
    async def get_redis_client(cls) -> redis.Redis:
        """获取并缓存 Redis 客户端连接。"""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.from_url(settings.redis_url,
                                                   encoding="utf-8",
                                                   decode_responses=True)
                await cls._redis_client.ping()
                logger.info(
                    "[TaskManager] Redis client connected successfully.")
            except Exception as e:
                logger.error(f"[TaskManager] Failed to connect to Redis: {e}")
                raise
        return cls._redis_client

    async def register_task(self, task_id: str):
        """在 Redis 中注册一个新任务。"""
        try:
            client = await self.get_redis_client()
            task_data = json.dumps({
                "worker_id": self.worker_id,
                "status": "running",
                "created_at": time.time()
            })
            await client.hset(RUNNING_TASKS_KEY, task_id, task_data)
            logger.success(
                f"[TaskManager] Task {task_id} registered by worker {self.worker_id}."
            )
        except Exception as e:
            logger.error(
                f"[TaskManager] Failed to register task {task_id}: {e}")

    async def deregister_task(self, task_id: str):
        """从 Redis 中移除一个已完成的任务。"""
        try:
            client = await self.get_redis_client()
            await client.hdel(RUNNING_TASKS_KEY, task_id)
            logger.info(f"[TaskManager] Task {task_id} deregistered.")
        except Exception as e:
            logger.error(
                f"[TaskManager] Failed to deregister task {task_id}: {e}")

    async def get_global_task_stats(self) -> dict:
        """从 Redis 获取全局任务统计信息。"""
        try:
            client = await self.get_redis_client()
            running_tasks = await client.hgetall(RUNNING_TASKS_KEY)
            # await client.hset(RUNNING_TASKS_KEY, task_id, task_data)
            # running_tasks 的结构为 [{task_id: task_data}]

            # 统计活跃的 worker 数量
            active_workers = set()
            total_tasks = len(running_tasks.keys())
            task_detail_data = running_tasks

            for task_id, task_data in running_tasks.items():
                try:
                    task_info = json.loads(task_data)
                    worker_id = task_info.get("worker_id")
                    if worker_id:
                        active_workers.add(worker_id)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(
                        f"[TaskManager] Failed to parse task data for {task_id}: {e}"
                    )

            return {
                "global_running_tasks_detail": task_detail_data,
                "global_running_tasks": total_tasks,
                "active_workers_count": len(active_workers),
                "active_worker_ids": list(active_workers)
            }
        except Exception as e:
            logger.error(f"[TaskManager] Failed to get global task stats: {e}")
            return {
                "global_running_tasks": "Error",
                "active_workers_count": "Error"
            }

    async def get_worker_task_info(self, task_index: str) -> dict:
        """获取一个 task_id 在 task 所在 worker 中的排队位置"""
        try:
            client = await self.get_redis_client()
            running_tasks = await client.hgetall(RUNNING_TASKS_KEY)

            # 检查任务是否存在
            if task_index not in running_tasks:
                logger.warning(f"任务 {task_index} 不在运行中的任务列表中")
                return {"error": f"任务 {task_index} 不存在"}

            worker_task_list = []
            task_data = running_tasks[task_index]
            task_info = json.loads(task_data)
            task_worker_id = task_info.get("worker_id")
            logger.info(f"task_worker_id: {task_worker_id}")
            worker_ids = set()

            for task_id, task_data in running_tasks.items():
                try:
                    task_info = json.loads(task_data)
                    worker_id = task_info.get("worker_id")
                    worker_ids.add(worker_id)
                    if task_worker_id == worker_id:
                        worker_task_list.append(
                            (task_id, task_info.get("created_at")))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"解析任务 {task_id} 数据失败: {e}")
                    continue

            logger.info(f"worker_task_list: {worker_task_list}")

            # 按 created_at 排序后取 task_id
            worker_task_list.sort(key=lambda x: x[1])
            worker_task_id_list = [x[0] for x in worker_task_list]

            # 检查任务是否在列表中
            if task_index not in worker_task_id_list:
                logger.warning(f"任务 {task_index} 不在当前 worker 的任务列表中")
                return {"error": f"任务 {task_index} 不在当前 worker 的任务列表中"}

            task_position = worker_task_id_list.index(task_index) + 1
            worker_ids_list = list(worker_ids)
            logger.info(f"worker_ids: {worker_ids}")
            return {
                "task_position": task_position,
                "task_worker_id": task_worker_id,
                "worker_ids": worker_ids_list
            }

        except Exception as e:
            logger.error(
                f"[TaskManager] Failed to get worker task position: {e}")
            return {"error": str(e)}

    async def publish_cancellation(self, task_id: str):
        """发布一个任务取消请求到 Pub/Sub 频道。"""
        try:
            client = await self.get_redis_client()
            await client.publish(CANCELLATION_CHANNEL, task_id)
            logger.info(
                f"[TaskManager] Cancellation request for task {task_id} published."
            )
        except Exception as e:
            logger.error(
                f"[TaskManager] Failed to publish cancellation for task {task_id}: {e}"
            )

    async def cleanup_tasks_by_worker(self, worker_id: str = None):
        """清理指定 worker 的任务，如果不指定则清理当前 worker 的任务"""
        try:
            client = await self.get_redis_client()
            running_tasks = await client.hgetall(RUNNING_TASKS_KEY)

            target_worker = worker_id or self.worker_id
            tasks_to_remove = []

            for task_id, task_data in running_tasks.items():
                try:
                    task_info = json.loads(task_data)
                    if task_info.get("worker_id") == target_worker:
                        tasks_to_remove.append(task_id)
                except (json.JSONDecodeError, KeyError):
                    continue

            if tasks_to_remove:
                await client.hdel(RUNNING_TASKS_KEY, *tasks_to_remove)
                logger.info(
                    f"[TaskManager] Cleaned up {len(tasks_to_remove)} tasks for worker {target_worker}"
                )
            else:
                logger.info(
                    f"[TaskManager] No tasks found for worker {target_worker}")

        except Exception as e:
            logger.error(
                f"[TaskManager] Failed to cleanup tasks for worker {target_worker}: {e}"
            )

    async def cleanup_expired_tasks(self, max_age_seconds: int = 3600):
        """清理过期任务（超过指定时间的任务）"""
        try:
            client = await self.get_redis_client()
            running_tasks = await client.hgetall(RUNNING_TASKS_KEY)
            current_time = time.time()
            tasks_to_remove = []

            for task_id, task_data in running_tasks.items():
                try:
                    task_info = json.loads(task_data)
                    task_time = task_info.get("created_at", 0)
                    if current_time - task_time > max_age_seconds:
                        tasks_to_remove.append(task_id)
                except (json.JSONDecodeError, KeyError):
                    continue

            if tasks_to_remove:
                await client.hdel(RUNNING_TASKS_KEY, *tasks_to_remove)
                logger.info(
                    f"[TaskManager] Cleaned up {len(tasks_to_remove)} expired tasks"
                )
            else:
                logger.info("[TaskManager] No expired tasks found")

        except Exception as e:
            logger.error(f"[TaskManager] Failed to cleanup expired tasks: {e}")

    async def _pubsub_listener(self):
        """后台监听器，用于处理取消消息。"""
        while True:
            try:
                client = await self.get_redis_client()
                pubsub = client.pubsub()
                await pubsub.subscribe(CANCELLATION_CHANNEL)
                logger.info(
                    f"[TaskManager] Worker {self.worker_id} subscribed to {CANCELLATION_CHANNEL}."
                )

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        task_id_to_cancel = message["data"]
                        logger.info(
                            f"[TaskManager] Worker {self.worker_id} received cancellation signal for task {task_id_to_cancel}."
                        )

                        # 检查这个任务是否由当前 worker 管理
                        task = self.running_tasks_in_worker.get(
                            task_id_to_cancel)
                        if task and not task.done():
                            task.cancel()
                            logger.success(
                                f"[TaskManager] Worker {self.worker_id} cancelled task {task_id_to_cancel}."
                            )
            except redis.ConnectionError:
                logger.warning(
                    "[TaskManager] Redis connection lost. Reconnecting in 5 seconds..."
                )
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(
                    f"[TaskManager] Pub/Sub listener failed: {e}. Restarting in 10 seconds..."
                )
                await asyncio.sleep(10)

    @classmethod
    async def start_listener(cls, running_tasks_in_worker: dict[str,
                                                                asyncio.Task]):
        """启动后台 Pub/Sub 监听器。"""
        if cls._instance is None:
            cls(running_tasks_in_worker
                )  # a little tricky to ensure singleton is initialized

        if cls._pubsub_listener_task is None or cls._pubsub_listener_task.done(
        ):
            logger.info("[TaskManager] Starting Pub/Sub listener...")
            cls._pubsub_listener_task = asyncio.create_task(
                cls._instance._pubsub_listener())
        else:
            logger.warning("[TaskManager] Listener already running.")

        client = await cls.get_redis_client()
        # 清理 redis 中的 RUNNING_TASKS_KEY 中的内容
        # 注意：这里会清空所有任务，在生产环境中要谨慎使用
        await client.delete(RUNNING_TASKS_KEY)
        # logger.info("[TaskManager] Cleared all running tasks from Redis")

    @classmethod
    async def stop_listener(cls):
        """停止后台 Pub/Sub 监听器。"""
        if cls._pubsub_listener_task and not cls._pubsub_listener_task.done():
            cls._pubsub_listener_task.cancel()
            try:
                await cls._pubsub_listener_task
            except asyncio.CancelledError:
                pass  # Expected
            logger.info("[TaskManager] Pub/Sub listener stopped.")
        if cls._redis_client:
            await cls._redis_client.close()
            cls._redis_client = None
            logger.info("[TaskManager] Redis client connection closed.")
