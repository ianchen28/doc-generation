"""
Elasticsearch搜索工具
基于底层ES服务模块，提供简洁有效的搜索接口，支持KNN向量搜索
"""

import json
from typing import Any, Dict, List, Optional

from doc_agent.core.logger import logger

from .es_discovery import ESDiscovery
from .es_service import ESSearchResult, ESService


class ESSearchTool:
    """
    Elasticsearch搜索工具类
    提供简洁有效的ES搜索功能，支持异步上下文管理器
    """

    def __init__(self,
                 hosts: list[str],
                 username: str = "",
                 password: str = "",
                 index_prefix: str = "doc_gen",
                 timeout: int = 30,
                 connections_per_node: int = 25):
        """
        初始化Elasticsearch搜索工具
        Args:
            hosts: ES服务器地址列表
            username: 用户名
            password: 密码
            index_prefix: 索引前缀
            timeout: 超时时间
            connections_per_node: 每个节点的连接数
        """
        self.hosts = hosts
        self.username = username
        self.password = password
        self.index_prefix = index_prefix
        self.timeout = timeout

        # 初始化底层服务
        self._es_service = ESService(hosts, username, password, timeout, connections_per_node)
        self._discovery = ESDiscovery(self._es_service)
        self._current_index = None
        self._indices_list = []
        self._vector_dims = 1536
        self._initialized = False
        logger.info("初始化ES搜索工具")

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            logger.info("开始初始化ES搜索工具")
            try:
                # 发现可用索引
                # 提取索引名称列表
                self._indices_list = [
                        'personal_knowledge_base', '.infini_alert-message',
                        '.infini_visualization', 'hdy_knowledge_base_v3_0422',
                        '.infini_rbac-user', '.infini_alert-rule',
                        '.infini_node', '.infini_layout',
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
                        '.infini_alert-history-000003',
                        '.infini_alert-history-000002', '.infini_index',
                        '.infini_instance', '.slo-observability.summary-v3',
                        'dev_user_knowledge_base_v1',
                        '.kibana-observability-ai-assistant-kb-000001',
                        '.infini_credential', '.infini_host', '.infini_task',
                        'defection_index_base', '.slo-observability.sli-v3',
                        'hdy_leader_index', '.infini_commands',
                        '.internal.alerts-ml.anomaly-detection.alerts-default-000001',
                        '.internal.alerts-observability.slo.alerts-default-000001',
                        '.infini_activities-000002',
                        '.internal.alerts-observability.metrics.alerts-default-000001',
                        '.infini_activities-000003', 'book_index_base_v2',
                        'hdy_knowledge_summary_index',
                        'thesis_summary_index_base', 'dev_user_knowledge_base',
                        '.monitoring-es-7-2025.08.13',
                        '.monitoring-es-7-2025.08.14',
                        '.monitoring-es-7-2025.08.15',
                        '.monitoring-es-7-2025.08.16',
                        '.monitoring-es-7-2025.08.17',
                        '.internal.alerts-stack.alerts-default-000001',
                        '.monitoring-es-7-2025.08.18',
                        '.monitoring-es-7-2025.08.19',
                        '.monitoring-kibana-7-2025.08.13',
                        'extract_image_index_v4', 'book_index_base',
                        '.infini_metrics-000005',
                        '.monitoring-kibana-7-2025.08.19',
                        '.infini_metrics-000004',
                        '.monitoring-kibana-7-2025.08.18',
                        '.infini_metrics-000007', '.infini_metrics-000006',
                        '.monitoring-kibana-7-2025.08.15',
                        '.monitoring-kibana-7-2025.08.14',
                        'book_index_base_v2_1', '.infini_metrics-000003',
                        '.monitoring-kibana-7-2025.08.17',
                        '.infini_logs-00001',
                        '.monitoring-kibana-7-2025.08.16',
                        '.kibana-observability-ai-assistant-conversations-000001',
                        '.internal.alerts-observability.threshold.alerts-default-000001',
                        'text2sql_enum_prod', '.infini_cluster',
                        'text2sql_enum', 'hdy_knowledge_base_v5',
                        'hdy_knowledge_base_v3', 'hdy_knowledge_base_v7',
                        'hdy_knowledge_base_v8', '.infini_rbac-role',
                        '.internal.alerts-default.alerts-default-000001',
                        'hdy_knowledge_base',
                        '.internal.alerts-ml.anomaly-detection-health.alerts-default-000001',
                        '.infini_notification', '.infini_email-server',
                        '.infini_audit-logs-000002',
                        '.infini_audit-logs-000003',
                        'standard_summary_index_base_v6',
                        'standard_summary_index_base_v4',
                        'standard_summary_index_base_v5',
                        'book_index_base_v3_2',
                        'standard_summary_index_base_v2', 'formula_index_base',
                        'standard_summary_index_base_v3',
                        'internal_index_base', 'standard_index_v1_1',
                        'standard_index_v1_2', 'text2sql_table_prod',
                        'standard_summary_index_base', 'hdy_leader_index_v4',
                        'hdy_leader_index_v2'
                    ]
                self._current_index = self._discovery.get_best_index()
                self._vector_dims = self._discovery.get_vector_dims()
                self._initialized = True
                logger.info(f"ES搜索工具初始化成功，使用索引: {self._current_index}")
                logger.info(f"可用索引: {self._indices_list}")
                self._initialized = True
            except Exception as e:
                logger.error(f"ES搜索工具初始化失败: {str(e)}")
                self._initialized = True  # 即使失败也标记为已初始化，避免重复尝试

    async def search(self,
                     query: str,
                     query_vector: list[float],
                     top_k: int = 10,
                     min_score: float = 0.3,
                     filters=None,
                     index: str = "*") -> list[ESSearchResult]:
        """
        执行Elasticsearch向量检索（简化版本）

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            min_score: 最小相似度分数

        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(
            f"开始向量检索，向量维度: {len(query_vector)}, top_k: {top_k}, min_score: {min_score}"
        )

        try:
            # 确保已初始化
            await self._ensure_initialized()

            # # 检查索引
            # if not self._indices_list:
            #     logger.warning("没有可用的知识库索引")
            #     return []

            # 调整向量维度
            if len(query_vector) != self._vector_dims:
                if len(query_vector) > self._vector_dims:
                    query_vector = query_vector[:self._vector_dims]
                    logger.info(f"截断向量维度到 {self._vector_dims}")
                else:
                    query_vector.extend(
                        [0.0] * (self._vector_dims - len(query_vector)))
                    logger.info(f"扩展向量维度到 {self._vector_dims}")

            # # 使用第一个索引进行搜索
            # index_to_use = self._indices_list[0]
            # logger.info(f"使用索引: {index_to_use}")

            # 执行向量搜索
            results = await self._es_service.search(
                index=index,
                query=query,  # 空查询，只使用向量
                top_k=top_k,
                query_vector=query_vector,
                filters=None)

            # 根据最小分数过滤结果
            if min_score > 0:
                original_count = len(results)
                results = [r for r in results if r.score >= min_score]
                logger.info(f"分数过滤: {original_count} -> {len(results)} 个结果")

            logger.info(f"向量检索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []

    async def search_with_hybrid(
            self,
            query: str,
            query_vector: Optional[list[float]] = None,
            top_k: int = 10,
            filters: Optional[dict[str, Any]] = None,
            config: Optional[dict[str, Any]] = None) -> list[ESSearchResult]:
        """
        执行混合搜索（文本+向量）

        Args:
            query: 搜索查询字符串
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始混合搜索，查询: {query[:50]}...")
        logger.debug(f"混合搜索参数 - top_k: {top_k}")
        if query_vector:
            logger.debug(f"查询向量维度: {len(query_vector)}")
        if filters:
            logger.debug(f"过滤条件: {filters}")

        if not query_vector:
            # 如果没有向量，回退到普通搜索
            logger.info("没有查询向量，回退到普通搜索")
            return await self.search(
                query,
                query_vector,
                top_k,
                min_score=config.get('min_score', 0.3) if config else 0.3)

        try:
            await self._ensure_initialized()

            if not self._indices_list:
                logger.warning("没有可用的知识库索引")
                return []

            # 准备查询向量
            if len(query_vector) != self._vector_dims:
                if len(query_vector) > self._vector_dims:
                    query_vector = query_vector[:self._vector_dims]
                else:
                    query_vector.extend(
                        [0.0] * (self._vector_dims - len(query_vector)))
                logger.info(f"调整向量维度到 {self._vector_dims}")

            # 使用配置参数或默认值
            if config:
                hybrid_recall_size = config.get('hybrid_recall_size', top_k)
                min_score = config.get('min_score', 0.3)
                logger.debug(
                    f"使用配置参数 - hybrid_recall_size: {hybrid_recall_size}, min_score: {min_score}"
                )
            else:
                hybrid_recall_size = top_k
                min_score = 0.3

            # 执行混合搜索
            index_to_use = self._current_index or self._indices_list[
                0] if self._indices_list else None
            if not index_to_use:
                logger.warning("没有可用的索引")
                return []

            logger.info(f"执行混合搜索，索引: {index_to_use}")
            results = await self._es_service.search(index=index_to_use,
                                                    query=query,
                                                    top_k=hybrid_recall_size,
                                                    query_vector=query_vector,
                                                    filters=filters)

            # 根据最小分数过滤结果
            if min_score > 0:
                original_count = len(results)
                results = [r for r in results if r.score >= min_score]
                logger.info(
                    f"根据最小分数 {min_score} 过滤后，剩余 {len(results)} 个结果（原始: {original_count}）"
                )

            logger.info(f"混合搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            return []

    async def search_by_file_token(
            self,
            file_token: str,
            top_k: int = 100,
            config: Optional[dict[str, Any]] = None) -> list[ESSearchResult]:
        """
        根据file_token查询文档内容
        
        Args:
            file_token: 文件token
            top_k: 返回结果数量
            config: 配置参数
            
        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始按file_token查询: {file_token}")

        await self._ensure_initialized()

        try:
            # 使用通配符索引进行查询，这样可以搜索所有索引
            index_to_use = "*"
            logger.info(f"使用通配符索引 {index_to_use} 进行file_token查询")
            results = await self._es_service.search_by_file_token(
                index=index_to_use, file_token=file_token, top_k=top_k)

            logger.info(f"file_token查询完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"file_token查询失败: {str(e)}")
            return []

    async def search_within_documents(
            self,
            query: str,
            query_vector: list[float],
            file_tokens: list[str],
            top_k: int = 10,
            min_score: float = 0.3) -> list[ESSearchResult]:
        """
        在指定文档范围内执行ES搜索（简化版本）
        
        Args:
            query: 搜索查询字符串
            query_vector: 查询向量
            file_tokens: 文档token列表，限制搜索范围
            top_k: 返回结果数量
            min_score: 最小相似度分数
            
        Returns:
            List[ESSearchResult]: 搜索结果列表
        """
        logger.info(f"开始在指定文档范围内搜索，查询: {query[:50]}...")
        logger.info(
            f"文档范围搜索参数 - file_tokens数量: {len(file_tokens)}, top_k: {top_k}, min_score: {min_score}"
        )

        # 构建文档范围过滤条件
        filters = {"doc_id": file_tokens}

        # 对于文档范围搜索，使用通配符索引以确保能找到所有相关文档
        logger.info("🔍 使用通配符索引进行文档范围搜索，确保覆盖所有索引")

        # 执行搜索
        results = await self._es_service.search(
            index="*",  # 使用通配符索引
            query=query,
            top_k=top_k,
            query_vector=query_vector,
            filters=filters)

        # 根据最小分数过滤结果
        if min_score > 0:
            original_count = len(results)
            results = [r for r in results if r.score >= min_score]
            logger.info(f"分数过滤: {original_count} -> {len(results)} 个结果")

        logger.info(f"文档范围搜索完成，返回 {len(results)} 个结果")
        return results

    async def get_available_indices(self) -> list[str]:
        """获取可用索引列表"""
        await self._ensure_initialized()
        logger.debug(f"获取可用索引列表，共 {len(self._indices_list)} 个")
        return self._indices_list.copy()

    async def get_current_index(self) -> Optional[str]:
        """获取当前使用的索引"""
        await self._ensure_initialized()
        logger.debug(f"获取当前索引: {self._current_index}")
        return self._current_index

    async def __aenter__(self):
        """异步上下文管理器入口"""
        logger.debug("进入ES搜索工具异步上下文")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，自动关闭连接"""
        logger.debug("退出ES搜索工具异步上下文")
        await self.close()

    async def close(self):
        """关闭连接"""
        logger.info("关闭ES搜索工具连接")
        try:
            await self._es_service.close()
            self._initialized = False

            # 从全局注册表移除（如果存在）
            try:
                from . import unregister_es_tool
                unregister_es_tool(self)
                logger.debug("从全局注册表移除ES工具")
            except ImportError:
                # 如果导入失败，说明不在测试环境中，忽略
                logger.debug("不在测试环境中，跳过注册表移除")
                pass
        except Exception as e:
            logger.error(f"关闭ES搜索工具时出错: {e}")

    # 兼容性方法，用于工具工厂
    async def _discover_available_indices(self):
        """发现可用索引（兼容性方法）"""
        await self._ensure_initialized()
        logger.debug("调用兼容性方法 _discover_available_indices")
        return self._indices_list

    @property
    def _available_indices(self):
        """获取可用索引（兼容性属性）"""
        logger.debug("调用兼容性属性 _available_indices")
        return self._indices_list
