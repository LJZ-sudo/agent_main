from enum import Enum

class LLMProvider(Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"

class Config:
    def __init__(self):
        self.llm_provider = LLMProvider.DEEPSEEK
        self.server_config = {"host": "0.0.0.0", "port": 8000}
        self.serpapi_key = "2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117"  # SerpApi key
        self.searchapi_key = "8vhuFGEGjkcngqyyvQH4GJJa"  # SearchApi API key
        self.google_search_key = "2fd95f3bec77e746e92711b65838d29c2d161f28d6ddc512e051e4d81dbd6117"  # Google Search API key

def get_config():
    return Config() 