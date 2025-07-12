#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MainAgent的任务拆解功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.main_agent import MainAgent
from backend.core.blackboard import Blackboard


async def test_main_agent():
    """测试MainAgent的基本功能"""
    print("🧪 开始测试MainAgent...")
    
    # 创建黑板
    blackboard = Blackboard()
    
    # 创建MainAgent
    main_agent = MainAgent(blackboard)
    await main_agent.initialize()
    
    print(f"✅ MainAgent初始化完成: {main_agent.agent_id}")
    
    # 测试目标拆解
    test_goal = "开发世界最高效的质子导体"
    print(f"\n🎯 测试目标拆解: {test_goal}")
    
    try:
        tasks = await main_agent.split_goal_to_tasks(test_goal)
        
        print(f"\n📋 拆解结果 ({len(tasks)}个子任务):")
        for i, task in enumerate(tasks, 1):
            print(f"\n任务 {i}:")
            print(f"  ID: {task['task_id']}")
            print(f"  描述: {task['description']}")
            print(f"  负责Agent: {task['assigned_agent']}")
            print(f"  优先级: {task['priority']}")
            print(f"  预期输出: {task['expected_output']}")
            print(f"  依赖: {task['dependencies']}")
        
        # 测试完整的任务处理
        print(f"\n🔄 测试完整任务处理...")
        task_data = {
            "query": test_goal,
            "session_id": "test_session_001"
        }
        
        result = await main_agent.process_task(task_data)
        
        if result["success"]:
            print(f"✅ 任务处理成功!")
            print(f"  会话ID: {result['result']['session_id']}")
            print(f"  任务数量: {result['result']['tasks_count']}")
            print(f"  处理时间: {result['processing_time']:.2f}秒")
        else:
            print(f"❌ 任务处理失败: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 测试完成")


if __name__ == "__main__":
    asyncio.run(test_main_agent()) 