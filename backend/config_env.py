#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量配置管理模块
"""

import os
from typing import Optional

class EnvironmentConfig:
    """环境变量配置类"""
    
    def __init__(self):
        # API密钥
        self.serpapi_key = os.getenv('SERPAPI_KEY', '2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117')
        self.searchapi_key = os.getenv('SEARCHAPI_KEY', '8vhuFGEGjkcngqyyvQH4GJJa')
        self.google_search_key = os.getenv('GOOGLE_SEARCH_KEY', '2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117')
        
        # LLM配置
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY', 'sk-7ca2f21430bb4383ab97fbf7e0f8cf05')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        # 搜索配置
        self.search_strategy = os.getenv('SEARCH_STRATEGY', 'intelligent')
        self.api_cost_monitoring = os.getenv('API_COST_MONITORING', 'false').lower() == 'true'
        self.daily_cost_limit = float(os.getenv('DAILY_COST_LIMIT', '10.0'))
        self.fallback_to_free = os.getenv('FALLBACK_TO_FREE', 'true').lower() == 'true'
        self.api_usage_log_enabled = os.getenv('API_USAGE_LOG_ENABLED', 'true').lower() == 'true'
        self.cost_alert_threshold = float(os.getenv('COST_ALERT_THRESHOLD', '0.8'))
    
    def get_literature_search_config(self):
        """获取文献搜索引擎配置"""
        return self
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        # 至少要有一个API密钥或者允许使用免费API
        has_paid_api = bool(self.serpapi_key or self.searchapi_key)
        return has_paid_api or self.fallback_to_free
    
    def get_available_apis(self) -> list:
        """获取可用的API列表"""
        apis = []
        if self.serpapi_key:
            apis.append('serpapi')
        if self.searchapi_key:
            apis.append('searchapi')
        if self.fallback_to_free:
            apis.extend(['arxiv', 'semantic_scholar', 'pubmed', 'crossref'])
        return apis

# 全局配置实例
_config_instance = None

def get_env_config() -> EnvironmentConfig:
    """获取环境配置单例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnvironmentConfig()
    return _config_instance

def set_env_variables():
    """设置环境变量（用于测试或手动配置）"""
    # 这个函数可以用来手动设置环境变量
    env_vars = {
        'SERPAPI_KEY': '2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117',
        'SEARCHAPI_KEY': '8vhuFGEGjkcngqyyvQH4GJJa',
        'GOOGLE_SEARCH_KEY': '2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117',
        'DEEPSEEK_API_KEY': 'sk-7ca2f21430bb4383ab97fbf7e0f8cf05',
        'SEARCH_STRATEGY': 'intelligent',
        'API_COST_MONITORING': 'false',
        'DAILY_COST_LIMIT': '10.0',
        'FALLBACK_TO_FREE': 'true',
        'API_USAGE_LOG_ENABLED': 'true',
        'COST_ALERT_THRESHOLD': '0.8'
    }
    
    for key, value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = value
    
    # 重新创建配置实例
    global _config_instance
    _config_instance = None
    return get_env_config()

if __name__ == "__main__":
    # 测试配置
    config = get_env_config()
    print(f"SerpApi Key: {config.serpapi_key[:20]}..." if config.serpapi_key else "SerpApi Key: 未配置")
    print(f"SearchApi Key: {config.searchapi_key[:20]}..." if config.searchapi_key else "SearchApi Key: 未配置")
    print(f"配置有效: {config.is_valid()}")
    print(f"可用APIs: {config.get_available_apis()}") 