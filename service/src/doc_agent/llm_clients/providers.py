# service/src/doc_agent/llm_clients/providers.py
import json
import pprint
import re
import time
from collections.abc import AsyncGenerator, Generator

import httpx

from doc_agent.core.logger import logger
from doc_agent.llm_clients.base import BaseOutputParser, LLMClient
from doc_agent.utils.timing import CodeTimer


class ReasoningParser(BaseOutputParser):
    """
    推理输出解析器
    去除模型响应中的推理过程，只保留最终答案
    """

    def __init__(self, reasoning: bool = False):
        self.reasoning = reasoning

    def parse(self, response: str) -> str:
        if self.reasoning:
            # 用正则表达式去除 <think> 和 </think> 之间的内容
            response = re.sub(r'<think>.*?</think>',
                              '',
                              response,
                              flags=re.DOTALL)
            return response.strip()
        else:
            return response.strip()


class GeminiClient(LLMClient):

    def __init__(self,
                 base_url: str,
                 model_name: str = "gemini-1.5-pro-latest",
                 api_key: str = None,
                 reasoning: bool = False,
                 timeout: float = 60.0):
        """
        初始化Gemini客户端
        Args:
            api_key: Gemini API密钥
            model: 模型名称，默认为gemini-1.5-pro-latest
            base_url: API基础URL，如果为None则使用默认URL
            reasoning: 是否启用推理模式
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.reasoning = reasoning
        self.timeout = timeout
        self.parser = ReasoningParser(reasoning=reasoning)
        # 如果提供了base_url，使用它；否则使用默认URL
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用Gemini API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Returns:
            str: 模型响应的内容
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }

            # 发送请求 - 修复 Gemini API URL
            # ChatAI API 使用不同的端点格式
            if "chataiapi.com" in self.base_url:
                # ChatAI API 格式
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                # 使用 OpenAI 兼容格式
                data = {
                    "model": self.model_name,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            else:
                # 标准 Gemini API 格式
                url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
                headers = {}
                # 使用 Gemini 格式
                data = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                }

            logger.debug(
                f"Gemini API request:\nURL: {url}\nData: {pprint.pformat(data)}"
            )

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()

                result = response.json()

                # 提取响应内容 - 支持两种格式
                if "chataiapi.com" in self.base_url:
                    # ChatAI API 返回 OpenAI 兼容格式
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        logger.debug(f"🔍 ChatAI原始响应: '{content}'")
                        parsed_content = self.parser.parse(content)
                        logger.debug(f"🔍 ChatAI解析后: '{parsed_content}'")
                        return parsed_content
                    else:
                        raise ValueError(
                            "No response content received from ChatAI API")
                else:
                    # 标准 Gemini API 格式
                    if "candidates" in result and len(
                            result["candidates"]) > 0:
                        content = result["candidates"][0]["content"]["parts"][
                            0]["text"]
                        logger.debug(f"🔍 Gemini原始响应: '{content}'")
                        parsed_content = self.parser.parse(content)
                        logger.debug(f"🔍 Gemini解析后: '{parsed_content}'")
                        return parsed_content
                    else:
                        raise ValueError(
                            "No response content received from Gemini API")

        except Exception as e:
            logger.error(f"Gemini API调用失败: {str(e)}")
            raise Exception(f"Gemini API调用失败: {str(e)}") from e

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        异步流式调用Gemini API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Yields:
            str: 模型响应的文本片段
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            if "chataiapi.com" in self.base_url:
                # ChatAI API 格式
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                data = {
                    "model": self.model_name,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True  # 启用流式输出
                }
            else:
                # 标准 Gemini API 格式
                url = f"{self.base_url}/{self.model_name}:streamGenerateContent?key={self.api_key}"
                headers = {}
                data = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                }

            logger.debug(
                f"Gemini 流式API请求:\nURL: {url}\nData: {pprint.pformat(data)}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST",
                                         url,
                                         json=data,
                                         headers=headers) as response:
                    response.raise_for_status()

                    if "chataiapi.com" in self.base_url:
                        # ChatAI API 流式格式
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]  # 移除 "data: " 前缀
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    if "choices" in chunk and len(
                                            chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get(
                                            "delta", {})
                                        if "content" in delta and delta[
                                                "content"]:
                                            yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
                    else:
                        # 标准 Gemini API 流式格式
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    if "candidates" in chunk and len(
                                            chunk["candidates"]) > 0:
                                        content = chunk["candidates"][0][
                                            "content"]["parts"][0]["text"]
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue

        except Exception as e:
            logger.error(f"Gemini 流式API调用失败: {str(e)}")
            raise Exception(f"Gemini 流式API调用失败: {str(e)}") from e


class DeepSeekClient(LLMClient):

    def __init__(self,
                 base_url: str,
                 api_key: str,
                 model_name: str,
                 reasoning: bool = False,
                 timeout: float = 60.0):
        """
        初始化DeepSeek客户端
        Args:
            api_key: DeepSeek API密钥
            model: 模型名称，默认为deepseek-chat
            reasoning: 是否启用推理模式
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.model_name = model_name
        self.reasoning = reasoning
        self.timeout = timeout
        self.parser = ReasoningParser(reasoning=reasoning)
        self.base_url = base_url.rstrip('/')

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用DeepSeek API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Returns:
            str: 模型响应的内容
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            logger.debug(
                f"DeepSeek API request:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()

                result = response.json()

                # 提取响应内容
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return self.parser.parse(content)
                else:
                    raise ValueError(
                        "No response content received from DeepSeek API")

        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            raise Exception(f"DeepSeek API调用失败: {str(e)}") from e

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        异步流式调用DeepSeek API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Yields:
            str: 模型响应的文本片段
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True  # 启用流式输出
            }

            logger.debug(
                f"DeepSeek 流式API请求:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST",
                                         url,
                                         json=data,
                                         headers=headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and len(
                                        chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get(
                                        "delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"DeepSeek 流式API调用失败: {str(e)}")
            raise Exception(f"DeepSeek 流式API调用失败: {str(e)}") from e


class MoonshotClient(LLMClient):

    def __init__(self,
                 base_url: str,
                 api_key: str,
                 model_name: str,
                 reasoning: bool = False,
                 timeout: float = 180.0):
        """
        初始化Moonshot客户端
        Args:
            base_url: Moonshot API地址
            api_key: API密钥
            model: 模型名称
            reasoning: 是否启用推理模式
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.reasoning = reasoning
        self.timeout = timeout
        self.parser = ReasoningParser(reasoning=reasoning)

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用Moonshot API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Returns:
            str: 模型响应的内容
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据 - 使用OpenAI兼容格式
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            logger.debug(
                f"Moonshot API request:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 创建自定义的httpx客户端，避免proxies参数问题
            http_client = httpx.Client(timeout=self.timeout)

            with http_client as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()

                result = response.json()

                # 提取响应内容
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.debug(f"🔍 Moonshot原始响应: '{content}'")
                    parsed_content = self.parser.parse(content)
                    logger.debug(f"🔍 Moonshot解析后: '{parsed_content}'")
                    return parsed_content
                else:
                    raise ValueError(
                        "No response content received from Moonshot API")

        except Exception as e:
            logger.error(f"Moonshot API调用失败: {str(e)}")
            raise Exception(f"Moonshot API调用失败: {str(e)}") from e

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        异步流式调用Moonshot API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Yields:
            str: 模型响应的文本片段
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据 - 使用OpenAI兼容格式
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True  # 启用流式输出
            }

            logger.debug(
                f"Moonshot 流式API请求:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST",
                                         url,
                                         json=data,
                                         headers=headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and len(
                                        chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get(
                                        "delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Moonshot 流式API调用失败: {str(e)}")
            raise Exception(f"Moonshot 流式API调用失败: {str(e)}") from e


class InternalLLMClient(LLMClient):

    def __init__(self,
                 base_url: str,
                 api_key: str,
                 model_name: str,
                 reasoning: bool = False,
                 timeout: float = 180.0):
        """
        初始化内部模型客户端
        Args:
            base_url: 内部API地址
            api_key: API密钥
            model: 模型名称
            reasoning: 是否启用推理模式
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.reasoning = reasoning
        self.timeout = timeout
        self.parser = ReasoningParser(reasoning=reasoning)

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用内部模型API

        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等

        Returns:
            str: 模型响应的内容
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 5000)

            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            logger.debug(
                f"Internal API request:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            } if self.api_key != "EMPTY" else {}

            with CodeTimer("llm_call <timer>"):
                with httpx.Client(
                        timeout=self.timeout) as client:  # 使用配置的timeout
                    response = client.post(url, json=data, headers=headers)
                    response.raise_for_status()

                    result = response.json()

                    # 提取响应内容
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return self.parser.parse(content)
                    else:
                        raise ValueError(
                            "No response content received from Internal API")

        except Exception as e:
            logger.error(f"Internal API调用失败: {str(e)}")
            raise Exception(f"Internal API调用失败: {str(e)}") from e

    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        同步流式调用内部模型API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Yields:
            str: 模型响应的文本片段
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True  # 启用流式输出
            }

            logger.debug(
                f"Internal 同步流式API请求:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            } if self.api_key != "EMPTY" else {}

            with httpx.Client(timeout=self.timeout) as client:  # 使用配置的timeout
                with client.stream("POST", url, json=data,
                                   headers=headers) as response:
                    response.raise_for_status()

                    for line in response.iter_lines():
                        # line 已经是字符串，不需要解码
                        line_str = line
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and len(
                                        chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get(
                                        "delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Internal 同步流式API调用失败: {str(e)}")
            raise Exception(f"Internal 同步流式API调用失败: {str(e)}") from e

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        异步流式调用内部模型API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数，如temperature, max_tokens等
        Yields:
            str: 模型响应的文本片段
        """
        try:
            # 获取可选参数
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1000)

            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True  # 启用流式输出
            }

            logger.debug(
                f"Internal 流式API请求:\nURL: {self.base_url}/chat/completions\nData: {pprint.pformat(data)}"
            )

            # 发送请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            } if self.api_key != "EMPTY" else {}

            async with httpx.AsyncClient(
                    timeout=self.timeout) as client:  # 使用配置的timeout
                async with client.stream("POST",
                                         url,
                                         json=data,
                                         headers=headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and len(
                                        chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get(
                                        "delta", {})
                                    if "content" in delta and delta["content"]:
                                        content = delta["content"]
                                        # 调试：检查内容是否为 Unicode 编码
                                        if content.startswith('\\u'):
                                            logger.debug(
                                                f"检测到 Unicode 编码内容: {content}")
                                            # 尝试解码 Unicode 转义序列
                                            try:
                                                decoded_content = content.encode(
                                                    'utf-8').decode(
                                                        'unicode_escape')
                                                logger.debug(
                                                    f"解码后内容: {decoded_content}"
                                                )
                                                yield decoded_content
                                            except Exception as e:
                                                logger.warning(
                                                    f"Unicode 解码失败: {e}, 使用原始内容"
                                                )
                                                yield content
                                        else:
                                            yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Internal 流式API调用失败: {str(e)}")
            raise Exception(f"Internal 流式API调用失败: {str(e)}") from e


class RerankerClient(LLMClient):

    def __init__(self, base_url: str, api_key: str):
        """
        初始化Reranker客户端
        Args:
            base_url: Reranker API地址
            api_key: API密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def invoke(self, prompt: str, **kwargs) -> dict:
        """
        调用Reranker API
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
        Returns:
            dict: 重排序结果
        """
        try:
            documents = kwargs.get("documents", [])
            doc_objs = [{"text": doc} for doc in documents]
            size = kwargs.get("size", len(doc_objs))
            data = {"query": prompt, "doc_list": doc_objs, "size": size}
            url = f"{self.base_url}"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            } if self.api_key != "EMPTY" else {}

            logger.debug(
                f"Reranker API request:\nURL: {url}\nData: {pprint.pformat(data)}"
            )

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Reranker API调用失败: {str(e)}")
            raise Exception(f"Reranker API调用失败: {str(e)}") from e

    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Reranker客户端不支持流式输出，返回空生成器
        """
        logger.warning("Reranker客户端不支持流式输出，返回空结果")
        return
        yield  # 这行永远不会执行，只是为了满足类型注解

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        Reranker客户端不支持流式输出
        """
        raise NotImplementedError("Reranker客户端不支持流式输出")
        yield  # 这行永远不会执行，只是为了满足类型注解


class EmbeddingClient(LLMClient):

    def __init__(self, base_url: str, api_key: str):
        """
        初始化Embedding客户端
        Args:
            base_url: Embedding API地址
            api_key: API密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def invoke(self, prompt: str, **kwargs) -> str:
        """
        调用Embedding API
        Args:
            prompt: 输入文本
            **kwargs: 其他参数
        Returns:
            str: 嵌入向量（JSON格式）
        """
        try:
            # 构建请求数据 - 修复字段名
            data = {"inputs": prompt, "model": kwargs.get("model", "gte-qwen")}

            logger.debug(
                f"Embedding API request:\nURL: {self.base_url}\nData: {pprint.pformat(data)}"
            )

            # 发送请求 - 直接使用根端点，因为测试显示它工作正常
            url = f"{self.base_url}"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            } if self.api_key != "EMPTY" else {}

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()
                return str(result)  # 返回嵌入向量

        except Exception as e:
            logger.error(f"Embedding API调用失败: {str(e)}")
            raise Exception(f"Embedding API调用失败: {str(e)}") from e

    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """
        Embedding客户端不支持流式输出，返回空生成器
        """
        logger.warning("Embedding客户端不支持流式输出，返回空结果")
        return
        yield  # 这行永远不会执行，只是为了满足类型注解

    async def astream(self, prompt: str,
                      **kwargs) -> AsyncGenerator[str, None]:
        """
        Embedding客户端不支持流式输出
        """
        raise NotImplementedError("Embedding客户端不支持流式输出")
        yield  # 这行永远不会执行，只是为了满足类型注解


if __name__ == "__main__":
    client = InternalLLMClient(base_url="http://10.238.130.28:10004/v1",
                               api_key="EMPTY",
                               model_name="hdy_model",
                               reasoning=True)
    print(client.invoke("你好"))
