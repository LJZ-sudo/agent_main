from enum import Enum

class LLMProvider(Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"

class Config:
    def __init__(self):
        self.llm_provider = LLMProvider.DEEPSEEK
        self.server_config = {"host": "0.0.0.0", "port": 8000}

def get_config():
    return Config() 