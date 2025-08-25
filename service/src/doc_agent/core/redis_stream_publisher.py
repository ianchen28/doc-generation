"""
Redis Streams 事件发布器

用于向 Redis Streams 发布任务事件，支持错误处理。
支持单节点和集群模式，统一使用原生redis。
"""

import json
import time
from typing import Optional, Union
from redis import Redis
from redis.cluster import RedisCluster

from doc_agent.core.logger import logger
from doc_agent.core.redis_health_check import get_redis_client


class RedisStreamPublisher:
    """
    使用原生redis的健壮事件发布器。
    支持单节点和集群模式。
    """

    def __init__(self, redis_client: Union[Redis, RedisCluster],
                 stream_name: str):
        if not hasattr(redis_client, 'xadd'):
            raise TypeError("redis_client 必须是一个 Redis 客户端实例")
        self.redis_client = redis_client
        self.stream_name = stream_name

        # 检查是否为集群模式
        self.is_cluster = hasattr(redis_client, 'cluster_nodes')

        logger.info(
            f"RedisStreamPublisher 已初始化，将发布到 Stream: '{self.stream_name}' "
            f"(模式: {'集群' if self.is_cluster else '单节点'})")

    def publish_event(self,
                      job_id: Union[str, int],
                      event_data: dict,
                      enable_listen_logger=True):

        job_id_str = str(job_id)

        try:
            # 2. 使用 Redis INCR 生成原子性的序列号
            counter_key = f"job_counter:{job_id_str}"
            i = self.redis_client.incr(counter_key)

            stream_name = f"job:{job_id_str}"
            # 使用时间戳作为ID的一部分，确保唯一性
            timestamp = int(time.time() * 1000)
            custom_id = f"{timestamp}-{i}"
            # logger.info(f"custom_id: {custom_id}")

            event_data["redisStreamKey"] = job_id_str
            event_data["redisStreamId"] = custom_id
            event_data["timestamp"] = self._get_current_timestamp()
            fields = {"data": json.dumps(event_data, ensure_ascii=False)}

            if enable_listen_logger:
                logger.info(f"redis_event listener: {fields}")

            # 4. 使用 xadd 命令，让Redis自动生成ID
            # 集群模式下，需要确保key路由到正确的节点
            event_id = self.redis_client.xadd(job_id_str, fields, id=custom_id)

            # 5. 设置过期时间（使用实际存储数据的 key）
            self.redis_client.expire(job_id_str, 24 * 60 * 60)

            if enable_listen_logger:
                logger.info(
                    f"事件发布成功: job_id={job_id_str}, event_id={event_id}, "
                    f"event_type={event_data.get('eventType', 'unknown')}, i={i}, "
                    f"模式={'集群' if self.is_cluster else '单节点'}")

        except Exception as e:
            logger.error(
                f"事件发布失败: job_id={job_id_str}, error_type={type(e).__name__}, "
                f"error_msg={e}, 模式={'集群' if self.is_cluster else '单节点'}")

    def publish_task_started(self, job_id: Union[str, int], task_type: str,
                             **kwargs) -> Optional[str]:
        """
        发布任务开始事件
        
        Args:
            job_id: 任务ID
            task_type: 任务类型 (如 "outline_generation", "document_generation")
            **kwargs: 额外的任务参数
            
        Returns:
            str: 事件ID
        """
        event_data = {
            "eventType": "task_started",
            "taskType": task_type,
            "status": "started",
            "timestamp": self._get_current_timestamp(),
            **kwargs
        }

        self.publish_event(job_id, event_data)

    def publish_task_progress(self, job_id: Union[str, int], task_type: str,
                              progress: str, **kwargs) -> Optional[str]:
        """
        发布任务进度事件
        
        Args:
            job_id: 任务ID
            task_type: 任务类型
            progress: 进度描述
            **kwargs: 额外的进度信息
            
        Returns:
            str: 事件ID
        """
        event_data = {
            "eventType": "task_progress",
            "taskType": task_type,
            "progress": progress,
            "status": "running",
            "timestamp": self._get_current_timestamp(),
            **kwargs
        }

        self.publish_event(job_id, event_data)

    def publish_task_completed(self,
                               job_id: Union[str, int],
                               task_type: str,
                               result: dict = None,
                               **kwargs) -> Optional[str]:
        """
        发布任务完成事件
        
        Args:
            job_id: 任务ID
            task_type: 任务类型
            result: 任务结果
            **kwargs: 额外的完成信息
            
        Returns:
            str: 事件ID
        """
        # 处理不可序列化的对象
        serializable_result = self._make_serializable(result) if result else {}
        serializable_kwargs = self._make_serializable(kwargs)

        event_data = {
            "eventType": "task_completed",
            "taskType": task_type,
            "status": "completed",
            "result": serializable_result,
            "timestamp": self._get_current_timestamp(),
            **serializable_kwargs
        }

        self.publish_event(job_id, event_data)

    def publish_task_failed(self, job_id: Union[str, int], task_type: str,
                            error: str, **kwargs) -> Optional[str]:
        """
        发布任务失败事件
        
        Args:
            job_id: 任务ID
            task_type: 任务类型
            error: 错误信息
            **kwargs: 额外的错误信息
            
        Returns:
            str: 事件ID
        """
        event_data = {
            "eventType": "task_failed",
            "taskType": task_type,
            "status": "failed",
            "error": error,
            "timestamp": self._get_current_timestamp(),
            **kwargs
        }

        self.publish_event(job_id, event_data)

    def publish_outline_generated(self, job_id: Union[str, int],
                                  outline: dict) -> Optional[str]:
        """
        发布大纲生成完成事件
        
        Args:
            job_id: 任务ID
            outline: 生成的大纲数据
            
        Returns:
            str: 事件ID
        """
        event_data = {
            "eventType": "outline_generated",
            "taskType": "outline_generation",
            "status": "completed",
            "outline": outline,
            "timestamp": self._get_current_timestamp()
        }

        self.publish_event(job_id, event_data)

    def publish_document_generated(self, job_id: Union[str, int],
                                   document: dict) -> Optional[str]:
        """
        发布文档生成完成事件
        
        Args:
            job_id: 任务ID
            document: 生成的文档数据
            
        Returns:
            str: 事件ID
        """
        # 处理不可序列化的对象
        serializable_document = self._make_serializable(document)

        event_data = {
            "eventType": "document_generated",
            "taskType": "document_generation",
            "status": "completed",
            "document": serializable_document,
            "timestamp": self._get_current_timestamp()
        }

        self.publish_event(job_id, event_data)

    def _make_serializable(self, obj):
        """
        将对象转换为可序列化的格式
        
        Args:
            obj: 要转换的对象
            
        Returns:
            可序列化的对象
        """
        if isinstance(obj, dict):
            return {
                key: self._make_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, 'model_dump'):
            # 如果是Pydantic模型，使用model_dump()
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # 如果是普通对象，转换为字典
            return obj.__dict__
        elif hasattr(obj, 'isoformat'):
            # 如果是datetime对象
            return obj.isoformat()
        else:
            # 如果是其他类型，尝试转换为字符串
            try:
                return str(obj)
            except:
                return f"<{type(obj).__name__} object>"

    def _get_current_timestamp(self) -> str:
        """
        获取当前时间戳（东八区时间）
        
        Returns:
            str: ISO 格式的时间戳（UTC+8）
        """
        from datetime import datetime, timezone, timedelta

        # 创建东八区时区
        tz_east_asia = timezone(timedelta(hours=8))

        # 获取当前UTC时间并转换为东八区时间
        utc_now = datetime.now(timezone.utc)
        east_asia_time = utc_now.astimezone(tz_east_asia)

        return east_asia_time.isoformat()

    def get_stream_info(self, job_id: Union[str, int]) -> Optional[dict]:
        """
        获取 Stream 信息
        
        Args:
            job_id: 任务ID
            
        Returns:
            dict: Stream 信息，如果不存在则返回 None
        """
        try:
            stream_name = str(job_id)  # 直接使用job_id作为流名称
            info = self.redis_client.xinfo_stream(stream_name)
            return info
        except Exception as e:
            logger.warning(f"获取 Stream 信息失败: job_id={job_id}, error={e}")
            return None

    def get_stream_length(self, job_id: Union[str, int]) -> int:
        """
        获取 Stream 长度
        
        Args:
            job_id: 任务ID
            
        Returns:
            int: Stream 中的事件数量
        """
        try:
            stream_name = str(job_id)  # 直接使用job_id作为流名称
            length = self.redis_client.xlen(stream_name)
            return length
        except Exception as e:
            logger.warning(f"获取 Stream 长度失败: job_id={job_id}, error={e}")
            return 0
