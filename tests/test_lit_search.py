import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.agents.information_agent import InformationAgent

def test_parallel_database_search():
    info_agent = InformationAgent(blackboard=None)
    docs = asyncio.run(info_agent._parallel_database_search(["proton conductor"]))
    assert len(docs) >= 10, f"返回文献数不足，实际: {len(docs)}"
    for doc in docs[:3]:
        print(doc.title, doc.source_database) 