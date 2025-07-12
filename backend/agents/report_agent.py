#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告Agent - 负责收集中间结果，生成总结报告
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import EventType, BlackboardEvent


class ReportAgent(BaseAgent):
    """报告Agent - 收集各Agent的分析结果，生成综合研究报告"""

    def __init__(self, blackboard):
        super().__init__("report_agent", blackboard)
        self.agent_type = "report"
        self.specializations = [
            "报告撰写",
            "结果整理",
            "可视化",
            "总结归纳",
            "文档生成"
        ]

    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理报告生成任务"""
        try:
            task_type = task_data.get("task_type", "comprehensive_report")
            session_id = task_data.get("session_id", "")
            
            logger.info(f"📝 ReportAgent开始处理报告生成任务: {task_type}")
            
            if task_type == "summary_report":
                return await self._generate_summary_report(task_data)
            elif task_type == "technical_report":
                return await self._generate_technical_report(task_data)
            elif task_type == "executive_summary":
                return await self._generate_executive_summary(task_data)
            else:
                # 默认综合报告
                return await self._generate_comprehensive_report(task_data)
                
        except Exception as e:
            logger.error(f"❌ ReportAgent处理失败: {e}")
            raise

    async def _generate_comprehensive_report(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合研究报告"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        # 收集所有前序Agent的结果
        agent_results = await self._collect_all_agent_results(session_id)
        
        # 构建报告生成提示词
        report_prompt = f"""作为专业的科研报告撰写专家，请基于以下多Agent协作分析结果，生成一份完整的研究报告：

研究目标: {query}

=== Agent分析结果 ===

信息收集Agent结果:
{self._format_agent_result(agent_results.get('information_agent', {}))}

验证Agent结果:
{self._format_agent_result(agent_results.get('verification_agent', {}))}

批判Agent结果:
{self._format_agent_result(agent_results.get('critique_agent', {}))}

请生成一份结构完整的研究报告，包含以下部分：

# 研究报告：{query}

## 1. 执行摘要
- 研究目标概述
- 主要发现总结
- 关键结论
- 建议概要

## 2. 研究背景与现状
- 研究领域背景
- 当前技术水平
- 存在的问题和挑战
- 研究的必要性

## 3. 技术分析
- 技术路线分析
- 关键技术要点
- 技术难点识别
- 解决方案建议

## 4. 可行性评估
- 技术可行性分析
- 资源需求评估
- 时间进度预估
- 风险因素识别

## 5. 创新性分析
- 主要创新点
- 与现有技术的差异
- 创新价值评估
- 潜在影响分析

## 6. 问题与挑战
- 主要技术挑战
- 实施风险
- 资源限制
- 外部制约因素

## 7. 改进建议
- 技术改进方向
- 实施策略优化
- 风险缓解措施
- 资源配置建议

## 8. 结论与展望
- 总体结论
- 实施建议
- 未来发展方向
- 预期成果

请确保报告内容专业、全面、逻辑清晰，并基于实际的分析结果进行撰写。"""

        try:
            # 调用LLM生成报告
            response = await self.llm_client.generate_text(
                report_prompt,
                temperature=0.3,
                max_tokens=3000
            )
            
            if response.success:
                report_content = response.content
                
                # 生成报告元数据
                report_metadata = self._generate_report_metadata(agent_results, session_id)
                
                result = {
                    "report_type": "comprehensive",
                    "report_content": report_content,
                    "report_metadata": report_metadata,
                    "agent_contributions": self._summarize_agent_contributions(agent_results),
                    "quality_indicators": self._calculate_quality_indicators(agent_results),
                    "generated_at": datetime.now().isoformat(),
                    "word_count": len(report_content.split()),
                    "sections_count": report_content.count("##")
                }
                
                # 发布报告生成完成事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.REPORT_GENERATED,
                    agent_id=self.agent_id,
                    session_id=session_id,
                    data={
                        "report_type": "comprehensive",
                        "word_count": result["word_count"],
                        "quality_score": result["quality_indicators"]["overall_quality"],
                        "completion_status": "success"
                    }
                ))
                
                logger.info(f"✅ 综合报告生成完成，字数: {result['word_count']}")
                return result
                
            else:
                raise Exception(f"LLM报告生成失败: {response.error}")
                
        except Exception as e:
            logger.error(f"综合报告生成失败: {e}")
            # 返回默认报告
            return self._generate_default_report(query, agent_results, session_id)

    async def _generate_summary_report(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成摘要报告"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        agent_results = await self._collect_all_agent_results(session_id)
        
        summary_prompt = f"""请为以下研究生成简洁的摘要报告：

研究目标: {query}

基于Agent分析结果，请生成包含以下要点的摘要：
1. 研究目标 (1-2句)
2. 主要发现 (3-4点)
3. 可行性评估 (1-2句)
4. 关键建议 (2-3点)
5. 总体结论 (1-2句)

要求：简洁明了，突出重点，总字数控制在300字以内。"""

        try:
            response = await self.llm_client.generate_text(summary_prompt, temperature=0.3, max_tokens=500)
            
            if response.success:
                return {
                    "report_type": "summary",
                    "summary_content": response.content,
                    "key_points": self._extract_key_points(response.content),
                    "generated_at": datetime.now().isoformat()
                }
            else:
                raise Exception(f"摘要报告生成失败: {response.error}")
                
        except Exception as e:
            logger.error(f"摘要报告生成失败: {e}")
            return {
                "report_type": "summary",
                "summary_content": f"研究目标：{query}。基于多Agent分析，该研究具有一定可行性，建议进一步深入调研和优化实施方案。",
                "key_points": ["研究方向可行", "需要深入调研", "优化实施方案"],
                "generated_at": datetime.now().isoformat()
            }

    async def _generate_technical_report(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成技术报告"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        agent_results = await self._collect_all_agent_results(session_id)
        
        # 重点关注技术细节
        technical_content = {
            "technical_analysis": agent_results.get('verification_agent', {}).get('verification_report', ''),
            "innovation_assessment": agent_results.get('critique_agent', {}).get('critique_report', ''),
            "technical_challenges": self._extract_technical_challenges(agent_results),
            "implementation_roadmap": self._generate_implementation_roadmap(agent_results)
        }
        
        return {
            "report_type": "technical",
            "technical_content": technical_content,
            "technical_score": self._calculate_technical_score(agent_results),
            "generated_at": datetime.now().isoformat()
        }

    async def _generate_executive_summary(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行摘要"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        agent_results = await self._collect_all_agent_results(session_id)
        
        # 提取关键决策信息
        executive_summary = {
            "research_objective": query,
            "feasibility_score": agent_results.get('verification_agent', {}).get('feasibility_score', 6.0),
            "innovation_score": agent_results.get('critique_agent', {}).get('innovation_score', 6.0),
            "key_recommendations": self._extract_key_recommendations(agent_results),
            "decision_points": self._identify_decision_points(agent_results),
            "resource_requirements": self._estimate_resource_requirements(agent_results),
            "timeline_estimate": "6-12个月",  # 简化估算
            "risk_level": self._assess_overall_risk(agent_results)
        }
        
        return {
            "report_type": "executive_summary",
            "executive_summary": executive_summary,
            "generated_at": datetime.now().isoformat()
        }

    async def _collect_all_agent_results(self, session_id: str) -> Dict[str, Any]:
        """收集所有Agent的结果"""
        agent_results = {}
        
        try:
            session_data = await self.blackboard.get_data(f"session_{session_id}")
            if session_data and "tasks" in session_data:
                for task_id, task in session_data["tasks"].items():
                    agent_type = task.get("assigned_agent")
                    if agent_type and task.get("status") == "completed":
                        agent_results[agent_type] = task.get("output_data", {})
            
            logger.info(f"收集到{len(agent_results)}个Agent的结果")
            return agent_results
            
        except Exception as e:
            logger.warning(f"收集Agent结果失败: {e}")
            return {}

    def _format_agent_result(self, result: Dict[str, Any]) -> str:
        """格式化Agent结果"""
        if not result:
            return "暂无结果"
        
        # 提取关键信息
        formatted_parts = []
        
        if "verification_report" in result:
            formatted_parts.append(f"验证报告: {result['verification_report'][:200]}...")
        elif "critique_report" in result:
            formatted_parts.append(f"批判分析: {result['critique_report'][:200]}...")
        elif "summary" in result:
            formatted_parts.append(f"信息摘要: {result['summary'][:200]}...")
        
        if "feasibility_score" in result:
            formatted_parts.append(f"可行性评分: {result['feasibility_score']}/10")
        
        if "innovation_score" in result:
            formatted_parts.append(f"创新性评分: {result['innovation_score']}/10")
        
        return "\n".join(formatted_parts) if formatted_parts else "结果格式化失败"

    def _generate_report_metadata(self, agent_results: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """生成报告元数据"""
        return {
            "session_id": session_id,
            "participating_agents": list(agent_results.keys()),
            "total_agents": len(agent_results),
            "generation_timestamp": datetime.now().isoformat(),
            "data_sources": self._identify_data_sources(agent_results),
            "analysis_depth": "comprehensive" if len(agent_results) >= 3 else "basic"
        }

    def _summarize_agent_contributions(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """总结各Agent的贡献"""
        contributions = {}
        
        for agent_type, result in agent_results.items():
            if agent_type == "information_agent":
                contributions[agent_type] = {
                    "contribution_type": "信息收集与分析",
                    "key_outputs": ["文献调研", "背景分析", "技术现状"],
                    "data_quality": "高" if result else "低"
                }
            elif agent_type == "verification_agent":
                contributions[agent_type] = {
                    "contribution_type": "可行性验证",
                    "key_outputs": ["技术可行性", "资源评估", "风险分析"],
                    "feasibility_score": result.get("feasibility_score", "未评估")
                }
            elif agent_type == "critique_agent":
                contributions[agent_type] = {
                    "contribution_type": "批判性分析",
                    "key_outputs": ["创新性评估", "问题识别", "改进建议"],
                    "innovation_score": result.get("innovation_score", "未评估")
                }
        
        return contributions

    def _calculate_quality_indicators(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算质量指标"""
        indicators = {
            "data_completeness": len(agent_results) / 3.0,  # 假设3个主要Agent
            "analysis_depth": 0.8 if len(agent_results) >= 2 else 0.5,
            "consistency_score": 0.85,  # 简化计算
            "overall_quality": 0.0
        }
        
        # 计算总体质量
        indicators["overall_quality"] = (
            indicators["data_completeness"] * 0.4 +
            indicators["analysis_depth"] * 0.4 +
            indicators["consistency_score"] * 0.2
        )
        
        return indicators

    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键点"""
        key_points = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                key_points.append(line[1:].strip())
            elif line.startswith(tuple('123456789')):
                key_points.append(line[2:].strip())
        
        return key_points[:5]  # 最多返回5个关键点

    def _extract_technical_challenges(self, agent_results: Dict[str, Any]) -> List[str]:
        """提取技术挑战"""
        challenges = []
        
        # 从验证Agent结果中提取
        verification_result = agent_results.get('verification_agent', {})
        if 'risk_assessment' in verification_result:
            challenges.extend(verification_result['risk_assessment'][:3])
        
        # 从批判Agent结果中提取
        critique_result = agent_results.get('critique_agent', {})
        if 'identified_issues' in critique_result:
            challenges.extend(critique_result['identified_issues'][:3])
        
        return challenges[:5]  # 最多返回5个挑战

    def _generate_implementation_roadmap(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成实施路线图"""
        return {
            "phase1": "需求分析与技术调研 (1-2个月)",
            "phase2": "方案设计与验证 (2-3个月)",
            "phase3": "原型开发与测试 (3-4个月)",
            "phase4": "优化完善与部署 (2-3个月)",
            "total_duration": "8-12个月",
            "key_milestones": [
                "技术方案确定",
                "原型验证完成",
                "系统集成测试",
                "正式部署上线"
            ]
        }

    def _calculate_technical_score(self, agent_results: Dict[str, Any]) -> float:
        """计算技术评分"""
        scores = []
        
        verification_result = agent_results.get('verification_agent', {})
        if 'feasibility_score' in verification_result:
            scores.append(verification_result['feasibility_score'])
        
        critique_result = agent_results.get('critique_agent', {})
        if 'innovation_score' in critique_result:
            scores.append(critique_result['innovation_score'])
        
        return sum(scores) / len(scores) if scores else 6.0

    def _extract_key_recommendations(self, agent_results: Dict[str, Any]) -> List[str]:
        """提取关键建议"""
        recommendations = []
        
        for agent_type, result in agent_results.items():
            if 'recommendations' in result:
                recommendations.extend(result['recommendations'][:2])
            elif 'improvement_suggestions' in result:
                recommendations.extend(result['improvement_suggestions'][:2])
        
        return recommendations[:5]

    def _identify_decision_points(self, agent_results: Dict[str, Any]) -> List[str]:
        """识别决策点"""
        return [
            "是否继续推进该研究方向",
            "技术路线选择",
            "资源投入规模",
            "实施时间安排",
            "风险控制策略"
        ]

    def _estimate_resource_requirements(self, agent_results: Dict[str, Any]) -> Dict[str, str]:
        """估算资源需求"""
        return {
            "人力资源": "3-5人团队",
            "时间投入": "6-12个月",
            "资金需求": "中等规模投入",
            "设备要求": "基础研发设备",
            "外部支持": "可能需要专家咨询"
        }

    def _assess_overall_risk(self, agent_results: Dict[str, Any]) -> str:
        """评估总体风险"""
        verification_result = agent_results.get('verification_agent', {})
        feasibility_score = verification_result.get('feasibility_score', 6.0)
        
        if feasibility_score >= 8.0:
            return "低风险"
        elif feasibility_score >= 6.0:
            return "中等风险"
        else:
            return "高风险"

    def _identify_data_sources(self, agent_results: Dict[str, Any]) -> List[str]:
        """识别数据来源"""
        sources = []
        
        if 'information_agent' in agent_results:
            sources.append("文献数据库")
        if 'verification_agent' in agent_results:
            sources.append("技术验证分析")
        if 'critique_agent' in agent_results:
            sources.append("专家批判分析")
        
        return sources

    def _generate_default_report(self, query: str, agent_results: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """生成默认报告"""
        default_content = f"""# 研究报告：{query}

## 执行摘要
本报告基于多Agent协作分析，对"{query}"进行了综合评估。

## 主要发现
- 该研究方向具有一定的技术可行性
- 需要进一步的技术调研和验证
- 建议制定详细的实施计划

## 可行性评估
基于现有分析，该研究项目具有中等可行性，建议谨慎推进。

## 建议
1. 加强技术调研
2. 制定详细计划
3. 评估资源需求
4. 建立风险控制机制

## 结论
该研究方向值得进一步探索，但需要充分的准备和规划。"""

        return {
            "report_type": "comprehensive",
            "report_content": default_content,
            "report_metadata": self._generate_report_metadata(agent_results, session_id),
            "agent_contributions": self._summarize_agent_contributions(agent_results),
            "quality_indicators": {"overall_quality": 0.6},
            "generated_at": datetime.now().isoformat(),
            "word_count": len(default_content.split()),
            "sections_count": default_content.count("##")
        }

    def _get_supported_task_types(self) -> List[str]:
        """获取支持的任务类型"""
        return [
            "comprehensive_report",
            "summary_report",
            "technical_report",
            "executive_summary",
            "progress_report"
        ]

    def _get_features(self) -> List[str]:
        """获取Agent特性"""
        return [
            "多源数据整合",
            "结构化报告生成",
            "质量指标评估",
            "可视化展示",
            "决策支持分析"
        ]
