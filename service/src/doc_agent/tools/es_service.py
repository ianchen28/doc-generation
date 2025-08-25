"""
Elasticsearch 底层服务模块
提供基础的ES连接和搜索功能，支持KNN向量搜索
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch

from doc_agent.core.logger import logger
from doc_agent.utils.meta_api import update_doc_meta_data
from doc_agent.utils.timing import CodeTimer


@dataclass
class ESSearchResult:
    """ES搜索结果"""
    id: str
    doc_id: str  # file_token
    index: str  # 索引
    domain_id: str  # index 映射之后的 domain_id
    doc_from: str  # 来源 self/data_platform （用户上传为 self， 其他为 data_platform）
    file_token: str  # file_token (大概率没有值)
    original_content: str  # 原始内容
    div_content: str = ""  # 切分后的内容
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = None
    alias_name: str = ""  # 来源索引别名

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


"""
ES 说明

index_id
alias_id
valid_indeces
type_id

一个真实 index_id 对应最多一个 alias_id
一个 alias_id 可能对应多个 index_id

alias_id -> 多个 index_id

有一个 domainid -> valid_alias 的映射表，需要从中得到 valid_aliases 然后找到 index_id 和 domain_id 的对应关系

valid_indeces
valid_indeces -> domain_id

根据 domain_id -> type_id 的映射表，得到 type_id


"""


class ESService:
    """ES底层服务类"""

    def __init__(self,
                 hosts: list[str],
                 username: str = "",
                 password: str = "",
                 timeout: int = 30,
                 connections_per_node: int = 25):
        """
        初始化ES服务

        Args:
            hosts: ES服务器地址列表
            username: 用户名
            password: 密码
            timeout: 超时时间
            connections_per_node: 每个节点的连接数
        """
        self.hosts = hosts
        self.username = username
        self.password = password
        self.timeout = timeout
        self.connections_per_node = connections_per_node
        self._client: Optional[AsyncElasticsearch] = None
        self._initialized = False
        logger.info("初始化ES服务")
        # domain_id -> alias_id/index_id
        self.domain_id_to_alias_id_map = {
            # "documentUploadAnswer": "personal_knowledge_base",
            "standard": "standard_index_prod",
            "thesis": "thesis_index_prod",
            "book": "book_index_prod",
            "other": "other_index_prod",
            "internal": "internal_index_prod_v2",
            "policy": "hdy_knowledge_prod_v2",
            "executivevoice": "hdy_knowledge_prod_v2",
            "corporatenews": "hdy_knowledge_prod_v2",
            "announcement": "hdy_knowledge_prod_v2",
            "ai_demo": "ai_demo"
        }
        # alias_id -> index_id
        self.alias_id_to_index_id_map = {}
        # indeces without alias
        self.index_id_without_alias = []
        # index_id -> domain_id
        self.index_id_to_domain_id_map = {}
        self.valid_indeces = []
        self._es_request_semaphore = asyncio.Semaphore(connections_per_node)
        self._ensure_connected()

    async def connect(self) -> bool:
        """连接ES服务"""
        logger.info("开始连接ES服务")
        try:
            es_kwargs = {
                "hosts": self.hosts,
                "verify_certs": False,
                "ssl_show_warn": False,
                "request_timeout": self.timeout,
                "max_retries": 3,
                "retry_on_timeout": True,
                # 连接池配置（参考AsyncElasticsearch源码）
                "connections_per_node": self.connections_per_node,  # 每个节点的连接数
                # HTTP连接器配置
                "http_compress": True,  # 启用HTTP压缩
                # 重试配置（根据源码支持的参数）
                "retry_on_status": [502, 503, 504],  # 指定重试的HTTP状态码
                # 连接管理配置
                "dead_node_backoff_factor": 2.0,  # 死节点退避因子
                "max_dead_node_backoff": 300.0,  # 最大死节点退避时间（秒）
                # 节点嗅探配置（在高并发场景下建议关闭）
                "sniff_on_start": False,  # 启动时不嗅探节点
                "sniff_before_requests": False,  # 请求前不嗅探节点
                "sniff_on_node_failure": False,  # 节点失败时不嗅探
            }

            if self.username and self.password:
                es_kwargs["basic_auth"] = (self.username, self.password)
                logger.debug("使用基本认证连接ES")

            self._client = AsyncElasticsearch(**es_kwargs)

            # 测试连接
            await self._client.ping()
            logger.info("ES连接成功")

            # 获取索引别名
            # index_id -> alias_id
            self.aliases_info = await self._client.indices.get_alias(index="*")
            logger.info(f"aliases_info: {self.aliases_info}")

            # 获取 alias_id -> index_id 的映射
            for index_name, info in self.aliases_info.items():
                if 'aliases' in info:
                    # aliases 字段可能有多个值，取第一个
                    alias_ids = list(info['aliases'].keys())
                    if alias_ids:
                        alias_id = alias_ids[0]
                        if alias_id not in self.alias_id_to_index_id_map:
                            self.alias_id_to_index_id_map[alias_id] = []
                        self.alias_id_to_index_id_map[alias_id].append(
                            index_name)
                else:
                    self.index_id_without_alias.append(index_name)

            # 结合 domain_id_to_alias_id_map 和 alias_id_to_index_id_map 构建 index_id_to_domain_id_map
            # 在 domain_id 范围内
            for domain_id, alias_or_index_id in self.domain_id_to_alias_id_map.items(
            ):
                if alias_or_index_id in self.alias_id_to_index_id_map:
                    # alias_or_index_id is alias_id and has multiple index_id
                    for index_id in self.alias_id_to_index_id_map[
                            alias_or_index_id]:
                        self.index_id_to_domain_id_map[index_id] = domain_id
                elif alias_or_index_id in self.index_id_without_alias:
                    # alias_or_index_id is index_id and has no alias and is not in index_id_without_alias
                    self.index_id_to_domain_id_map[
                        alias_or_index_id] = domain_id
                else:
                    logger.warning(
                        f"index {alias_or_index_id} has domain_id {domain_id} but not listed in client's index"
                    )

            # 构建 valid_indeces
            self.valid_indeces = list(self.index_id_to_domain_id_map.keys())
            logger.info(f"成功获取索引别名映射，共 {len(self.valid_indeces)} 个索引")

            logger.info(f"valid_indeces: {self.valid_indeces}")
            logger.info(
                f"index_id_to_domain_id_map: {self.index_id_to_domain_id_map}")
            logger.info(
                f"alias_id_to_index_id_map: {self.alias_id_to_index_id_map}")
            logger.info(
                f"index_id_without_alias: {self.index_id_without_alias}")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"ES连接失败: {str(e)}")
            self._initialized = False
            return False

    async def _ensure_connected(self):
        """确保已连接"""
        if not self._initialized or not self._client:
            logger.debug("ES客户端未连接，尝试连接")
            await self.connect()

    async def search_by_file_token(self,
                                   index: str,
                                   file_token: str,
                                   top_k: int = 100) -> list[ESSearchResult]:
        """
        根据file_token查询文档内容
        
        Args:
            index: 索引名称
            file_token: 文件token
            top_k: 返回结果数量
            
        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始按file_token查询，索引: {index}, file_token: {file_token}")

        # 验证索引是否在有效范围内（允许通配符索引用于文档范围搜索）
        index = "personal_knowledge_base"

        await self._ensure_connected()

        if not self._client:
            logger.error("ES客户端未连接")
            return []

        try:
            search_body = {
                "size": top_k * 2,  # 设置更大的size
                "query": {
                    "term": {
                        "doc_id": file_token
                    }
                }
                # 移除排序，避免字段不存在的问题
            }

            logger.debug(f"file_token查询体: {search_body}")

            # 执行搜索
            response = await self._client.search(index=index, body=search_body)

            # 解析结果
            results = []
            docs = []

            # 为每个文档设置 index 和 domain_id，以便 update_doc_meta_data 使用
            for hit in response['hits']['hits']:
                doc = hit['_source'].copy()

                doc['_id'] = hit['_id']  # 添加 _id 字段
                doc['index'] = hit['_index']  # 添加 index 字段

                index = doc['index']
                # domain_id = self.index_id_to_domain_id_map.get(index, "")
                domain_id = "documentUploadAnswer"

                if not domain_id:
                    logger.info(f"未找到索引 {index} 的域名映射")
                logger.info(f"index_id -> domain_id: {index} -> {domain_id}")

                doc['domain_id'] = domain_id
                docs.append(doc)

            docs = update_doc_meta_data(docs)

            for doc in docs:
                # 安全获取 doc_id
                doc_id = doc.get('doc_id', "")
                index = doc.get('index', "")
                domain_id = doc.get('domain_id', "")  # 使用之前设置的 domain_id

                doc_from = "self" if domain_id == "documentUploadAnswer" else "data_platform"

                logger.debug(
                    f"file_token查询结果 - 索引: {index}, domain_id: {domain_id}, doc_from: {doc_from}"
                )
                original_content = (doc.get('content_view')
                                    or doc.get('content') or doc.get('text')
                                    or doc.get('title') or '')
                div_content = (doc.get('content') or doc.get('text')
                               or doc.get('title') or '')

                source = (doc.get('meta_data', {}).get('file_name')
                          or doc.get('file_name') or doc.get('name') or '')

                result = ESSearchResult(id=doc['_id'],
                                        doc_id=doc_id,
                                        index=index,
                                        domain_id=domain_id,
                                        doc_from=doc_from,
                                        file_token=doc.get('file_token', ""),
                                        original_content=original_content,
                                        div_content=div_content,
                                        source=source,
                                        score=doc.get('score', 0.0),
                                        metadata=doc.get('meta_data', {}),
                                        alias_name=index)
                # 修改 metadata.source = doc_from
                result.metadata["source"] = doc_from
                results.append(result)

            logger.info(f"file_token查询成功，返回 {len(results)} 个文档")
            return results

        except Exception as e:
            logger.error(f"file_token查询失败: {str(e)}")
            return []

    async def search(
            self,
            index: str,
            query: str,
            top_k: int = 10,
            query_vector: Optional[list[float]] = None,
            filters: Optional[dict[str, Any]] = None) -> list[ESSearchResult]:
        """
        执行ES搜索

        Args:
            index: 索引名称
            query: 搜索查询
            top_k: 返回结果数量
            query_vector: 查询向量（可选）
            filters: 过滤条件（可选）

        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始ES搜索，索引: {index}, 查询: {query[:50]}...")
        logger.debug(f"搜索参数 - top_k: {top_k}")
        if query_vector:
            logger.debug(f"查询向量维度: {len(query_vector)}")
        if filters:
            logger.debug(f"过滤条件: {filters}")

        # 验证索引是否在有效范围内（允许通配符索引用于文档范围搜索）
        if index == "*":
            index = self.valid_indeces

        await self._ensure_connected()

        if not self._client:
            logger.error("ES客户端未连接")
            return []

        try:
            # 构建搜索查询
            search_body = self._build_search_body(query, query_vector, filters,
                                                  top_k)
            # logger.debug(f"搜索查询体: {search_body}")

            logger.info(f"搜索query <es_search>: {query}")
            start_time = time.time()
            # 使用信号量控制并发
            with CodeTimer("es_search <timer>"):
                async with self._es_request_semaphore:
                    # 执行搜索
                    response = await self._client.search(index=index,
                                                         body=search_body)
            end_time = time.time()
            logger.info(
                f"ES搜索耗时<es_search>: {query} {end_time - start_time:.4f} 秒")

            # 解析结果
            results = []
            docs = []
            for hit in response['hits']['hits']:
                doc = hit['_source'].copy()
                index = hit["_index"]
                doc["index"] = index
                domain_id = self.index_id_to_domain_id_map.get(index, "")
                doc["domain_id"] = domain_id
                docs.append(doc)

            docs = update_doc_meta_data(docs)

            for doc in docs:
                # 获取原始内容和切分后的内容
                original_content = (doc.get('content_view')
                                    or doc.get('content') or doc.get('text')
                                    or doc.get('title') or '')

                div_content = (doc.get('content') or doc.get('text')
                               or doc.get('title') or '')

                # 灵活获取来源字段
                source = (doc.get('meta_data', {}).get('file_name')
                          or doc.get('file_name') or doc.get('name') or '')

                # 安全获取 doc_id，如果不存在则使用 _id
                doc_id = doc.get('doc_id', "")
                index = hit["_index"]
                domain_id = self.index_id_to_domain_id_map.get(index, "")
                if index == "personal_knowledge_base":
                    domain_id = "documentUploadAnswer"

                doc_from = "self" if domain_id == "documentUploadAnswer" else "data_platform"

                logger.info(
                    f"搜索结果 - 索引: {index}, domain_id: {domain_id}, doc_from: {doc_from}"
                )

                result = ESSearchResult(id=hit['_id'],
                                        doc_id=doc_id,
                                        index=index,
                                        domain_id=domain_id,
                                        doc_from=doc_from,
                                        file_token=doc.get('file_token', ""),
                                        original_content=original_content,
                                        div_content=div_content,
                                        source=source,
                                        score=hit['_score'],
                                        metadata=doc.get('meta_data', {}),
                                        alias_name=index)
                # 修改 metadata.source = doc_from
                result.metadata["source"] = doc_from
                results.append(result)

            logger.info(f"ES搜索成功，返回 {len(results)} 个文档")
            return results

        except Exception as e:
            logger.error(f"ES搜索失败: {str(e)}")
            return []

    def _build_search_body(self,
                           query: str,
                           query_vector: Optional[list[float]] = None,
                           filters: Optional[dict[str, Any]] = None,
                           top_k: int = 10) -> dict[str, Any]:
        """
        构建搜索查询体

        Args:
            query: 搜索查询
            query_vector: 查询向量
            filters: 过滤条件
            top_k: 返回结果数量

        Returns:
            Dict[str, Any]: 搜索查询体
        """
        # 如果有向量查询，优先使用KNN搜索
        if query_vector:
            logger.debug("使用KNN向量搜索")
            return self._build_knn_search_body(query_vector, query, filters,
                                               top_k)
        else:
            logger.debug("使用文本搜索")
            return self._build_text_search_body(query, filters, top_k)

    def _build_knn_search_body(self,
                               query_vector: list[float],
                               query: str = "",
                               filters: Optional[dict[str, Any]] = None,
                               top_k: int = 10) -> dict[str, Any]:
        """
        构建KNN向量搜索查询体

        Args:
            query_vector: 查询向量
            query: 文本查询（可选，用于混合搜索）
            filters: 过滤条件
            top_k: 返回结果数量

        Returns:
            Dict[str, Any]: KNN搜索查询体
        """
        # 确保向量维度正确
        if len(query_vector) != 1536:
            if len(query_vector) > 1536:
                query_vector = query_vector[:1536]
                logger.debug("截断向量维度到 1536")
            else:
                query_vector.extend([0.0] * (1536 - len(query_vector)))
                logger.debug("扩展向量维度到 1536")

        # 构建基础KNN查询
        search_body = {
            "size": top_k,
            "_source": {
                "excludes": ["content"]  # 排除大字段以提高性能
            },
            "knn": {
                "field": "context_vector",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 2
            }
        }

        # 构建过滤条件
        filter_conditions = []

        # 添加 valid 过滤条件
        filter_conditions.append({'term': {'valid': True}})

        # 添加自定义过滤条件（如果存在）
        if filters:
            logger.debug(f"添加KNN过滤条件: {filters}")
            for key, value in filters.items():
                if isinstance(value, list):
                    if value:  # 非空列表
                        filter_conditions.append({"terms": {key: value}})
                elif value is not None:
                    filter_conditions.append({"term": {key: value}})

        # 如果有过滤条件，添加到KNN查询中
        if filter_conditions:
            search_body["knn"]["filter"] = {
                'bool': {
                    'must': filter_conditions,
                    'must_not': []
                }
            }

        logger.info(f"构建的KNN搜索查询体: {search_body}")

        return search_body

    def _build_text_search_body(self,
                                query: str,
                                filters: Optional[dict[str, Any]] = None,
                                top_k: int = 10) -> dict[str, Any]:
        """
        构建文本搜索查询体

        Args:
            query: 搜索查询
            filters: 过滤条件
            top_k: 返回结果数量

        Returns:
            Dict[str, Any]: 文本搜索查询体
        """
        # 基础文本查询
        search_body = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [{
                        "multi_match": {
                            "query":
                            query,
                            "fields": [
                                "content^2", "file_name", "title^2", "text^2",
                                "name"
                            ],
                            "type":
                            "best_fields"
                        }
                    }],
                    "minimum_should_match":
                    1
                }
            }
        }

        # 添加过滤条件
        if filters:
            logger.debug(f"添加过滤条件: {filters}")
            filter_conditions = self._build_filter_conditions(filters)
            search_body["query"]["bool"]["filter"] = filter_conditions["bool"][
                "must"]

        return search_body

    def _build_filter_conditions(self, filters: dict[str,
                                                     Any]) -> dict[str, Any]:
        """
        构建过滤条件

        Args:
            filters: 过滤条件字典

        Returns:
            Dict[str, Any]: 过滤条件查询体
        """
        filter_conditions = {"bool": {"must": [], "must_not": []}}

        for key, value in filters.items():
            if isinstance(value, list):
                if value:  # 非空列表
                    filter_conditions["bool"]["must"].append(
                        {"terms": {
                            key: value
                        }})
            elif value is not None:
                filter_conditions["bool"]["must"].append(
                    {"term": {
                        key: value
                    }})

        logger.debug(f"构建的过滤条件: {filter_conditions}")
        return filter_conditions

    async def search_multiple_indices(
            self,
            indices: list[str],
            query: str,
            top_k: int = 10,
            query_vector: Optional[list[float]] = None,
            filters: Optional[dict[str, Any]] = None) -> list[ESSearchResult]:
        """
        在多个索引中搜索

        Args:
            indices: 索引列表
            query: 搜索查询
            top_k: 返回结果数量
            query_vector: 查询向量
            filters: 过滤条件

        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始多索引搜索，索引数量: {len(indices)}")
        logger.debug(f"索引列表: {indices}")
        logger.debug(f"搜索参数 - top_k: {top_k}")
        if query_vector:
            logger.debug(f"查询向量维度: {len(query_vector)}")
        if filters:
            logger.debug(f"过滤条件: {filters}")

        if not indices:
            logger.warning("索引列表为空")
            return []

        # 过滤出有效的索引
        valid_indices = [idx for idx in indices if idx in self.valid_indeces]
        if not valid_indices:
            logger.warning(f"所有索引都不在有效范围内: {indices}")
            return []

        if len(valid_indices) != len(indices):
            invalid_indices = [
                idx for idx in indices if idx not in self.valid_indeces
            ]
            logger.warning(f"过滤掉无效索引: {invalid_indices}")

        await self._ensure_connected()

        if not self._client:
            logger.error("ES客户端未连接")
            return []

        try:
            # 构建msearch请求体
            msearch_body = []
            search_body = self._build_search_body(query, query_vector, filters,
                                                  top_k)

            for index in valid_indices:
                msearch_body.append({"index": index})
                msearch_body.append(search_body)

            logger.debug(f"构建msearch请求体，包含 {len(indices)} 个索引")

            # 执行msearch
            response = await self._client.msearch(body=msearch_body)

            # 处理结果
            all_results = []
            for i, search_response in enumerate(response["responses"]):
                if "hits" in search_response and "hits" in search_response[
                        "hits"]:
                    for hit in search_response["hits"]["hits"]:
                        doc_data = hit["_source"]

                        # 获取内容
                        original_content = (doc_data.get('content_view')
                                            or doc_data.get('content')
                                            or doc_data.get('text')
                                            or doc_data.get('title') or '')

                        div_content = (doc_data.get('content')
                                       or doc_data.get('text')
                                       or doc_data.get('title') or '')

                        # 获取来源
                        source = (doc_data.get('meta_data',
                                               {}).get('file_name')
                                  or doc_data.get('file_name')
                                  or doc_data.get('name') or '')

                        # 安全获取 doc_id，如果不存在则使用 _id
                        doc_id = doc_data.get('doc_id', "")
                        index = hit["_index"]
                        domain_id = self.index_id_to_domain_id_map.get(
                            index, "")

                        # 如果找不到domain_id，尝试从索引名称推断
                        if not domain_id:
                            # 尝试从索引名称推断域名
                            for known_domain, known_index in self.domain_index_map.items(
                            ):
                                if index == known_index or index in self.index_aliases.get(
                                        known_index, []):
                                    domain_id = known_domain
                                    break

                            # 如果还是找不到，使用索引名称作为domain_id
                            if not domain_id:
                                domain_id = index
                                logger.debug(
                                    f"未找到索引 {index} 的域名映射，使用索引名称作为domain_id")

                        doc_from = "self" if domain_id == "documentUploadAnswer" else "data_platform"

                        logger.debug(
                            f"多索引搜索结果 - 索引: {index}, domain_id: {domain_id}, doc_from: {doc_from}"
                        )

                        result = ESSearchResult(
                            id=hit["_id"],
                            doc_id=doc_id,
                            index=index,
                            domain_id=domain_id,
                            doc_from=doc_from,
                            file_token=doc_data.get('file_token', ""),
                            original_content=original_content,
                            div_content=div_content,
                            source=source,
                            score=hit["_score"],
                            metadata=doc_data.get('meta_data', {}),
                            alias_name=valid_indices[i]
                            if i < len(valid_indices) else "")
                        # 修改 metadata.source = doc_from
                        result.metadata["source"] = doc_from
                        all_results.append(result)

            logger.info(f"多索引搜索成功，返回 {len(all_results)} 个文档")
            return all_results

        except Exception as e:
            logger.error(f"多索引搜索失败: {str(e)}")
            return []

    async def close(self):
        """关闭连接"""
        logger.info("开始关闭ES连接")
        if self._client:
            try:
                await self._client.close()
                self._client = None
                self._initialized = False
                logger.info("ES连接已关闭")

                # 等待一小段时间确保连接完全关闭
                await asyncio.sleep(0.05)

            except Exception as e:
                logger.error(f"关闭ES连接失败: {str(e)}")
                self._client = None
                self._initialized = False

    async def get_indices(self) -> list[dict[str, Any]]:
        """获取所有索引信息"""
        logger.debug("获取所有索引信息")
        await self._ensure_connected()

        if not self._client:
            logger.error("ES客户端未连接")
            return []

        try:
            indices = [
                'personal_knowledge_base', '.infini_alert-message',
                '.infini_visualization', 'hdy_knowledge_base_v3_0422',
                '.infini_rbac-user', '.infini_alert-rule', '.infini_node',
                '.infini_layout',
                '.internal.alerts-observability.uptime.alerts-default-000001',
                'thesis_index_base', '.apm-source-map',
                '.infini_async_bulk_results-00001',
                '.slo-observability.summary-v3.temp',
                '.internal.alerts-transform.health.alerts-default-000001',
                'thesis_index_base_v2', 'thesis_index_base_v3',
                'text2sql_table', 'ai_demo',
                '.internal.alerts-observability.apm.alerts-default-000001',
                '.infini_dashboard', '.infini_requests_logging-00001',
                'internal_index_base_v2', '.infini_widget',
                'standard_index_base_v2', 'internal_index_base_v3',
                '.infini_channel',
                '.internal.alerts-security.alerts-default-000001',
                'other_index_base', '.infini_view',
                '.internal.alerts-observability.logs.alerts-default-000001',
                '.infini_configs', 'standard_index_base',
                '.infini_alert-history-000003', '.infini_alert-history-000002',
                '.infini_index', '.infini_instance',
                '.slo-observability.summary-v3', 'dev_user_knowledge_base_v1',
                '.kibana-observability-ai-assistant-kb-000001',
                '.infini_credential', '.infini_host', '.infini_task',
                'defection_index_base', '.slo-observability.sli-v3',
                'hdy_leader_index', '.infini_commands',
                '.internal.alerts-ml.anomaly-detection.alerts-default-000001',
                '.internal.alerts-observability.slo.alerts-default-000001',
                '.infini_activities-000002',
                '.internal.alerts-observability.metrics.alerts-default-000001',
                '.infini_activities-000003', 'book_index_base_v2',
                'hdy_knowledge_summary_index', 'thesis_summary_index_base',
                'dev_user_knowledge_base', '.monitoring-es-7-2025.08.13',
                '.monitoring-es-7-2025.08.14', '.monitoring-es-7-2025.08.15',
                '.monitoring-es-7-2025.08.16', '.monitoring-es-7-2025.08.17',
                '.internal.alerts-stack.alerts-default-000001',
                '.monitoring-es-7-2025.08.18', '.monitoring-es-7-2025.08.19',
                '.monitoring-kibana-7-2025.08.13', 'extract_image_index_v4',
                'book_index_base', '.infini_metrics-000005',
                '.monitoring-kibana-7-2025.08.19', '.infini_metrics-000004',
                '.monitoring-kibana-7-2025.08.18', '.infini_metrics-000007',
                '.infini_metrics-000006', '.monitoring-kibana-7-2025.08.15',
                '.monitoring-kibana-7-2025.08.14', 'book_index_base_v2_1',
                '.infini_metrics-000003', '.monitoring-kibana-7-2025.08.17',
                '.infini_logs-00001', '.monitoring-kibana-7-2025.08.16',
                '.kibana-observability-ai-assistant-conversations-000001',
                '.internal.alerts-observability.threshold.alerts-default-000001',
                'text2sql_enum_prod', '.infini_cluster', 'text2sql_enum',
                'hdy_knowledge_base_v5', 'hdy_knowledge_base_v3',
                'hdy_knowledge_base_v7', 'hdy_knowledge_base_v8',
                '.infini_rbac-role',
                '.internal.alerts-default.alerts-default-000001',
                'hdy_knowledge_base',
                '.internal.alerts-ml.anomaly-detection-health.alerts-default-000001',
                '.infini_notification', '.infini_email-server',
                '.infini_audit-logs-000002', '.infini_audit-logs-000003',
                'standard_summary_index_base_v6',
                'standard_summary_index_base_v4',
                'standard_summary_index_base_v5', 'book_index_base_v3_2',
                'standard_summary_index_base_v2', 'formula_index_base',
                'standard_summary_index_base_v3', 'internal_index_base',
                'standard_index_v1_1', 'standard_index_v1_2',
                'text2sql_table_prod', 'standard_summary_index_base',
                'hdy_leader_index_v4', 'hdy_leader_index_v2'
            ]
            logger.debug(f"获取到 {len(indices)} 个索引")
            return indices
        except Exception as e:
            logger.error(f"获取索引失败: {str(e)}")
            return []

    async def get_index_mapping(self, index: str) -> Optional[dict[str, Any]]:
        """获取索引映射"""
        logger.debug(f"获取索引 {index} 的映射信息")

        # 验证索引是否在有效范围内
        if index not in self.valid_indeces:
            logger.warning(f"索引 {index} 不在有效索引范围内: {self.valid_indeces}")
            return None

        await self._ensure_connected()

        if not self._client:
            logger.error("ES客户端未连接")
            return None

        try:
            mapping = await self._client.indices.get_mapping(index=index)
            logger.debug(f"成功获取索引 {index} 的映射")
            return mapping[index]['mappings']
        except Exception as e:
            logger.error(f"获取索引映射失败: {str(e)}")
            return None

    def get_valid_indices(self) -> list[str]:
        """获取有效索引列表"""
        return self.valid_indeces.copy()

    def is_valid_index(self, index: str) -> bool:
        """检查索引是否有效"""
        return index in self.valid_indeces

    async def __aenter__(self):
        logger.debug("进入ES服务异步上下文")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("退出ES服务异步上下文")
        await self.close()
