#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试任务状态管理功能
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


async def test_task_status_management():
    """测试任务状态管理功能"""
    print("🧪 开始测试任务状态管理...")
    
    # 创建黑板
    blackboard = Blackboard()
    
    # 创建Agents
    main_agent = MainAgent(blackboard)
    verification_agent = VerificationAgent(blackboard)
    critique_agent = CritiqueAgent(blackboard)
    report_agent = ReportAgent(blackboard)
    
    print("✅ Agent创建完成")
    
    # 测试1: 创建任务请求
    print("\n📝 测试1: 创建任务请求")
    
    task1 = TaskRequest(
        session_id="test_session_001",
        task_type="information_gathering",
        description="收集质子导体相关文献",
        assigned_agent="information_agent",
        priority=8
    )
    
    task_id1 = await blackboard.create_task_request(task1)
    print(f"创建任务1: {task_id1}")
    
    task2 = TaskRequest(
        session_id="test_session_001",
        task_type="verification",
        description="验证技术可行性",
        assigned_agent="verification_agent",
        priority=7,
        dependencies=[task_id1]
    )
    
    task_id2 = await blackboard.create_task_request(task2)
    print(f"创建任务2: {task_id2}")
    
    # 测试2: 查看任务状态
    print("\n📊 测试2: 查看任务状态")
    
    status1 = await blackboard.get_task_status(task_id1)
    print(f"任务1状态: {status1['status']}")
    
    status2 = await blackboard.get_task_status(task_id2)
    print(f"任务2状态: {status2['status']}")
    
    # 测试3: 更新任务状态
    print("\n🔄 测试3: 更新任务状态")
    
    # 任务1开始执行
    await blackboard.update_task_status(task_id1, TaskStatus.RUNNING, progress=0.1)
    print("任务1状态: PENDING -> RUNNING")
    
    # 任务1完成
    await blackboard.update_task_status(
        task_id1, 
        TaskStatus.SUCCESS, 
        output_data={"summary": "收集了50篇相关文献"},
        progress=1.0
    )
    print("任务1状态: RUNNING -> SUCCESS")
    
    # 任务2现在可以开始（依赖满足）
    await blackboard.update_task_status(task_id2, TaskStatus.RUNNING, progress=0.2)
    print("任务2状态: PENDING -> RUNNING")
    
    # 测试4: 获取待执行任务
    print("\n⏳ 测试4: 获取待执行任务")
    
    pending_tasks = await blackboard.get_pending_tasks()
    print(f"待执行任务数量: {len(pending_tasks)}")
    
    # 测试5: 获取会话任务统计
    print("\n📈 测试5: 获取任务统计")
    
    session_tasks = await blackboard.get_session_tasks("test_session_001")
    print(f"会话任务数量: {len(session_tasks)}")
    
    stats = await blackboard.get_task_statistics("test_session_001")
    print(f"任务统计: {stats}")
    
    print("\n✅ 任务状态管理测试完成")


async def test_multi_agent_coordination():
    """测试多Agent协调功能"""
    print("\n🤖 开始测试多Agent协调...")
    
    # 创建黑板和Agents
    blackboard = Blackboard()
    main_agent = MainAgent(blackboard)
    verification_agent = VerificationAgent(blackboard)
    critique_agent = CritiqueAgent(blackboard)
    report_agent = ReportAgent(blackboard)
    
    # 模拟完整的Agent协调流程
    session_id = "coordination_test_001"
    goal = "开发世界最高效的质子导体"
    
    print(f"🎯 测试目标: {goal}")
    
    # 步骤1: MainAgent拆解任务
    print("\n步骤1: MainAgent拆解任务")
    main_task_data = {
        "query": goal,
        "session_id": session_id
    }
    
    main_result = await main_agent.process_task(main_task_data)
    if main_result["success"]:
        print(f"✅ 任务拆解完成，生成{main_result['result']['tasks_count']}个子任务")
        tasks = main_result['result']['tasks']
        
        # 步骤2: 创建TaskRequest并更新状态
        print("\n步骤2: 创建TaskRequest")
        task_requests = []
        
        for task in tasks:
            task_request = TaskRequest(
                session_id=session_id,
                task_type=task['assigned_agent'],
                description=task['description'],
                assigned_agent=task['assigned_agent'],
                priority=8 if task['priority'] == 'high' else 5,
                dependencies=task.get('dependencies', [])
            )
            
            task_id = await blackboard.create_task_request(task_request)
            task_requests.append((task_id, task_request))
            print(f"创建任务: {task_id} -> {task['assigned_agent']}")
        
        # 步骤3: 模拟Agent依次执行
        print("\n步骤3: 模拟Agent执行")
        
        for task_id, task_request in task_requests:
            agent_type = task_request.assigned_agent
            
            # 更新为运行状态
            await blackboard.update_task_status(task_id, TaskStatus.RUNNING)
            print(f"🔄 {agent_type} 开始执行任务 {task_id}")
            
            # 模拟Agent处理
            try:
                if agent_type == "information_agent":
                    # 模拟信息收集
                    result_data = {"summary": "收集了相关文献和技术资料"}
                elif agent_type == "verification_agent":
                    # 执行验证Agent
                    verify_task_data = {"query": goal, "session_id": session_id}
                    verify_result = await verification_agent.process_task(verify_task_data)
                    result_data = verify_result.get("result", {})
                elif agent_type == "critique_agent":
                    # 执行批判Agent
                    critique_task_data = {"query": goal, "session_id": session_id}
                    critique_result = await critique_agent.process_task(critique_task_data)
                    result_data = critique_result.get("result", {})
                elif agent_type == "report_agent":
                    # 执行报告Agent
                    report_task_data = {"query": goal, "session_id": session_id}
                    report_result = await report_agent.process_task(report_task_data)
                    result_data = report_result.get("result", {})
                else:
                    result_data = {"message": f"{agent_type} 处理完成"}
                
                # 更新为成功状态
                await blackboard.update_task_status(
                    task_id, 
                    TaskStatus.SUCCESS, 
                    output_data=result_data,
                    progress=1.0
                )
                print(f"✅ {agent_type} 完成任务 {task_id}")
                
            except Exception as e:
                # 更新为失败状态
                await blackboard.update_task_status(
                    task_id, 
                    TaskStatus.FAILED, 
                    error_message=str(e)
                )
                print(f"❌ {agent_type} 任务失败 {task_id}: {e}")
        
        # 步骤4: 查看最终状态
        print("\n步骤4: 查看最终状态")
        
        final_stats = await blackboard.get_task_statistics(session_id)
        print(f"最终统计: {final_stats}")
        
        session_tasks = await blackboard.get_session_tasks(session_id)
        print(f"会话任务详情:")
        for task in session_tasks:
            print(f"  - {task['task_id']}: {task['status']} ({task['assigned_agent']})")
    
    else:
        print(f"❌ 任务拆解失败: {main_result.get('error')}")
    
    print("\n✅ 多Agent协调测试完成")


async def main():
    """主测试函数"""
    print("🔬 任务状态管理与多Agent协调测试")
    print("=" * 60)
    
    try:
        # 测试任务状态管理
        await test_task_status_management()
        
        # 测试多Agent协调
        await test_multi_agent_coordination()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 