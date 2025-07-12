#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主Agent - 负责任务拆解、协调和管理
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.core.base_agent import BaseAgent


class MainAgent(BaseAgent):
    """主Agent - 负责科研任务的拆解、协调和管理"""

    def __init__(self, blackboard):
        super().__init__("main_agent", blackboard)
        self.agent_type = "main_coordinator"
        self.specializations = [
            "任务拆解",
            "工作流协调", 
            "项目管理",
            "科研规划"
        ]
        
        # 可用的Agent类型及其专长
        self.available_agents = {
            "information_agent": {
                "name": "信息收集Agent",
                "capabilities": ["文献检索", "数据收集", "背景调研", "前沿技术分析"]
            },
            "verification_agent": {
                "name": "验证Agent", 
                "capabilities": ["数据验证", "可行性分析", "质量评估", "风险分析"]
            },
            "critique_agent": {
                "name": "批判分析Agent",
                "capabilities": ["批判性分析", "问题识别", "改进建议", "质量评估"]
            },
            "report_agent": {
                "name": "报告生成Agent",
                "capabilities": ["报告撰写", "结果整理", "可视化", "总结归纳"]
            },
            "modeling_agent": {
                "name": "建模Agent",
                "capabilities": ["数学建模", "仿真分析", "理论推导", "模型验证"]
            },
            "experiment_design_agent": {
                "name": "实验设计Agent", 
                "capabilities": ["实验设计", "方案制定", "参数优化", "流程规划"]
            },
            "evaluation_agent": {
                "name": "评估Agent",
                "capabilities": ["性能评估", "效果分析", "对比研究", "指标评价"]
            }
        }

    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理主任务 - 拆解目标并协调执行"""
        try:
            goal = task_data.get("query", "")
            session_id = task_data.get("session_id", f"session_{uuid.uuid4().hex[:8]}")
            
            logger.info(f"🎯 MainAgent开始处理科研目标: {goal[:100]}...")
            
            # 1. 拆解目标为子任务
            tasks = await self.split_goal_to_tasks(goal)
            
            # 2. 将任务发布到黑板
            await self._publish_tasks_to_blackboard(tasks, session_id)
            
            # 3. 生成执行计划
            execution_plan = self._generate_execution_plan(tasks)
            
            logger.info(f"✅ MainAgent完成任务拆解，生成{len(tasks)}个子任务")
            
            return {
                "goal": goal,
                "session_id": session_id,
                "tasks_count": len(tasks),
                "tasks": tasks,
                "execution_plan": execution_plan,
                "status": "tasks_created",
                "message": f"已将科研目标拆解为{len(tasks)}个子任务，并制定执行计划"
            }
            
        except Exception as e:
            logger.error(f"❌ MainAgent处理失败: {e}")
            raise

    async def split_goal_to_tasks(self, goal: str) -> List[Dict]:
        """将科研目标拆解为结构化的子任务列表"""
        try:
            logger.info(f"🔍 开始拆解科研目标: {goal}")
            
            # 构建任务拆解的提示词
            system_prompt = """你是一个专业的科研项目管理专家，擅长将复杂的科研目标拆解为具体的执行步骤。

请将用户输入的科研目标拆解为具体的子任务，每个子任务应该：
1. 有明确的任务描述
2. 指定最适合的执行Agent
3. 有清晰的预期输出
4. 考虑任务间的依赖关系

可用的Agent类型：
- information_agent: 文献检索、数据收集、背景调研
- verification_agent: 数据验证、可行性分析、质量评估  
- critique_agent: 批判性分析、问题识别、改进建议
- report_agent: 报告撰写、结果整理、总结归纳
- modeling_agent: 数学建模、仿真分析、理论推导
- experiment_design_agent: 实验设计、方案制定、参数优化
- evaluation_agent: 性能评估、效果分析、对比研究

请以JSON格式返回任务列表，格式如下：
[
  {
    "task_id": "t1",
    "description": "具体任务描述",
    "assigned_agent": "agent类型",
    "expected_output": "预期输出描述",
    "priority": "high/medium/low",
    "dependencies": ["依赖的task_id列表"]
  }
]"""

            user_prompt = f"""科研目标：{goal}

请将此目标拆解为具体的子任务列表。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 调用LLM进行任务拆解
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await self.llm_client.generate_text(
                full_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            if not response.success:
                raise Exception(f"LLM调用失败: {response.error}")
            
            content = response.content.strip()
            logger.debug(f"LLM任务拆解原始响应: {content}")
            
            # 解析JSON响应
            try:
                # 尝试提取JSON部分
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "[" in content and "]" in content:
                    json_start = content.find("[")
                    json_end = content.rfind("]") + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                tasks = json.loads(json_content)
                
                # 验证和标准化任务格式
                standardized_tasks = []
                for i, task in enumerate(tasks):
                    standardized_task = {
                        "task_id": task.get("task_id", f"t{i+1}"),
                        "description": task.get("description", ""),
                        "assigned_agent": task.get("assigned_agent", "information_agent"),
                        "expected_output": task.get("expected_output", "相关研究结果"),
                        "priority": task.get("priority", "medium"),
                        "dependencies": task.get("dependencies", []),
                        "status": "pending",
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # 验证assigned_agent是否有效
                    if standardized_task["assigned_agent"] not in self.available_agents:
                        logger.warning(f"未知的Agent类型: {standardized_task['assigned_agent']}, 使用默认的information_agent")
                        standardized_task["assigned_agent"] = "information_agent"
                    
                    standardized_tasks.append(standardized_task)
                
                logger.info(f"✅ 成功拆解为{len(standardized_tasks)}个子任务")
                return standardized_tasks
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 内容: {content}")
                # 返回默认的任务拆解
                return self._generate_default_tasks(goal)
                
        except Exception as e:
            logger.error(f"任务拆解失败: {e}")
            # 返回默认的任务拆解
            return self._generate_default_tasks(goal)

    def _generate_default_tasks(self, goal: str) -> List[Dict]:
        """生成默认的任务拆解（当LLM拆解失败时使用）"""
        logger.warning("使用默认任务拆解模板")
        
        default_tasks = [
            {
                "task_id": "t1",
                "description": f"收集关于'{goal}'的相关文献和背景资料",
                "assigned_agent": "information_agent",
                "expected_output": "相关文献列表和背景分析报告",
                "priority": "high",
                "dependencies": [],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            },
            {
                "task_id": "t2", 
                "description": f"验证'{goal}'的技术可行性和实现难度",
                "assigned_agent": "verification_agent",
                "expected_output": "可行性分析报告和风险评估",
                "priority": "high",
                "dependencies": ["t1"],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            },
            {
                "task_id": "t3",
                "description": f"对'{goal}'进行批判性分析，识别潜在问题和改进方向",
                "assigned_agent": "critique_agent", 
                "expected_output": "批判分析报告和改进建议",
                "priority": "medium",
                "dependencies": ["t1", "t2"],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            },
            {
                "task_id": "t4",
                "description": f"生成关于'{goal}'的综合研究报告",
                "assigned_agent": "report_agent",
                "expected_output": "完整的研究报告和总结",
                "priority": "medium", 
                "dependencies": ["t1", "t2", "t3"],
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        return default_tasks

    async def _publish_tasks_to_blackboard(self, tasks: List[Dict], session_id: str):
        """将任务发布到黑板系统"""
        try:
            # 创建会话记录
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "total_tasks": len(tasks),
                "completed_tasks": 0,
                "tasks": {task["task_id"]: task for task in tasks}
            }
            
            # 写入黑板
            await self.blackboard.store_data(f"session_{session_id}", session_data)
            
            # 为每个任务创建独立的黑板条目
            for task in tasks:
                task_key = f"task_{session_id}_{task['task_id']}"
                await self.blackboard.store_data(task_key, task)
                
            logger.info(f"✅ 已将{len(tasks)}个任务发布到黑板")
            
        except Exception as e:
            logger.error(f"发布任务到黑板失败: {e}")
            raise

    def _generate_execution_plan(self, tasks: List[Dict]) -> Dict[str, Any]:
        """生成任务执行计划"""
        try:
            # 按优先级和依赖关系排序任务
            high_priority = [t for t in tasks if t["priority"] == "high"]
            medium_priority = [t for t in tasks if t["priority"] == "medium"] 
            low_priority = [t for t in tasks if t["priority"] == "low"]
            
            # 按Agent类型分组
            agent_workload = {}
            for task in tasks:
                agent = task["assigned_agent"]
                if agent not in agent_workload:
                    agent_workload[agent] = []
                agent_workload[agent].append(task["task_id"])
            
            # 估算总执行时间（基于任务数量和复杂度）
            estimated_time_minutes = len(tasks) * 5  # 假设每个任务平均5分钟
            
            execution_plan = {
                "total_tasks": len(tasks),
                "priority_distribution": {
                    "high": len(high_priority),
                    "medium": len(medium_priority), 
                    "low": len(low_priority)
                },
                "agent_workload": agent_workload,
                "estimated_time_minutes": estimated_time_minutes,
                "execution_phases": [
                    {
                        "phase": 1,
                        "name": "信息收集阶段",
                        "tasks": [t["task_id"] for t in tasks if t["assigned_agent"] == "information_agent"]
                    },
                    {
                        "phase": 2, 
                        "name": "分析验证阶段",
                        "tasks": [t["task_id"] for t in tasks if t["assigned_agent"] in ["verification_agent", "critique_agent"]]
                    },
                    {
                        "phase": 3,
                        "name": "报告生成阶段", 
                        "tasks": [t["task_id"] for t in tasks if t["assigned_agent"] == "report_agent"]
                    }
                ],
                "created_at": datetime.now().isoformat()
            }
            
            return execution_plan
            
        except Exception as e:
            logger.error(f"生成执行计划失败: {e}")
            return {"error": str(e)}

    def _get_supported_task_types(self) -> List[str]:
        """获取支持的任务类型"""
        return [
            "goal_decomposition",
            "task_coordination", 
            "project_planning",
            "workflow_management"
        ]

    def _get_features(self) -> List[str]:
        """获取Agent特性"""
        return [
            "智能任务拆解",
            "多Agent协调",
            "执行计划生成",
            "项目进度管理",
            "科研流程优化"
        ]

    async def get_task_status(self, session_id: str) -> Dict[str, Any]:
        """获取任务执行状态"""
        try:
            session_data = await self.blackboard.get_data(f"session_{session_id}")
            if not session_data:
                return {"error": "会话不存在"}
            
            # 统计任务状态
            tasks = session_data.get("tasks", {})
            status_count = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
            
            for task in tasks.values():
                status = task.get("status", "pending")
                status_count[status] = status_count.get(status, 0) + 1
            
            progress = (status_count["completed"] / len(tasks)) * 100 if tasks else 0
            
            return {
                "session_id": session_id,
                "total_tasks": len(tasks),
                "status_distribution": status_count,
                "progress_percentage": round(progress, 2),
                "session_status": session_data.get("status", "unknown"),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {"error": str(e)}