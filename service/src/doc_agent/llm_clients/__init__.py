"""LLM客户端模块"""

from pprint import pformat
from doc_agent.core.logger import logger

from doc_agent.core.config import settings

from .base import LLMClient
from .providers import (
    DeepSeekClient,
    EmbeddingClient,
    GeminiClient,
    InternalLLMClient,
    MoonshotClient,
    RerankerClient,
)


def get_llm_client(model_key: str = "qwen_2_5_235b_a22b") -> LLMClient:
    """
    工厂函数，根据配置创建并返回一个LLM客户端实例
    Args:
        model_key: 模型键名，从config.yaml的supported_models中获取，
            默认为qwen_2_5_235b_a22b
    Returns:
        LLMClient: 相应的客户端实例
    """
    logger.info(f"🔧 开始创建LLM客户端: {model_key}")

    model_config = settings.get_model_config(model_key)
    if not model_config:
        logger.error(f"❌ 模型配置未找到: {model_key}")
        raise ValueError(f"Model {model_key} not found in configuration")

    try:
        logger.debug(f"Model configuration:\n{pformat(model_config.__dict__)}")
    except Exception:
        logger.debug("Model configuration: <unprintable>")

    # 根据模型类型创建相应的客户端
    if model_config.type == "enterprise_generate":
        # 企业内网模型
        logger.info(f"🏢 创建企业内网模型客户端: {model_config.model_name}")
        return InternalLLMClient(base_url=model_config.url,
                                 api_key=model_config.api_key,
                                 model_name=model_config.model_name,
                                 reasoning=model_config.reasoning)
    elif model_config.type == "external_generate":
        # 外部模型
        if "gemini" in model_config.model_name.lower():
            logger.info(f"🤖 创建Gemini客户端: {model_config.model_name}")
            return GeminiClient(base_url=model_config.url,
                                api_key=model_config.api_key,
                                model_name=model_config.model_name,
                                reasoning=model_config.reasoning)
        elif "deepseek" in model_config.model_name.lower():
            logger.info(f"🔍 创建DeepSeek客户端: {model_config.model_name}")
            return DeepSeekClient(base_url=model_config.url,
                                  api_key=model_config.api_key,
                                  model_name=model_config.model_name,
                                  reasoning=model_config.reasoning)
        elif ("moonshot" in model_config.model_name.lower()
              or "kimi" in model_config.name.lower()):
            logger.info(f"🌙 创建Moonshot客户端: {model_config.model_name}")
            return MoonshotClient(base_url=model_config.url,
                                  api_key=model_config.api_key,
                                  model_name=model_config.model_name,
                                  reasoning=model_config.reasoning)
        else:
            logger.error(f"❌ 未知的模型类型: {model_config.type}")
            raise ValueError(f"Unknown model type: {model_config.type}")
    else:
        logger.error(f"❌ 未知的模型类型: {model_config.type}")
        raise ValueError(f"Unknown model type: {model_config.type}")


def get_reranker_client() -> RerankerClient:
    """获取Reranker客户端"""
    logger.info("🔧 开始创建Reranker客户端")

    reranker_config = settings.get_model_config("reranker")
    if reranker_config:
        logger.info(f"✅ 创建Reranker客户端: {reranker_config.model_name}")
        return RerankerClient(base_url=reranker_config.url,
                              api_key=reranker_config.api_key)
    else:
        logger.error("❌ Reranker模型配置未找到")
        raise ValueError("Reranker model not found in configuration")


def get_embedding_client() -> EmbeddingClient:
    """获取Embedding客户端"""
    logger.info("🔧 开始创建Embedding客户端")

    embedding_config = settings.get_model_config("gte_qwen")
    if embedding_config:
        logger.info(f"✅ 创建Embedding客户端: {embedding_config.model_name}")
        return EmbeddingClient(base_url=embedding_config.url,
                               api_key=embedding_config.api_key)
    else:
        logger.error("❌ Embedding模型配置未找到")
        raise ValueError("Embedding model not found in configuration")
