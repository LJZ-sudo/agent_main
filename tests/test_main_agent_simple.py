#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的MainAgent测试 - 测试基本功能
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.main_agent import MainAgent
from backend.core.blackboard import Blackboard


async def test_main_agent_basic():
    """测试MainAgent的基本功能（不使用LLM）"""
    print("🧪 开始测试MainAgent基本功能...")
    
    # 创建黑板
    blackboard = Blackboard()
    
    # 创建MainAgent
    main_agent = MainAgent(blackboard)
    
    print(f"✅ MainAgent创建完成: {main_agent.agent_id}")
    print(f"Agent类型: {main_agent.agent_type}")
    print(f"专长领域: {main_agent.specializations}")
    
    # 测试可用Agent信息
    print(f"\n🤖 可用Agent类型 ({len(main_agent.available_agents)}个):")
    for agent_id, agent_info in main_agent.available_agents.items():
        print(f"  - {agent_id}: {agent_info['name']}")
        print(f"    能力: {', '.join(agent_info['capabilities'])}")
    
    # 测试默认任务拆解
    test_goal = "开发世界最高效的质子导体"
    print(f"\n🎯 测试默认任务拆解: {test_goal}")
    
    default_tasks = main_agent._generate_default_tasks(test_goal)
    
    print(f"\n📋 默认拆解结果 ({len(default_tasks)}个子任务):")
    for i, task in enumerate(default_tasks, 1):
        print(f"\n任务 {i}:")
        print(f"  ID: {task['task_id']}")
        print(f"  描述: {task['description']}")
        print(f"  负责Agent: {task['assigned_agent']}")
        print(f"  优先级: {task['priority']}")
        print(f"  预期输出: {task['expected_output']}")
        print(f"  依赖: {task['dependencies']}")
    
    # 测试执行计划生成
    print(f"\n📊 测试执行计划生成...")
    execution_plan = main_agent._generate_execution_plan(default_tasks)
    
    print(f"总任务数: {execution_plan['total_tasks']}")
    print(f"优先级分布: {execution_plan['priority_distribution']}")
    print(f"Agent工作负载: {execution_plan['agent_workload']}")
    print(f"预计时间: {execution_plan['estimated_time_minutes']}分钟")
    
    print(f"\n执行阶段:")
    for phase in execution_plan['execution_phases']:
        print(f"  阶段{phase['phase']}: {phase['name']} ({len(phase['tasks'])}个任务)")
    
    # 测试黑板操作
    print(f"\n📝 测试黑板操作...")
    session_id = "test_session_001"
    
    try:
        await main_agent._publish_tasks_to_blackboard(default_tasks, session_id)
        print(f"✅ 任务发布到黑板成功")
        
        # 检查任务状态
        task_status = await main_agent.get_task_status(session_id)
        print(f"任务状态: {task_status}")
        
    except Exception as e:
        print(f"❌ 黑板操作失败: {e}")
    
    # 测试Agent能力
    print(f"\n🔧 Agent能力测试:")
    capabilities = main_agent.get_capabilities()
    print(f"支持的任务类型: {capabilities['supported_task_types']}")
    print(f"特性: {capabilities['features']}")
    
    print("\n🏁 基本功能测试完成")


if __name__ == "__main__":
    asyncio.run(test_main_agent_basic()) 