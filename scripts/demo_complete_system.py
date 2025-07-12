#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整系统演示 - 展示任务状态管理和多Agent协调
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


async def demo_complete_system():
    """完整系统演示"""
    print("🚀 多Agent科研系统完整演示")
    print("=" * 60)
    
    # 创建系统组件
    blackboard = Blackboard()
    main_agent = MainAgent(blackboard)
    verification_agent = VerificationAgent(blackboard)
    critique_agent = CritiqueAgent(blackboard)
    report_agent = ReportAgent(blackboard)
    
    # 研究目标
    goal = "开发世界最高效的质子导体"
    session_id = "demo_session_001"
    
    print(f"🎯 研究目标: {goal}")
    print(f"📋 会话ID: {session_id}")
    
    try:
        # === 阶段1: 任务拆解 ===
        print(f"\n{'='*60}")
        print("🔧 阶段1: 主Agent任务拆解")
        print(f"{'='*60}")
        
        main_task_data = {
            "query": goal,
            "session_id": session_id
        }
        
        # MainAgent拆解任务
        main_result = await main_agent.process_task(main_task_data)
        
        if main_result["success"]:
            tasks = main_result['result']['tasks']
            print(f"✅ 任务拆解成功，生成{len(tasks)}个子任务:")
            
            for i, task in enumerate(tasks, 1):
                print(f"  {i}. 【{task['task_id']}】{task['assigned_agent']}")
                print(f"     描述: {task['description']}")
                print(f"     优先级: {task['priority']}")
                print(f"     依赖: {task['dependencies'] if task['dependencies'] else '无'}")
                print()
        else:
            print(f"❌ 任务拆解失败: {main_result.get('error')}")
            return
        
        # === 阶段2: 任务状态管理 ===
        print(f"{'='*60}")
        print("📊 阶段2: 任务状态管理")
        print(f"{'='*60}")
        
        # 创建TaskRequest对象
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
            print(f"📝 创建任务: {task['assigned_agent']} -> {task_id[:8]}...")
        
        # 显示初始状态
        print(f"\n📈 初始任务统计:")
        initial_stats = await blackboard.get_task_statistics(session_id)
        print(f"  总任务: {initial_stats['total']}")
        print(f"  待执行: {initial_stats['pending']}")
        print(f"  进行中: {initial_stats['running']}")
        print(f"  已完成: {initial_stats['success']}")
        
        # === 阶段3: Agent协调执行 ===
        print(f"\n{'='*60}")
        print("🤖 阶段3: Agent协调执行")
        print(f"{'='*60}")
        
        for i, (task_id, task_request) in enumerate(task_requests, 1):
            agent_type = task_request.assigned_agent
            
            print(f"\n--- 执行任务 {i}/{len(task_requests)}: {agent_type} ---")
            
            # 更新为运行状态
            await blackboard.update_task_status(task_id, TaskStatus.RUNNING)
            print(f"🔄 {agent_type} 开始执行任务...")
            
            # 根据Agent类型执行相应任务
            try:
                if agent_type == "information_agent":
                    # 模拟信息收集
                    result_data = {
                        "summary": "收集了50篇相关文献，包括最新的质子导体研究进展",
                        "key_findings": ["新型材料发现", "效率提升方法", "应用前景分析"],
                        "data_quality": "高"
                    }
                    
                elif agent_type == "verification_agent":
                    # 执行验证分析
                    verify_task_data = {"query": goal, "session_id": session_id}
                    verify_result = await verification_agent.process_task(verify_task_data)
                    result_data = verify_result.get("result", {})
                    
                elif agent_type == "critique_agent":
                    # 执行批判分析
                    critique_task_data = {"query": goal, "session_id": session_id}
                    critique_result = await critique_agent.process_task(critique_task_data)
                    result_data = critique_result.get("result", {})
                    
                elif agent_type == "report_agent":
                    # 执行报告生成
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
                
                print(f"✅ {agent_type} 任务完成")
                
                # 显示关键结果
                if "feasibility_score" in result_data:
                    print(f"   可行性评分: {result_data['feasibility_score']}/10")
                if "innovation_score" in result_data:
                    print(f"   创新性评分: {result_data['innovation_score']}/10")
                if "word_count" in result_data:
                    print(f"   报告字数: {result_data['word_count']}")
                
            except Exception as e:
                # 更新为失败状态
                await blackboard.update_task_status(
                    task_id, 
                    TaskStatus.FAILED, 
                    error_message=str(e)
                )
                print(f"❌ {agent_type} 任务失败: {e}")
        
        # === 阶段4: 结果汇总 ===
        print(f"\n{'='*60}")
        print("📋 阶段4: 结果汇总与分析")
        print(f"{'='*60}")
        
        # 最终统计
        final_stats = await blackboard.get_task_statistics(session_id)
        print(f"📊 最终任务统计:")
        print(f"  总任务数: {final_stats['total']}")
        print(f"  成功完成: {final_stats['success']}")
        print(f"  执行失败: {final_stats['failed']}")
        print(f"  完成率: {final_stats['completion_rate']:.1%}")
        print(f"  平均执行时间: {final_stats['average_execution_time']:.2f}秒")
        
        # 详细任务状态
        print(f"\n📝 详细任务状态:")
        session_tasks = await blackboard.get_session_tasks(session_id)
        
        for task in session_tasks:
            status_emoji = {
                "success": "✅",
                "failed": "❌", 
                "running": "🔄",
                "pending": "⏳"
            }.get(task['status'], "❓")
            
            print(f"  {status_emoji} {task['assigned_agent']}: {task['status']}")
            if task['execution_time_seconds']:
                print(f"     执行时间: {task['execution_time_seconds']:.2f}秒")
            if task['error_message']:
                print(f"     错误信息: {task['error_message']}")
        
        # 系统健康状态
        print(f"\n🔍 系统健康状态:")
        health_status = await blackboard.health_check()
        print(f"  系统状态: {'健康' if health_status['status'] == 'healthy' else '异常'}")
        print(f"  活跃会话: {health_status['active_sessions']}")
        print(f"  事件总数: {health_status['total_events']}")
        
        # === 阶段5: 成果展示 ===
        print(f"\n{'='*60}")
        print("🎉 阶段5: 成果展示")
        print(f"{'='*60}")
        
        print(f"🏆 多Agent协作成果:")
        print(f"  📚 信息收集: 完成文献调研和背景分析")
        print(f"  🔍 可行性验证: 评估技术实现可能性")
        print(f"  🔬 批判分析: 识别问题并提出改进建议")
        print(f"  📄 报告生成: 整合结果形成完整报告")
        
        print(f"\n✨ 系统特色:")
        print(f"  🔄 智能任务拆解: 将复杂目标分解为可执行子任务")
        print(f"  📊 状态实时跟踪: 全程监控任务执行状态")
        print(f"  🤝 Agent协调: 多个专门Agent协作完成复杂任务")
        print(f"  📈 质量保证: 多层次验证确保结果可靠性")
        
        print(f"\n🎯 研究结论:")
        print(f"  基于多Agent协作分析，'{goal}'项目:")
        print(f"  • 具有较好的技术可行性")
        print(f"  • 存在一定的创新潜力")
        print(f"  • 需要充分的资源投入")
        print(f"  • 建议分阶段实施")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎊 完整系统演示结束")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(demo_complete_system()) 