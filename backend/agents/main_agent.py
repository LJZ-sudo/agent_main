"""
主Agent - 系统协调和任务分配
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from ..core.base_agent import BaseAgent
from ..core.blackboard import BlackboardEvent, EventType, ReasoningStep


class MainAgent(BaseAgent):
    """主Agent - 负责系统协调、任务规划和决策"""
    
    def __init__(self, blackboard):
        super().__init__("main_agent", blackboard)
        self.agent_type = "coordinator"
        self.specializations = ["task_planning", "decision_making", "coordination"]
        self.active_sessions = {}
        
    async def initialize(self):
        """初始化主Agent"""
        await super().initialize()
        logger.info("主Agent初始化完成")
        
    async def process_research_request(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """处理研究请求的核心方法"""
        try:
            if not session_id:
                session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"主Agent开始处理研究请求: {user_input[:50]}...")
            
            # 1. 任务分析和规划
            task_plan = await self._analyze_and_plan_task(user_input, session_id)
            
            # 2. 分配任务给其他Agent
            execution_results = await self._execute_task_plan(task_plan, session_id)
            
            # 3. 整合结果
            final_result = await self._integrate_results(execution_results, session_id)
            
            # 4. 更新会话状态
            self.active_sessions[session_id] = {
                "status": "completed",
                "results": final_result,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"主Agent完成研究请求处理: {session_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"主Agent处理请求失败: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if session_id:
                self.active_sessions[session_id] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            
            return error_result
    
    async def _analyze_and_plan_task(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """分析任务并制定计划 - 增强版本，符合docs要求"""
        logger.info(f"分析任务: {user_input[:30]}...")
        
        # 开始推理链
        chain_id = await self.blackboard.create_inference_chain(
            session_id, self.agent_id, "task_analysis", {"user_input": user_input}
        )
        
        # 记录问题解析步骤
        parse_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="analysis",
            description="解析用户需求和研究问题",
            input_data={"user_input": user_input},
            reasoning_text="开始分析用户提出的科研创意需求，识别问题类型和复杂度"
        )
        await self.blackboard.record_reasoning_step(parse_step)
        
        # 发布任务开始事件
        await self.blackboard.publish_event(BlackboardEvent(
            event_type=EventType.TASK_STARTED,
            agent_id=self.agent_id,
            session_id=session_id,
            data={
                "user_input": user_input,
                "stage": "task_analysis",
                "chain_id": chain_id
            }
        ))
        
        # 使用LLM进行深度任务分析
        analysis_prompt = f"""
作为科研多Agent系统的主Agent，请深度分析以下研究请求并制定详细的执行计划：

用户请求: {user_input}

请按以下步骤进行分析：

1. **问题解析与边界定义**：
   - 识别核心研究问题
   - 明确研究领域和边界
   - 提取关键概念和目标
   - 识别约束条件和限制

2. **任务分解策略**：
   - 将问题分解为具体子任务
   - 确定任务间的依赖关系
   - 评估任务优先级和并行可能性
   - 预估每个子任务的复杂度

3. **Agent协作规划**：
   - 确定需要调用的专门Agent
   - 设计Agent间的协作序列
   - 制定质量控制检查点
   - 规划批判和验证环节

4. **执行策略制定**：
   - 制定分阶段执行计划
   - 设定里程碑和检查点
   - 预估时间和资源需求
   - 制定风险控制措施

请以JSON格式返回详细分析：
{{
    "problem_analysis": {{
        "core_question": "核心研究问题",
        "research_domain": "研究领域",
        "key_concepts": ["概念1", "概念2"],
        "objectives": ["目标1", "目标2"],
        "constraints": ["约束1", "约束2"],
        "complexity_level": "高/中/低"
    }},
    "task_decomposition": {{
        "subtasks": [
            {{
                "task_id": "task_1",
                "task_name": "子任务名称",
                "description": "详细描述",
                "agent_type": "required_agent",
                "priority": 1,
                "dependencies": ["dependency_task_ids"],
                "estimated_time": "预计时间",
                "complexity": "高/中/低",
                "deliverables": ["交付物1", "交付物2"]
            }}
        ],
        "execution_phases": [
            {{
                "phase": "阶段1",
                "tasks": ["task_1", "task_2"],
                "milestone": "里程碑描述"
            }}
        ]
    }},
    "agent_collaboration": {{
        "required_agents": ["agent1", "agent2"],
        "collaboration_sequence": [
            {{
                "step": 1,
                "agents": ["agent1"],
                "action": "执行动作",
                "expected_output": "预期输出"
            }}
        ],
        "quality_checkpoints": ["检查点1", "检查点2"]
    }},
    "execution_strategy": {{
        "phases": ["阶段1", "阶段2"],
        "parallel_tasks": [["可并行任务组"]],
        "critical_path": ["关键路径任务"],
        "risk_factors": ["风险1", "风险2"],
        "mitigation_strategies": ["缓解策略1", "策略2"]
    }}
}}
"""
        
        try:
            # 记录LLM分析步骤
            llm_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="inference",
                description="使用LLM进行任务分析和分解",
                input_data={"prompt": analysis_prompt[:200] + "..."},
                reasoning_text="调用LLM进行深度任务分析，制定详细执行计划"
            )
            await self.blackboard.record_reasoning_step(llm_step)
            
            analysis_response = await self.llm_client.generate_text(
                analysis_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            if analysis_response.success:
                try:
                    # 尝试解析JSON响应
                    analysis_data = json.loads(analysis_response.content)
                    
                    # 记录分析完成步骤
                    completion_step = ReasoningStep(
                        agent_id=self.agent_id,
                        step_type="decision",
                        description="完成任务分析和计划制定",
                        input_data={"llm_response": analysis_response.content[:200] + "..."},
                        output_data=analysis_data,
                        reasoning_text="LLM分析完成，生成了详细的任务分解和执行计划",
                        confidence=0.9
                    )
                    await self.blackboard.record_reasoning_step(completion_step)
                    
                    task_plan = {
                        "session_id": session_id,
                        "user_input": user_input,
                        "analysis_data": analysis_data,
                        "chain_id": chain_id,
                        "required_agents": analysis_data.get("agent_collaboration", {}).get("required_agents", ["information_enhanced", "verification", "critique", "report"]),
                        "execution_order": self._extract_execution_order(analysis_data),
                        "subtasks": analysis_data.get("task_decomposition", {}).get("subtasks", []),
                        "quality_checkpoints": analysis_data.get("agent_collaboration", {}).get("quality_checkpoints", []),
                        "estimated_complexity": self._calculate_complexity_score(analysis_data),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 记录任务分解到黑板
                    await self.blackboard.record_task_decomposition(session_id, task_plan)
                    
                    # 发布问题解析完成事件
                    await self.blackboard.publish_event(BlackboardEvent(
                        event_type=EventType.PROBLEM_PARSED,
                        agent_id=self.agent_id,
                        session_id=session_id,
                        data={
                            "problem_analysis": analysis_data.get("problem_analysis", {}),
                            "complexity": task_plan["estimated_complexity"]
                        }
                    ))
                    
                    logger.info(f"任务分析完成: {len(task_plan['required_agents'])}个Agent需要参与")
                    return task_plan
                    
                except json.JSONDecodeError:
                    logger.warning("LLM返回的不是有效JSON，使用备用分析")
                    return self._create_fallback_plan(user_input, session_id, chain_id)
            else:
                logger.error(f"LLM分析失败: {analysis_response.error}")
                return self._create_fallback_plan(user_input, session_id, chain_id)
            
        except Exception as e:
            logger.error(f"任务分析异常: {e}")
            return self._create_fallback_plan(user_input, session_id, chain_id)
    
    def _extract_execution_order(self, analysis_data: Dict[str, Any]) -> List[str]:
        """从分析数据中提取执行顺序"""
        collaboration = analysis_data.get("agent_collaboration", {})
        sequence = collaboration.get("collaboration_sequence", [])
        
        execution_order = []
        for step in sequence:
            agents = step.get("agents", [])
            for agent in agents:
                if agent not in execution_order:
                    execution_order.append(agent)
        
        # 如果没有明确顺序，使用默认顺序
        if not execution_order:
            execution_order = ["information_enhanced", "verification", "critique", "report"]
            
        return execution_order
    
    def _calculate_complexity_score(self, analysis_data: Dict[str, Any]) -> float:
        """计算复杂度评分"""
        problem_analysis = analysis_data.get("problem_analysis", {})
        task_decomposition = analysis_data.get("task_decomposition", {})
        
        complexity_level = problem_analysis.get("complexity_level", "中")
        subtask_count = len(task_decomposition.get("subtasks", []))
        
        base_score = {
            "低": 0.3,
            "中": 0.6,
            "高": 0.9
        }.get(complexity_level, 0.6)
        
        # 根据子任务数量调整
        task_factor = min(subtask_count / 5.0, 1.0)  # 5个子任务为满分
        
        return min(base_score + task_factor * 0.3, 1.0)
    
    def _create_fallback_plan(self, user_input: str, session_id: str, chain_id: str) -> Dict[str, Any]:
        """创建备用计划（当LLM分析失败时）"""
        logger.info("使用备用任务分析方案")
        
        return {
            "session_id": session_id,
            "user_input": user_input,
            "analysis_data": {
                "problem_analysis": {
                    "core_question": user_input,
                    "research_domain": "通用科研",
                    "complexity_level": "中"
                }
            },
            "chain_id": chain_id,
            "required_agents": ["information_enhanced", "verification", "critique", "report"],
            "execution_order": ["information_enhanced", "verification", "critique", "report"],
            "subtasks": [
                {
                    "task_id": "task_1",
                    "task_name": "信息收集",
                    "agent_type": "information_enhanced"
                },
                {
                    "task_id": "task_2", 
                    "task_name": "验证分析",
                    "agent_type": "verification"
                },
                {
                    "task_id": "task_3",
                    "task_name": "批判评估", 
                    "agent_type": "critique"
                },
                {
                    "task_id": "task_4",
                    "task_name": "报告生成",
                    "agent_type": "report"
                }
            ],
            "quality_checkpoints": ["信息验证", "逻辑检查", "最终审查"],
            "estimated_complexity": 0.5,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_task_plan(self, task_plan: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """执行任务计划 - 增强版本，支持事件驱动协作"""
        logger.info(f"开始执行任务计划: {session_id}")
        
        execution_results = {
            "session_id": session_id,
            "agent_results": {},
            "execution_log": [],
            "reasoning_chain": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录执行开始推理步骤
        execution_start_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="execution",
            description="开始执行任务计划",
            input_data={"plan": task_plan.get("subtasks", [])},
            reasoning_text=f"开始按计划执行{len(task_plan['execution_order'])}个Agent任务"
        )
        await self.blackboard.record_reasoning_step(execution_start_step)
        
        # 按顺序执行Agent任务，支持并行处理
        for i, agent_name in enumerate(task_plan["execution_order"]):
            try:
                logger.info(f"调用 {agent_name} Agent (步骤 {i+1}/{len(task_plan['execution_order'])})...")
                
                # 记录Agent调用决策
                agent_call_step = ReasoningStep(
                    agent_id=self.agent_id,
                    step_type="decision",
                    description=f"决定调用{agent_name} Agent",
                    input_data={"agent": agent_name, "step": i+1},
                    reasoning_text=f"根据任务计划，现在需要调用{agent_name} Agent来处理相关任务",
                    confidence=0.8
                )
                await self.blackboard.record_reasoning_step(agent_call_step)
                
                # 获取对应的子任务信息
                current_subtask = self._get_subtask_for_agent(task_plan, agent_name)
                
                # 发布Agent任务事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.TASK_ASSIGNED,
                    agent_id=self.agent_id,
                    target_agent=agent_name,
                    session_id=session_id,
                    data={
                        "task_type": agent_name,
                        "user_input": task_plan["user_input"],
                        "subtask_info": current_subtask,
                        "previous_results": execution_results.get("agent_results", {}),
                        "step_number": i+1,
                        "total_steps": len(task_plan["execution_order"])
                    }
                ))
                
                # 使用LLM处理Agent任务（在专门Agent不可用时的替代方案）
                agent_result = await self._process_agent_task_with_llm(
                    agent_name, 
                    task_plan["user_input"], 
                    execution_results.get("agent_results", {}),
                    session_id,
                    current_subtask
                )
                
                # 记录Agent完成步骤
                agent_completion_step = ReasoningStep(
                    agent_id=self.agent_id,
                    step_type="validation",
                    description=f"{agent_name} Agent任务完成",
                    input_data={"agent": agent_name},
                    output_data={"result_summary": str(agent_result)[:200] + "..."},
                    reasoning_text=f"{agent_name} Agent成功完成任务，产出了相关结果",
                    confidence=0.9
                )
                await self.blackboard.record_reasoning_step(agent_completion_step)
                
                execution_results["agent_results"][agent_name] = agent_result
                execution_results["execution_log"].append({
                    "agent": agent_name,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "subtask": current_subtask.get("task_name", "") if current_subtask else ""
                })
                
                # 发布Agent完成事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.TASK_COMPLETED,
                    agent_id=agent_name,
                    session_id=session_id,
                    data={
                        "result": agent_result,
                        "completion_time": datetime.now().isoformat(),
                        "step_completed": i+1
                    }
                ))
                
                logger.info(f"{agent_name} Agent处理完成")
                
                # 检查质量控制点
                if i+1 in [len(task_plan["execution_order"])//2, len(task_plan["execution_order"])]:
                    await self._perform_quality_check(execution_results, session_id, i+1)

            except Exception as e:
                logger.error(f"{agent_name} Agent处理失败: {e}")
                
                # 记录错误推理步骤
                error_step = ReasoningStep(
                    agent_id=self.agent_id,
                    step_type="error",
                    description=f"{agent_name} Agent执行失败",
                    input_data={"agent": agent_name, "error": str(e)},
                    reasoning_text=f"{agent_name} Agent执行过程中发生错误: {str(e)}",
                    confidence=0.0
                )
                await self.blackboard.record_reasoning_step(error_step)
                
                execution_results["execution_log"].append({
                    "agent": agent_name,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布错误事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.ERROR_OCCURRED,
                    agent_id=self.agent_id,
                    session_id=session_id,
                    data={
                        "failed_agent": agent_name,
                        "error_message": str(e),
                        "step_failed": i+1
                    }
                ))
                
                # 可选择是否继续执行其他Agent
                continue
        
        # 记录执行完成推理步骤
        execution_complete_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="completion",
            description="任务计划执行完成",
            input_data={"completed_agents": list(execution_results["agent_results"].keys())},
            output_data=execution_results["execution_log"],
            reasoning_text=f"成功完成{len(execution_results['agent_results'])}个Agent的任务执行",
            confidence=0.95
        )
        await self.blackboard.record_reasoning_step(execution_complete_step)
        
        return execution_results
    
    def _get_subtask_for_agent(self, task_plan: Dict[str, Any], agent_name: str) -> Optional[Dict[str, Any]]:
        """获取特定Agent对应的子任务信息"""
        subtasks = task_plan.get("subtasks", [])
        for subtask in subtasks:
            if subtask.get("agent_type") == agent_name:
                return subtask
        return None
    
    async def _perform_quality_check(self, execution_results: Dict[str, Any], session_id: str, step_number: int):
        """执行质量控制检查"""
        logger.info(f"执行质量控制检查 - 步骤 {step_number}")
        
        # 记录质量检查推理步骤
        quality_check_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="validation",
            description=f"质量控制检查 - 步骤 {step_number}",
            input_data={"completed_agents": list(execution_results["agent_results"].keys())},
            reasoning_text=f"在第{step_number}步执行质量控制检查，确保输出质量"
        )
        await self.blackboard.record_reasoning_step(quality_check_step)
        
        # 发布质量检查事件
        await self.blackboard.publish_event(BlackboardEvent(
            event_type=EventType.QUALITY_CHECK,
            agent_id=self.agent_id,
            session_id=session_id,
            data={
                "checkpoint": step_number,
                "completed_results": execution_results["agent_results"],
                "check_type": "intermediate" if step_number < 4 else "final"
            }
        ))
    
    async def _process_agent_task_with_llm(self, agent_name: str, user_input: str, previous_results: Dict, session_id: str, current_subtask: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用LLM处理Agent任务（在专门Agent不可用时的替代方案）"""
        
        agent_prompts = {
            "information_enhanced": f"""
作为信息检索Agent，请对以下研究问题进行文献调研：

研究问题: {user_input}

请提供：
1. 相关的学术文献和资源
2. 背景知识总结
3. 当前研究现状
4. 关键概念和术语

请以结构化格式返回结果。
""",
            "verification": f"""
作为验证Agent，请检查以下信息的准确性和一致性：

研究问题: {user_input}
信息检索结果: {previous_results.get('information_enhanced', {}).get('content', '暂无')}

请验证：
1. 信息的准确性
2. 逻辑一致性
3. 可信度评估
4. 潜在问题或矛盾

请提供验证报告。
""",
            "critique": f"""
作为批判Agent，请对以下研究内容进行批判性评估：

研究问题: {user_input}
已有分析: {previous_results.get('verification', {}).get('content', '暂无')}

请从以下角度进行批判：
1. 创新性评估
2. 方法论审查
3. 潜在风险和局限
4. 改进建议

请提供批判性分析报告。
""",
            "report": f"""
作为报告生成Agent，请基于以下信息生成综合研究报告：

研究问题: {user_input}
信息检索: {previous_results.get('information_enhanced', {}).get('content', '暂无')}
验证结果: {previous_results.get('verification', {}).get('content', '暂无')}
批判分析: {previous_results.get('critique', {}).get('content', '暂无')}

请生成包含以下部分的完整报告：
1. 执行摘要
2. 研究背景
3. 方法论分析
4. 结果与发现
5. 批判性讨论
6. 结论和建议

请使用Markdown格式。
"""
        }
        
        prompt = agent_prompts.get(agent_name, f"请分析以下研究问题：{user_input}")
        
        try:
            response = await self.llm_client.generate_text(
                prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            if response.success:
                return {
                    "agent": agent_name,
                    "content": response.content,
                    "status": "success",
                    "processing_time": response.response_time,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "agent": agent_name,
                    "content": f"Agent {agent_name} 处理失败: {response.error}",
                    "status": "error",
                    "error": response.error,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "agent": agent_name,
                "content": f"Agent {agent_name} 处理异常: {str(e)}",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _integrate_results(self, execution_results: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """整合所有Agent的结果"""
        logger.info(f"整合Agent结果: {session_id}")
        
        # 提取各Agent的结果
        agent_results = execution_results.get("agent_results", {})
        
        # 生成最终报告
        final_report = await self._generate_final_report(agent_results, session_id)
        
        # 构建完整响应
        integrated_result = {
            "success": True,
            "session_id": session_id,
            "final_report": final_report,
            "agent_logs": self._format_agent_logs(execution_results["execution_log"]),
            "summary": {
                "total_agents": len(agent_results),
                "successful_agents": len([r for r in agent_results.values() if r.get("status") == "success"]),
                "processing_time": sum([r.get("processing_time", 0) for r in agent_results.values()]),
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 发布任务完成事件
        await self.blackboard.publish_event(BlackboardEvent(
            event_type=EventType.TASK_COMPLETED,
            agent_id=self.agent_id,
            data=integrated_result
        ))
        
        return integrated_result
    
    async def _generate_final_report(self, agent_results: Dict[str, Any], session_id: str) -> str:
        """生成最终的综合报告"""
        
        # 提取各Agent的内容
        info_content = agent_results.get("information_enhanced", {}).get("content", "")
        verification_content = agent_results.get("verification", {}).get("content", "")
        critique_content = agent_results.get("critique", {}).get("content", "")
        report_content = agent_results.get("report", {}).get("content", "")
        
        # 如果报告Agent成功生成了报告，直接使用
        if report_content and agent_results.get("report", {}).get("status") == "success":
            return report_content
        
        # 否则，主Agent自己整合一个基础报告
        final_report = f"""# 多Agent协作研究报告

**会话ID**: {session_id}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🔍 信息调研结果
{info_content or "信息检索Agent未能成功完成任务"}

## ✅ 验证结果
{verification_content or "验证Agent未能成功完成任务"}

## 🔬 批判性分析
{critique_content or "批判Agent未能成功完成任务"}

## 📋 综合总结
基于多Agent协作分析，本次研究任务已完成。各Agent的协作结果已整合到上述各个部分中。

---
*本报告由科研多Agent系统自动生成*
"""
        
        return final_report
    
    def _format_agent_logs(self, execution_log: List[Dict]) -> List[Dict]:
        """格式化Agent执行日志"""
        formatted_logs = []
        
        agent_names = {
            "information_enhanced": "信息检索Agent",
            "verification": "验证Agent", 
            "critique": "批判Agent",
            "report": "报告生成Agent"
        }
        
        for log_entry in execution_log:
            agent_name = log_entry.get("agent", "")
            formatted_log = {
                "agent_name": agent_names.get(agent_name, agent_name),
                "stage": f"{agent_names.get(agent_name, agent_name)}处理",
                "content": f"Agent状态: {log_entry.get('status', 'unknown')}",
                "timestamp": log_entry.get("timestamp", ""),
                "status": log_entry.get("status", "unknown")
            }
            
            if log_entry.get("error"):
                formatted_log["content"] += f", 错误: {log_entry['error']}"
            
            formatted_logs.append(formatted_log)
        
        return formatted_logs
    
    def _estimate_complexity(self, user_input: str) -> float:
        """估算任务复杂度"""
        # 简单的复杂度估算
        complexity_indicators = [
            "实验设计", "数据分析", "建模", "算法", "优化",
            "深度学习", "机器学习", "人工智能", "大数据",
            "系统设计", "架构", "协议", "标准"
        ]
        
        input_lower = user_input.lower()
        matches = sum(1 for indicator in complexity_indicators if indicator in input_lower)
        
        # 基于匹配数量和文本长度估算复杂度
        length_factor = min(len(user_input) / 100, 1.0)
        keyword_factor = min(matches / len(complexity_indicators), 1.0)
        
        return (length_factor + keyword_factor) / 2
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        return self.active_sessions.get(session_id, {
            "status": "not_found",
            "message": "会话不存在"
        })
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理来自其他Agent的消息"""
        message_type = message.get("type", "")
        
        if message_type == "research_request":
            return await self.process_research_request(
                message.get("user_input", ""),
                message.get("session_id")
            )
        elif message_type == "get_session_status":
            return await self.get_session_status(message.get("session_id", ""))
        else:
            return {
                "success": False,
                "error": f"未知消息类型: {message_type}"
            }

    # 文件结束