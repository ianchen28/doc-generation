import json

import redis

from doc_agent.config.nacos_config import config_file as settings
from doc_agent.core import logger


class RedisMetaClient:
    """
    Redis元信息查询客户端
    """

    def __init__(self):
        self.redis_client = None
        self.meta_key_pattern = "Data:governance:llm:meta:{}"
        self._initialize_client()

    def _initialize_client(self):
        """初始化Redis客户端"""
        try:

            # 从配置中获取Redis连接信息，如果没有则使用默认值
            redis_settings = settings.get('redis', {}).get('single', {})
            redis_host = redis_settings.get('host', '10.215.149.74')
            redis_port = redis_settings.get('port', '10.215.149.74')
            redis_password = redis_settings.get('password',
                                                'xJrhp*4mnHxbBWN2grqq')
            redis_db = redis_settings.get('db', 0)

            logger.info(
                f"尝试连接Redis: {redis_host}:{redis_port}, DB: {redis_db}")

            # 创建Redis连接池
            pool = redis.ConnectionPool(host=redis_host,
                                        port=redis_port,
                                        password=redis_password,
                                        db=redis_db,
                                        decode_responses=True,
                                        socket_timeout=5,
                                        socket_connect_timeout=5,
                                        retry_on_timeout=True)

            self.redis_client = redis.Redis(connection_pool=pool)

            # 测试连接
            ping_result = self.redis_client.ping()
            logger.info(
                f"Redis客户端连接成功: {redis_host}:{redis_port}, ping结果: {ping_result}"
            )

        except Exception as e:
            logger.error(f"Redis客户端初始化失败: {str(e)}")
            self.redis_client = None

    def get_meta_info_from_redis(self,
                                 file_tokens: list[str]) -> dict[str, dict]:
        """
        从Redis中批量获取元信息原始数据
        
        Args:
            file_tokens: 文件token列表
            
        Returns:
            dict: {fileToken: redis_raw_data}，包含Redis原始数据和解析后的metaInfo
                 redis_raw_data包含所有Redis hash字段 + parsed_metaInfo字段
        """
        if not self.redis_client or not file_tokens:
            return {}

        result = {}
        found_tokens = []

        try:
            logger.debug(f"开始从Redis查询 {len(file_tokens)} 个token的元信息")

            # 使用pipeline提高批量查询性能
            pipe = self.redis_client.pipeline()

            # 为每个token添加hgetall查询
            hash_keys = []
            for token in file_tokens:
                hash_key = self.meta_key_pattern.format(token)
                hash_keys.append(hash_key)
                pipe.hgetall(hash_key)

            logger.debug(f"查询的Redis keys: {hash_keys}")

            # 执行批量查询
            redis_results = pipe.execute()
            logger.debug(f"Redis pipeline返回结果数量: {len(redis_results)}")

            # 处理查询结果
            for i, token in enumerate(file_tokens):
                redis_data = redis_results[i]

                # 检查redis_data的类型和内容
                if redis_data and isinstance(redis_data,
                                             dict) and len(redis_data) > 0:
                    try:
                        # 解析metaInfo字段（可能是双重JSON编码）
                        meta_info_str = redis_data.get('metaInfo', '{}')
                        if meta_info_str:
                            # 首先尝试解析JSON
                            first_parse = json.loads(meta_info_str)
                            # 如果解析结果是字符串，说明是双重编码，需要再次解析
                            if isinstance(first_parse, str):
                                meta_info = json.loads(first_parse)
                                logger.debug(
                                    f"双重JSON解码成功，token: {token}, 结果: {meta_info}"
                                )
                            else:
                                meta_info = first_parse
                                logger.debug(
                                    f"单层JSON解码成功，token: {token}, 结果: {meta_info}"
                                )
                        else:
                            meta_info = {}
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(
                            f"解析metaInfo失败，token: {token}, 原始值: {meta_info_str}, 错误: {str(e)}"
                        )
                        meta_info = {}

                    # 直接返回Redis原始数据，包含解析后的metaInfo
                    redis_data['parsed_metaInfo'] = meta_info
                    result[token] = redis_data
                    found_tokens.append(token)
                else:
                    # 记录无效数据的情况
                    if redis_data:
                        logger.warning(
                            f"Redis返回的数据格式不正确，token: {token}, 数据类型: {type(redis_data)}, 数据: {redis_data}"
                        )
                    else:
                        logger.debug(f"Redis中没有找到token: {token}")

            logger.info(f"从Redis获取到 {len(found_tokens)} 个fileToken的元信息")
            return result

        except Exception as e:
            logger.error(f"从Redis获取元信息失败: {str(e)}")
            return {}

    def get_missing_tokens(self, all_tokens: list[str]) -> list[str]:
        """
        获取Redis中不存在的fileToken列表
        
        Args:
            all_tokens: 所有需要查询的token列表
            
        Returns:
            List[str]: Redis中不存在的token列表
        """
        if not self.redis_client or not all_tokens:
            return all_tokens

        try:
            pipe = self.redis_client.pipeline()

            # 检查每个token的hash是否存在
            hash_keys = []
            for token in all_tokens:
                hash_key = self.meta_key_pattern.format(token)
                hash_keys.append(hash_key)
                pipe.exists(hash_key)

            logger.debug(f"检查存在性的Redis keys: {hash_keys}")
            exists_results = pipe.execute()
            logger.debug(f"存在性检查结果: {exists_results}")

            # 返回不存在的token
            missing_tokens = []
            for i, token in enumerate(all_tokens):
                if not exists_results[i]:  # 如果不存在
                    missing_tokens.append(token)

            logger.debug(f"缺失的tokens: {missing_tokens}")
            return missing_tokens

        except Exception as e:
            logger.error(f"检查Redis中缺失的token失败: {str(e)}")
            # 如果Redis查询失败，返回所有token（走HTTP接口）
            return all_tokens


# 全局Redis客户端实例
redis_meta_client = RedisMetaClient()
