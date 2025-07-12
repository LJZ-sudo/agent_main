#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化LLM客户端 - 用于Agent系统
避免复杂依赖，提供基础LLM功能
"""

import asyncio
import time
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class SimpleLLMClient:
    """简化LLM客户端"""
    
    def __init__(self, config=None):
        self.config = config
        self.initialized = False
        
    async def initialize(self):
        """初始化客户端"""
        logger.info("初始化简化LLM客户端...")
        self.initialized = True
        return True
    
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天完成接口"""
        if not self.initialized:
            await self.initialize()
        
        await asyncio.sleep(0.5)
        
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if "文献" in user_message:
            response_content = f"针对您的文献需求：{user_message}，我建议从以下方面研究：1. 理论基础 2. 最新进展 3. 应用案例。这是简化响应，实际环境将提供详细分析。"
        elif "实验" in user_message:
            response_content = f"关于实验设计：{user_message}，建议：1. 确定假设 2. 设计对照 3. 选择指标。这是简化响应。"
        else:
            response_content = f"感谢您的问题：{user_message}。这是简化LLM响应，展示了Agent系统功能。实际环境将调用真实LLM服务。"
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            },
            "model": "simplified-llm",
            "created": int(time.time())
        }
    
    async def close(self):
        """关闭客户端"""
        logger.info("关闭简化LLM客户端")
        self.initialized = False

# 兼容性别名
LLMClient = SimpleLLMClient 