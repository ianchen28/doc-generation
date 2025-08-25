import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

env = os.getenv("ENV", "dev")


class NacosConfig:
    namespace = os.getenv('NACOS_NAMESPACE', 'hdec-llm')
    group = os.getenv('NACOS_GROUP', 'DEFAULT_GROUP')
    data_id = os.getenv('NACOS_DATA_ID', 'doc-generation.json')


nacos_config = NacosConfig()

SERVER_ADDRESSES = os.getenv('NACOS_SERVER_ADDRESSES',
                             'nacos.common.svc.cluster.local:8848')


def resolve_placeholders(data):
    """
    递归解析配置中的 ${VARIABLE_NAME} 占位符
    从环境变量中获取实际值进行替换
    """
    if isinstance(data, str):
        # 使用正则表达式查找并替换 ${VARIABLE_NAME} 占位符
        pattern = r'\$\{([^}]+)\}'

        def replace_placeholder(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            else:
                # 环境变量不存在时的处理策略
                return match.group(0)  # 保持原占位符

        return re.sub(pattern, replace_placeholder, data)

    elif isinstance(data, dict):
        # 递归处理字典
        return {
            key: resolve_placeholders(value)
            for key, value in data.items()
        }

    elif isinstance(data, list):
        # 递归处理列表
        return [resolve_placeholders(item) for item in data]

    else:
        # 其他类型直接返回
        return data


try:
    if env in ['prod', 'test']:
        import nacos
        client = nacos.NacosClient(SERVER_ADDRESSES,
                                   namespace=nacos_config.namespace)
        raw_config_str = client.get_config(nacos_config.data_id,
                                           nacos_config.group)

        # 解析JSON
        raw_config_data = json.loads(raw_config_str)

        # 处理占位符替换
        config_file = resolve_placeholders(raw_config_data)
    else:
        config_file = {}
except Exception as e:
    config_file = {}

# 默认配置值 - 当Nacos配置为空或获取失败时使用
DEFAULT_CONFIG = {
    "redis": {
        "mode": "single",
        "single": {
            "host": "10.215.149.74",
            "port": 26379,
            "db": 0,
            "password": "xJrhp*4mnHxbBWN2grqq"
        },
        "cluster": {
            "nodes": ["10.215.149.74:6380", "10.215.149.75:6380"],
            "max_redirects": 3,
            "password": "xJrhp*4mnHxbBWN2grqq",
            "timeout": 35000,
            "pool": {
                "max_active": 20,
                "max_idle": 10,
                "min_idle": 2,
                "max_wait": 5000
            },
            "refresh": {
                "adaptive": True,
                "period": 30000
            },
            "shutdown_timeout": 10000,
            "retry": {
                "attempts": 3,
                "interval": 5000
            },
            "concurrency": 1
        }
    },
    "supported_models": {
        "hdy_model": {
            "name": "HDY模型",
            "type": "enterprise_generate",
            "model_id": "Qwen3-235B-new",
            "url": "http://10.238.130.28:10004/v1",
            "reasoning": False,
            "description": "基于 qwen-32b 精调的行业知识问答模型",
            "api_key": "EMPTY"
        },
        "qwen_2_5_235b_a22b": {
            "name": "Qwen3-235B-A22B-new (推理)",
            "type": "enterprise_generate",
            "model_id": "hdy_model",
            "url": "http://10.238.130.30:11242/v1",
            "reasoning": True,
            "description": "千问 235b 最强推理模型量化版",
            "api_key": "EMPTY"
        },
        "qwen_72b": {
            "name": "Qwen2.5-72B (基础)",
            "type": "enterprise_generate",
            "model_id": "Qwen2.5-72B-new",
            "url": "http://10.238.130.16:23215/v1",
            "reasoning": False,
            "description": "千问 72b 大模型",
            "api_key": "EMPTY"
        },
        "reranker": {
            "name": "reranker",
            "type": "enterprise_reranker",
            "model_id": "reranker",
            "url": "http://10.218.108.239:39939/reranker",
            "description": "reranker - 重排序模型，擅长重排序任务",
            "api_key": "EMPTY"
        },
        "gte_qwen": {
            "name": "gte_qwen",
            "type": "enterprise_embedding",
            "model_id": "gte_qwen",
            "url": "http://10.215.58.199:13037/embed",
            "description": "gte_qwen - 嵌入模型",
            "api_key": "EMPTY"
        }
    },
    "elasticsearch": {
        "hosts": [
            "https://10.238.130.43:9200", "https://10.238.130.44:9200",
            "https://10.238.130.45:9200"
        ],
        "port":
        9200,
        "scheme":
        "https",
        "username":
        "devops",
        "password":
        "mQxMg8wEKnN1WExz",
        "verify_certs":
        False,
        "index_prefix":
        "doc_gen",
        "timeout":
        30,
        "max_retries":
        3,
        "retry_on_timeout":
        True,
        "connections_per_node":
        25  # 每个节点的连接数（推荐配置）
    },
    "tavily": {
        "api_key": "${TAVILY_API_KEY}",
        "search_depth": "advanced",
        "max_results": 6
    },
    "document_generation": {
        "es_search": {
            "vector_recall_size": 20,
            "hybrid_recall_size": 15,
            "rerank_size": 8,
            "min_score": 0.3
        },
        "document_length": {
            "total_target_words": 8000,
            "chapter_target_words": 1600,
            "chapter_count": 5,
            "min_chapter_words": 800,
            "max_chapter_words": 2500
        },
        "generation_complexity": {
            "level": "fast",
            "fast": {
                "initial_search_queries": 2,
                "chapter_search_queries": 2,
                "max_search_results": 3,
                "data_truncate_length": 5000,
                "max_chapters": 2,
                "chapter_target_words": 600,
                "total_target_words": 1200,
                "vector_recall_size": 10,
                "hybrid_recall_size": 8,
                "rerank_size": 5,
                "use_simplified_prompts": True,
                "llm_timeout": 120,
                "max_retries": 2
            },
            "standard": {
                "initial_search_queries": 5,
                "chapter_search_queries": 3,
                "max_search_results": 5,
                "data_truncate_length": 10000,
                "max_chapters": 5,
                "chapter_target_words": 1600,
                "total_target_words": 8000,
                "vector_recall_size": 20,
                "hybrid_recall_size": 15,
                "rerank_size": 8,
                "use_simplified_prompts": False,
                "llm_timeout": 180,
                "max_retries": 5
            },
            "comprehensive": {
                "initial_search_queries": 8,
                "chapter_search_queries": 5,
                "max_search_results": 10,
                "data_truncate_length": -1,
                "max_chapters": -1,
                "chapter_target_words": 2000,
                "total_target_words": 15000,
                "vector_recall_size": 30,
                "hybrid_recall_size": 20,
                "rerank_size": 12,
                "use_simplified_prompts": False,
                "llm_timeout": 300,
                "max_retries": 8
            }
        }
    },
    "agent_config": {
        "default_llm": "qwen_2_5_235b_a22b",
        "task_planner": {
            "name": "task_planner",
            "description": "任务规划器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        },
        "retriever": {
            "name": "retriever",
            "description": "检索器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        },
        "executor": {
            "name": "executor",
            "description": "执行器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        },
        "composer": {
            "name": "composer",
            "description": "写作器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.8,
            "max_tokens": 3000,
            "timeout": 300,
            "retry_count": 8,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 300
            }
        },
        "validator": {
            "name": "validator",
            "description": "验证器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.6,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        },
        "knowledge_retriever": {
            "name": "knowledge_retriever",
            "description": "知识检索器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        },
        "hybrid_retriever": {
            "name": "hybrid_retriever",
            "description": "混合检索器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.7,
            "max_tokens": 2000,
            "timeout": 240,
            "retry_count": 6,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 240
            }
        },
        "content_composer": {
            "name": "content_composer",
            "description": "内容创作器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.8,
            "max_tokens": 4000,
            "timeout": 360,
            "retry_count": 10,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 360
            }
        },
        "content_checker": {
            "name": "content_checker",
            "description": "内容检查器",
            "provider": "qwen_2_5_235b_a22b",
            "model": "qwen_2_5_235b_a22b",
            "temperature": 0.6,
            "max_tokens": 2000,
            "timeout": 180,
            "retry_count": 5,
            "enable_logging": True,
            "extra_params": {
                "connect_timeout": 60,
                "read_timeout": 180
            }
        }
    },
    "search_config": {
        "max_search_rounds": 1,
        "max_queries": 1,
        "max_results_per_query": 3
    },
    "storage": {
        "base_url": "https://copilot.test.hcece.net"
    },
    "logging": {
        "level": "INFO",
        "file_path": "logs/app.log",
        "rotation": "10 MB",
        "retention": "7 days"
    },
    "log_dir": "logs",
    "output_dir": "output",
    "server": {
        "max_concurrent_tasks": 10,
        "workers": 8,
        "host": "0.0.0.0",
        "port": 8081
    }
}

# 如果配置文件为空，使用默认配置
if not config_file:
    config_file = DEFAULT_CONFIG
