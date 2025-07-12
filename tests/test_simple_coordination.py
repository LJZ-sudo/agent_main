#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的多Agent协调测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.blackboard import Blackboard, TaskRequest, TaskStatus
from backend.agents.main_agent import MainAgent
from backend.agents.verification_agent import VerificationAgent
from backend.agents.critique_agent import CritiqueAgent
from backend.agents.report_agent import ReportAgent


async def test_simple_coordination():
    """简化的协调测试"""
    print("🧪 简化多Agent协调测试")
    print("=" * 50)
    
    # 创建系统
    blackboard = Blackboard()
    main_agent = MainAgent(blackboard)
    verification_agent = VerificationAgent(blackboard)
    critique_agent = CritiqueAgent(blackboard)
    report_agent = ReportAgent(blackboard)
    
    goal = "开发世界最高效的质子导体"
    session_id = "simple_test_001"
    
    print(f"🎯 目标: {goal}")
    
    try:
        # 步骤1: MainAgent拆解任务
        print("\n步骤1: 任务拆解")
        tasks = main_agent._generate_default_tasks(goal)
        print(f"拆解为{len(tasks)}个任务")
        
        # 步骤2: 创建任务状态记录
        print("\n步骤2: 创建任务状态")
        task_ids = []
        for task in tasks:
            task_request = TaskRequest(
                session_id=session_id,
                task_type=task['assigned_agent'],
                description=task['description'],
                assigned_agent=task['assigned_agent'],
                priority=8 if task['priority'] == 'high' else 5
            )
            task_id = await blackboard.create_task_request(task_request)
            task_ids.append(task_id)
            print(f"  创建: {task['assigned_agent']} -> {task_id[:8]}")
        
        # 步骤3: 模拟执行过程
        print("\n步骤3: 模拟执行")
        
        for i, task_id in enumerate(task_ids):
            # 开始执行
            await blackboard.update_task_status(task_id, TaskStatus.RUNNING)
            print(f"  任务{i+1}开始执行")
            
            # 完成执行
            await blackboard.update_task_status(
                task_id, 
                TaskStatus.SUCCESS,
                output_data={"result": f"任务{i+1}完成"},
                progress=1.0
            )
            print(f"  任务{i+1}执行完成")
        
        # 步骤4: 查看最终状态
        print("\n步骤4: 最终状态")
        stats = await blackboard.get_task_statistics(session_id)
        print(f"统计: 总计{stats['total']}个任务，成功{stats['success']}个")
        
        session_tasks = await blackboard.get_session_tasks(session_id)
        print(f"任务详情:")
        for task in session_tasks:
            print(f"  - {task['assigned_agent']}: {task['status']}")
        
        print("\n✅ 测试成功完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_coordination()) 