#!/usr/bin/env python3
"""
LLM客户端模块 - 支持多个LLM服务提供商
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
import openai
from loguru import logger # type: ignore


class LLMProvider(Enum):
    """LLM服务提供商"""
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """LLM配置"""
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 3000
    timeout: int = 90  # 增加超时时间
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    usage: Dict[str, int]
    model: str
    provider: str
    response_time: float
    success: bool = True
    error: Optional[str] = None


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, config: LLMConfig, provider: LLMProvider = LLMProvider.DEEPSEEK):
        self.config = config
        self.provider = provider
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_response_time": 0.0
        }
        self.response_times = []
        
        # 根据提供商初始化客户端
        if provider == LLMProvider.DEEPSEEK:
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url
            )
        elif provider == LLMProvider.OPENROUTER:
            self.client = openai.AsyncOpenAI(
                api_key=config.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        else:
            self.client = openai.AsyncOpenAI(api_key=config.api_key)
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """生成文本"""
        start_time = time.time()
        self.usage_stats["total_requests"] += 1
        
        try:
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # 调用参数
            params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
                **kwargs
            }
            
            # 针对不同提供商的特殊处理
            if self.provider == LLMProvider.OPENROUTER:
                # OpenRouter需要特殊的headers
                params["headers"] = {
                    "HTTP-Referer": "https://github.com/research-agent",
                    "X-Title": "Research Multi-Agent System"
                }
            
            # 执行调用
            response = await self._call_with_retry(params)
            
            # 处理响应
            content = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else {}
            response_time = time.time() - start_time
            
            # 更新统计
            self.usage_stats["successful_requests"] += 1
            self.usage_stats["total_tokens"] += usage.get("total_tokens", 0)
            self.response_times.append(response_time)
            self._update_average_response_time()
            
            logger.info(f"LLM调用成功: {self.provider.value}/{self.config.model}, tokens: {usage.get('total_tokens', 0)}, time: {response_time:.2f}s")
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=self.config.model,
                provider=self.provider.value,
                response_time=response_time
            )
            
        except Exception as e:
            self.usage_stats["failed_requests"] += 1
            logger.error(f"LLM调用失败 [{self.provider.value}/{self.config.model}]: {e}")
            
            return LLMResponse(
                content="",
                usage={},
                model=self.config.model,
                provider=self.provider.value,
                response_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    async def _call_with_retry(self, params: Dict[str, Any]):
        """带重试的API调用"""
        headers = params.pop("headers", {})
        
        for attempt in range(self.config.max_retries):
            try:
                # 特殊处理OpenRouter的headers
                if self.provider == LLMProvider.OPENROUTER and headers:
                    # 为OpenRouter设置额外的headers
                    import httpx
                    async with httpx.AsyncClient() as client:
                        api_response = await client.post(
                            f"{self.config.base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.config.api_key}",
                                "Content-Type": "application/json",
                                **headers
                            },
                            json=params,
                            timeout=self.config.timeout
                        )
                        response_data = api_response.json()
                        
                        # 转换为OpenAI格式的响应对象
                        class MockResponse:
                            def __init__(self, data):
                                self.choices = [type('Choice', (), {
                                    'message': type('Message', (), {
                                        'content': data['choices'][0]['message']['content']
                                    })()
                                })()]
                                usage_data = data.get('usage', {})
                                self.usage = type('Usage', (), usage_data)()
                                if hasattr(self.usage, '__dict__'):
                                    self.usage.model_dump = lambda: usage_data
                        
                        return MockResponse(response_data)
                else:
                    # 标准OpenAI客户端调用
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(**params),
                        timeout=self.config.timeout
                    )
                    return response
                
            except asyncio.TimeoutError:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.config.max_retries})")
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"请求超时，已重试{self.config.max_retries}次")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise e
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
    
    async def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成结构化响应"""
        full_prompt = f"""
{prompt}

请按照以下JSON格式返回响应：
{json.dumps(schema, indent=2, ensure_ascii=False)}

确保返回的是有效的JSON格式。
"""
        
        response = await self.generate_text(full_prompt, system_prompt)
        
        if not response.success:
            return {"error": response.error}
        
        try:
            # 尝试解析JSON
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取JSON部分
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            try:
                result = json.loads(content.strip())
                return result
            except json.JSONDecodeError:
                return {"error": "无法解析为JSON格式", "raw_content": response.content}
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            logger.info(f"测试LLM连接: {self.provider.value}/{self.config.model}")
            response = await self.generate_text("Hello, please reply 'Connected successfully' or '连接成功'")
            is_connected = response.success and ("Connected successfully" in response.content or "连接成功" in response.content)
            
            if is_connected:
                logger.info(f"✅ LLM连接测试成功: {self.provider.value}/{self.config.model}")
            else:
                logger.error(f"❌ LLM连接测试失败: {self.provider.value}/{self.config.model}, 响应: {response.content[:100]}")
                
            return is_connected
        except Exception as e:
            logger.error(f"❌ LLM连接测试异常: {self.provider.value}/{self.config.model}: {e}")
            return False
    
    def _update_average_response_time(self):
        """更新平均响应时间"""
        if self.response_times:
            self.usage_stats["average_response_time"] = sum(self.response_times) / len(self.response_times)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self.usage_stats.copy()
    
    def reset_stats(self):
        """重置统计"""
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_response_time": 0.0
        }
        self.response_times = []


class LLMClientManager:
    """LLM客户端管理器"""
    
    def __init__(self):
        self.clients: Dict[str, LLMClient] = {}
        self.primary_client: Optional[LLMClient] = None
    
    def add_client(self, name: str, client: LLMClient, is_primary: bool = False):
        """添加客户端"""
        self.clients[name] = client
        if is_primary or not self.primary_client:
            self.primary_client = client
    
    async def generate_text(self, prompt: str, client_name: Optional[str] = None, **kwargs) -> LLMResponse:
        """生成文本（支持客户端选择）"""
        client = self.clients.get(client_name) if client_name else self.primary_client
        if not client:
            raise ValueError("没有可用的LLM客户端")
        
        return await client.generate_text(prompt, **kwargs)
    
    async def generate_with_fallback(self, prompt: str, **kwargs) -> LLMResponse:
        """带故障转移的生成（自动尝试所有客户端）"""
        for name, client in self.clients.items():
            try:
                response = await client.generate_text(prompt, **kwargs)
                if response.success:
                    return response
            except Exception as e:
                logger.warning(f"客户端 {name} 失败: {e}")
                continue
        
        raise Exception("所有LLM客户端都不可用")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有客户端统计"""
        return {name: client.get_usage_stats() for name, client in self.clients.items()}


def create_llm_client(
    api_key: str,
    model: str = "deepseek-chat",
    base_url: str = "https://api.deepseek.com/v1",
    provider: LLMProvider = LLMProvider.DEEPSEEK,
    **kwargs
) -> LLMClient:
    """创建LLM客户端"""
    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        **kwargs
    )
    return LLMClient(config, provider)


def create_multi_llm_manager(configs: List[Dict[str, Any]]) -> LLMClientManager:
    """创建多LLM管理器"""
    manager = LLMClientManager()
    
    for i, config in enumerate(configs):
        provider = LLMProvider(config.get("provider", "deepseek"))
        client = create_llm_client(
            api_key=config["api_key"],
            model=config.get("model", "deepseek-chat"),
            base_url=config.get("base_url", "https://api.deepseek.com/v1"),
            provider=provider
        )
        
        name = config.get("name", f"client_{i}")
        is_primary = config.get("is_primary", i == 0)
        manager.add_client(name, client, is_primary)
    
    return manager


# 导出主要类和函数
__all__ = [
    "LLMClient",
    "LLMClientManager", 
    "LLMConfig",
    "LLMResponse",
    "LLMProvider",
    "create_llm_client",
    "create_multi_llm_manager"
]
