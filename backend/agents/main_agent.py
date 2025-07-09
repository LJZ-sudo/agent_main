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
from ..core.blackboard import BlackboardEvent, EventType


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
        """分析任务并制定计划"""
        logger.info(f"分析任务: {user_input[:30]}...")
        
        # 发布任务开始事件
        await self.blackboard.publish_event(BlackboardEvent(
            event_type=EventType.TASK_STARTED,
            agent_id=self.agent_id,
            data={
                "session_id": session_id,
                "user_input": user_input,
                "stage": "task_analysis"
            }
        ))
        
        # 使用LLM分析用户输入
        analysis_prompt = f"""
作为科研多Agent系统的主协调者，请分析以下研究请求并制定执行计划：

用户请求: {user_input}

请分析：
1. 研究问题的类型和复杂度
2. 需要调用哪些Agent（信息检索、验证、批判、报告生成等）
3. Agent协作的优先级和顺序
4. 预期的输出格式

请以JSON格式返回分析结果。
"""
        
        try:
            analysis_response = await self.llm_client.generate_text(
                analysis_prompt,
                temperature=0.3,
                max_tokens=1000
            )
            
            if analysis_response.success:
                task_plan = {
                    "session_id": session_id,
                    "user_input": user_input,
                    "analysis": analysis_response.content,
                    "required_agents": ["information_enhanced", "verification", "critique", "report"],
                    "execution_order": ["information_enhanced", "verification", "critique", "report"],
                    "estimated_complexity": self._estimate_complexity(user_input),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"任务分析完成: {len(task_plan['required_agents'])}个Agent需要参与")
                return task_plan
            else:
                logger.error(f"LLM分析失败: {analysis_response.error}")
                return {
                        "session_id": session_id,
                    "user_input": user_input,
                    "analysis": f"基础分析：{user_input}",
                    "required_agents": ["information_enhanced", "verification", "critique", "report"],
                    "execution_order": ["information_enhanced", "verification", "critique", "report"],
                    "estimated_complexity": 0.5,
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            logger.error(f"任务分析异常: {e}")
            return {
                "session_id": session_id,
                "user_input": user_input,
                "analysis": f"简化分析：{user_input}",
                "required_agents": ["information_enhanced", "verification", "critique", "report"],
                "execution_order": ["information_enhanced", "verification", "critique", "report"],
                "estimated_complexity": 0.5,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_task_plan(self, task_plan: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """执行任务计划"""
        logger.info(f"开始执行任务计划: {session_id}")
        
        execution_results = {
            "session_id": session_id,
            "agent_results": {},
            "execution_log": [],
            "timestamp": datetime.now().isoformat()
        }
        
                # 按顺序执行Agent任务
        for agent_name in task_plan["execution_order"]:
            try:
                logger.info(f"调用 {agent_name} Agent...")
                
                # 发布Agent任务事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.TASK_ASSIGNED,
                    agent_id=self.agent_id,
                    target_agent=agent_name,
                    data={
                        "session_id": session_id,
                        "task_type": agent_name,
                        "user_input": task_plan["user_input"]
                    }
                ))
                
                # 使用LLM处理Agent任务（在专门Agent不可用时的替代方案）
                agent_result = await self._process_agent_task_with_llm(
                    agent_name, 
                    task_plan["user_input"], 
                    execution_results.get("agent_results", {}),
                    session_id
                )
                
                execution_results["agent_results"][agent_name] = agent_result
                execution_results["execution_log"].append({
                    "agent": agent_name,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"{agent_name} Agent处理完成")

            except Exception as e:
                logger.error(f"{agent_name} Agent处理失败: {e}")
                execution_results["execution_log"].append({
                    "agent": agent_name,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return execution_results
    
    async def _process_agent_task_with_llm(self, agent_name: str, user_input: str, previous_results: Dict, session_id: str) -> Dict[str, Any]:
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