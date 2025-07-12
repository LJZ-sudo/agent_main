#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from backend.agents.information_agent import InformationAgent
    print("✅ 成功导入 InformationAgent")
    
    async def test_literature_search():
        info_agent = InformationAgent(blackboard=None)
        docs = await info_agent._parallel_database_search(["proton conductor"])
        print(f"📚 检索到 {len(docs)} 篇文献")
        
        if len(docs) >= 10:
            print("✅ 文献数量满足要求")
        else:
            print(f"⚠️ 文献数量不足，期望>=10，实际={len(docs)}")
        
        # 打印前3篇文献信息
        for i, doc in enumerate(docs[:3]):
            print(f"📄 {i+1}. {doc.title} | 来源: {doc.source_database}")
        
        return docs
    
    if __name__ == "__main__":
        docs = asyncio.run(test_literature_search())
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
except Exception as e:
    print(f"❌ 测试失败: {e}") 