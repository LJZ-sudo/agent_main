import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.agents.information_agent import InformationAgent

async def main():
    agent = InformationAgent(blackboard=None)
    docs = await agent._parallel_database_search(["new proton conductor materials"])
    print(f"FETCHED: {len(docs)} docs")
    print(json.dumps([d.title for d in docs[:5]], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 