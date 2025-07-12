"""
批判Agent - 负责对阶段性成果和最终方案进行审查、批评和改进建议
扮演AI团队中的"审稿人"或"质询专家"角色
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import uuid

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import Blackboard, BlackboardEvent, EventType, ReasoningStep


@dataclass
class CritiqueResult:
    """批判结果数据结构"""
    critique_id: str
    target_content: str
    critique_type: str  # logic, innovation, feasibility, ethics
    critique_text: str
    recommendation: str
    score: Dict[str, float]  # 各维度评分
    severity: str  # low, medium, high
    evidence: List[str]


class CritiqueAgent(BaseAgent):
    """
    批判Agent - 严谨的科研审稿人
    
    职责:
    - 逻辑审查: 检查推理逻辑的严谨性
    - 知识与证据检视: 确保论据充分
    - 伦理合规审视: 检查是否违反科研伦理
    - 建设性反馈: 提出改进建议
    - 质量评分: 对方案按维度打分
    """
    
    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="CritiqueAgent",
            agent_type="critic",
            description="批判Agent - 审稿人和质询专家",
            subscribed_events=[
                EventType.SOLUTION_DRAFT_CREATED,
                EventType.EXPERIMENT_PLAN,
                EventType.VERIFICATION_REPORT,
                EventType.CONFLICT_WARNING,
                EventType.TASK_ASSIGNED
            ],
            max_concurrent_tasks=3
        )
        super().__init__(config, blackboard, llm_client)
        
        # 评估维度和标准（符合文档要求的四维度评分）
        self.evaluation_dimensions = {
            "创新性": {
                "description": "方案的新颖性、独创性和突破性",
                "criteria": ["理论创新", "方法创新", "技术创新", "应用创新"],
                "weight": 0.3
            },
            "可行性": {
                "description": "方案的实际可操作性和技术可实现性",
                "criteria": ["技术可行性", "资源可行性", "时间可行性", "成本合理性"],
                "weight": 0.3
            },
            "完整性": {
                "description": "方案的全面性、完整性和逻辑严谨性",
                "criteria": ["逻辑完整性", "信息全面性", "方法完备性", "结论可靠性"],
                "weight": 0.2
            },
            "安全性": {
                "description": "方案的安全风险评估和伦理合规性",
                "criteria": ["实验安全", "数据安全", "伦理合规", "环境影响"],
                "weight": 0.2
            }
        }
        
        # 定义输入输出Schema
        self.input_schema = {
            "type": "object",
            "properties": {
                "draft_content": {"type": "string"},
                "draft_id": {"type": "string"},
                "experiment_plan": {"type": "string"},
                "information_sources": {"type": "array"}
            }
        }
        
        self.output_schema = {
            "type": "object",
            "properties": {
                "critique_type": {"type": "string"},
                "overall_assessment": {"type": "string"},
                "problems_found": {"type": "array"},
                "scores": {"type": "object"},
                "recommendations": {"type": "array"}
            },
            "required": ["critique_type", "overall_assessment"]
        }
        
    async def _load_prompt_templates(self):
        """加载批判Agent的Prompt模板"""
        self.prompt_templates = {
            "comprehensive_critique": """
系统：你是资深的科研批判专家，请对以下方案进行全面、深入的批判性评审。

方案内容：{solution_content}
研究背景：{research_context}
已知信息：{known_information}

请从以下维度进行深度批判：

1. **逻辑严密性审查**：
   - 推理过程是否严谨无漏洞
   - 假设前提是否合理充分
   - 结论是否必然从前提得出
   - 是否存在逻辑谬误（如循环论证、偷换概念等）

2. **创新性评估**：
   - 方案的核心创新点是什么
   - 与现有方案相比的独特性
   - 创新的价值和影响力评估
   - 是否真正解决了新问题或提供了新视角

3. **完整性检查**：
   - 方案是否涵盖了问题的所有重要方面
   - 是否有关键环节被忽略
   - 边界条件和特殊情况的考虑
   - 方案的系统性和全面性

4. **可行性深度分析**：
   - 技术实现的难点和挑战
   - 资源需求的合理性评估
   - 时间进度的现实性
   - 潜在障碍的识别和评估

5. **知识基础审查**：
   - 引用的理论和数据是否准确
   - 是否存在知识盲区或误解
   - 学科交叉的合理性
   - 前沿性和时效性评估

6. **风险和局限性**：
   - 方案的主要风险点
   - 固有局限性和适用范围
   - 失败可能性和后果评估
   - 伦理和社会影响考量

7. **改进潜力分析**：
   - 方案的优化空间
   - 可能的改进方向
   - 与其他方法的结合可能
   - 长期发展潜力

请以JSON格式返回批判结果：
{{
    "critique_summary": "总体批判意见概述",
    "overall_quality_score": 0-10的总体质量评分,
    "dimension_scores": {{
        "logical_rigor": 0-10,
        "innovation": 0-10,
        "completeness": 0-10,
        "feasibility": 0-10,
        "knowledge_foundation": 0-10,
        "risk_awareness": 0-10
    }},
    "critical_issues": [
        {{
            "issue": "关键问题描述",
            "severity": "高/中/低",
            "impact": "影响说明",
            "suggestion": "改进建议"
        }}
    ],
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["缺点1", "缺点2", "缺点3"],
    "improvement_recommendations": [
        {{
            "area": "改进领域",
            "specific_suggestion": "具体建议",
            "expected_benefit": "预期效果",
            "implementation_difficulty": "高/中/低"
        }}
    ],
    "innovation_assessment": {{
        "novelty_level": "突破性/渐进性/模仿性",
        "contribution_value": "高/中/低",
        "competitive_advantage": "竞争优势分析"
    }},
    "risk_assessment": {{
        "technical_risks": ["技术风险1", "技术风险2"],
        "resource_risks": ["资源风险1", "资源风险2"],
        "execution_risks": ["执行风险1", "执行风险2"],
        "mitigation_strategies": ["缓解策略1", "策略2"]
    }},
    "final_recommendation": "接受/有条件接受/需要重大修改/拒绝",
    "revision_priority": ["优先修改事项1", "事项2", "事项3"],
    "confidence": 0-1的批判置信度
}}
""",

            "innovation_critique": """
系统：你是创新评估专家，请专门评估方案的创新性。

方案内容：{content}
领域背景：{domain_context}

请深入分析：

1. **创新类型识别**：
   - 是原创性创新还是改进性创新？
   - 是技术创新、方法创新还是应用创新？
   - 创新的层次（基础理论/技术方法/工程应用）

2. **新颖性评估**：
   - 与现有方案的本质区别
   - 是否提出了新的概念或原理
   - 是否采用了新的技术路线

3. **创新价值分析**：
   - 解决了什么之前未解决的问题
   - 带来了什么新的可能性
   - 对领域发展的潜在贡献

4. **创新风险评估**：
   - 创新方案的不确定性
   - 可能的技术障碍
   - 市场或应用接受度

请以JSON格式返回：
{{
    "innovation_type": "原创性/改进性/组合性",
    "innovation_level": "突破性/显著/渐进/微小",
    "novelty_score": 0-10,
    "value_score": 0-10,
    "risk_score": 0-10,
    "key_innovations": ["创新点1", "创新点2"],
    "comparison_with_sota": "与最先进方案的对比",
    "potential_impact": "潜在影响描述",
    "recommendations": ["建议1", "建议2"]
}}
""",

            "feasibility_critique": """
系统：你是可行性分析专家，请深入评估方案的实际可行性。

方案内容：{content}
资源条件：{resource_context}

请从以下角度分析：

1. **技术可行性**：
   - 关键技术的成熟度
   - 技术整合的复杂度
   - 技术瓶颈和解决方案

2. **经济可行性**：
   - 成本效益分析
   - 投资回报评估
   - 经济风险因素

3. **操作可行性**：
   - 实施步骤的合理性
   - 人员技能要求
   - 管理复杂度

4. **时间可行性**：
   - 时间进度的现实性
   - 关键里程碑设置
   - 延期风险评估

请以JSON格式返回：
{{
    "overall_feasibility": "高/中/低",
    "feasibility_scores": {{
        "technical": 0-10,
        "economic": 0-10,
        "operational": 0-10,
        "temporal": 0-10
    }},
    "critical_challenges": ["挑战1", "挑战2"],
    "success_factors": ["成功因素1", "因素2"],
    "implementation_roadmap": "实施路线图建议",
    "alternative_approaches": ["备选方案1", "方案2"]
}}
""",

            "ethical_critique": """
系统：你是科研伦理专家，请评估方案的伦理合规性。

方案内容：{content}
研究类型：{research_type}

请检查以下伦理维度：

1. **研究伦理**：
   - 是否涉及人体或动物实验
   - 数据隐私和保护措施
   - 知情同意的必要性

2. **环境伦理**：
   - 对环境的潜在影响
   - 可持续性考虑
   - 生态风险评估

3. **社会伦理**：
   - 社会公平性影响
   - 潜在的负面社会效应
   - 公众接受度预测

4. **学术伦理**：
   - 学术诚信风险
   - 利益冲突声明
   - 成果归属问题

请以JSON格式返回：
{{
    "ethical_compliance": "完全合规/基本合规/存在问题/严重问题",
    "ethical_concerns": ["伦理关注点1", "关注点2"],
    "required_approvals": ["需要的批准1", "批准2"],
    "mitigation_measures": ["缓解措施1", "措施2"],
    "ethical_guidelines": ["适用的伦理准则1", "准则2"]
}}
"""
        }
    
    async def _process_event_impl(self, event: BlackboardEvent) -> Any:
        """处理批判相关事件"""
        try:
            # 记录事件处理推理步骤
            event_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="event_processing",
                description=f"处理{event.event_type.value}事件",
                input_data={"event_type": event.event_type.value, "source_agent": event.agent_id},
                reasoning_text=f"批判Agent收到{event.event_type.value}事件，开始进行批判性分析"
            )
            await self.blackboard.record_reasoning_step(event_step)
            
            if event.event_type == EventType.TASK_ASSIGNED:
                if event.target_agent == self.agent_id or event.data.get("task_type") == "critique":
                    return await self._handle_critique_task(event)
            elif event.event_type == EventType.SOLUTION_DRAFT_CREATED:
                return await self._critique_solution_draft(event.data)
            elif event.event_type == EventType.EXPERIMENT_PLAN:
                return await self._critique_experiment_plan(event.data)
            elif event.event_type == EventType.VERIFICATION_REPORT:
                return await self._analyze_verification_report(event.data)
            elif event.event_type == EventType.CONFLICT_WARNING:
                return await self._analyze_conflict(event.data)
            else:
                self.logger.warning(f"未处理的事件类型: {event.event_type}")
                
        except Exception as e:
            self.logger.error(f"批判处理失败: {e}")
            await self._publish_critique_error(event, str(e))

    async def _handle_critique_task(self, event: BlackboardEvent):
        """处理批判任务分配"""
        task_data = event.data
        session_id = event.session_id or "default"
        
        self.logger.info(f"开始批判分析任务: {task_data.get('user_input', '')[:50]}...")
        
        # 记录任务开始推理步骤
        task_start_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="task_start",
            description="开始批判分析任务",
            input_data=task_data,
            reasoning_text="收到批判任务，开始对前期Agent结果进行批判性分析"
        )
        await self.blackboard.record_reasoning_step(task_start_step)
        
        try:
            # 执行全面批判分析
            critique_result = await self._enhanced_critical_analysis(task_data, session_id)
            
            # 发布批判结果
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.CRITIQUE_FEEDBACK,
                agent_id=self.agent_id,
                session_id=session_id,
                data={
                    "critique_result": critique_result,
                    "task_completed": True,
                    "timestamp": datetime.now().isoformat()
                }
            ))
            
            # 记录任务完成推理步骤
            completion_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="completion",
                description="批判分析任务完成",
                input_data=task_data,
                output_data={"overall_score": critique_result.get("overall_score", 0)},
                reasoning_text="完成了全面的批判性分析，识别了优势、问题和改进建议",
                confidence=0.85
            )
            await self.blackboard.record_reasoning_step(completion_step)
            
            self.logger.info(f"批判分析完成，总评分: {critique_result.get('overall_score', 0)}")
            
            return critique_result
            
        except Exception as e:
            self.logger.error(f"批判任务失败: {e}")
            await self._publish_critique_error(event, str(e))
    
    async def _critique_solution_draft(self, data: Dict[str, Any]) -> None:
        """批判解决方案草案"""
        draft_id = data.get("draft_id")
        solution_content = data.get("solution_content", "")
        solution_type = data.get("solution_type", "general")
        session_id = data.get("session_id")
        
        self.logger.info(f"开始批判方案草案: {draft_id}")
        
        try:
            # 获取研究背景和已知信息
            research_context = await self.blackboard.get_data(f"session_{session_id}_info")
            known_information = await self.blackboard.get_data(f"session_{session_id}_analysis")
            
            # 执行全面批判
            comprehensive_prompt = self.format_prompt(
                "comprehensive_critique",
                solution_content=solution_content,
                research_context=json.dumps(research_context or {}, ensure_ascii=False),
                known_information=json.dumps(known_information or {}, ensure_ascii=False)
            )
            
            comprehensive_result = await self.call_llm(
                comprehensive_prompt,
                temperature=0.7,
                max_tokens=4000,
                response_format="json"
            )
            
            critique_data = json.loads(comprehensive_result)
            
            # 根据评分决定是否需要专项批判
            if critique_data.get("dimension_scores", {}).get("innovation", 0) < 7:
                # 创新性不足，进行专门的创新性批判
                innovation_prompt = self.format_prompt(
                    "innovation_critique",
                    content=solution_content,
                    domain_context=json.dumps(research_context or {}, ensure_ascii=False)
                )
                
                innovation_result = await self.call_llm(
                    innovation_prompt,
                    temperature=0.8,
                    response_format="json"
                )
                
                innovation_data = json.loads(innovation_result)
                critique_data["innovation_details"] = innovation_data
            
            if critique_data.get("dimension_scores", {}).get("feasibility", 0) < 7:
                # 可行性存疑，进行专门的可行性批判
                feasibility_prompt = self.format_prompt(
                    "feasibility_critique",
                    content=solution_content,
                    resource_context="{}"  # 可以从黑板获取资源信息
                )
                
                feasibility_result = await self.call_llm(
                    feasibility_prompt,
                    temperature=0.7,
                    response_format="json"
                )
                
                feasibility_data = json.loads(feasibility_result)
                critique_data["feasibility_details"] = feasibility_data
            
            # 构建批判结果
            critique_result = CritiqueResult(
                critique_id=str(uuid.uuid4()),
                target_content=solution_content,
                critique_type="comprehensive",
                critique_text=critique_data.get("critique_summary", ""),
                recommendation=critique_data.get("final_recommendation", "需要修改"),
                score=critique_data.get("dimension_scores", {}),
                severity=self._determine_severity(critique_data.get("critical_issues", [])),
                evidence=critique_data.get("strengths", []) + critique_data.get("weaknesses", [])
            )
            
            # 发布批判结果
            await self.publish_result(
                EventType.CRITIQUE_FEEDBACK,
                {
                    "draft_id": draft_id,
                    "critique_result": {
                        "critique_id": critique_result.critique_id,
                        "overall_score": critique_data.get("overall_quality_score", 0),
                        "dimension_scores": critique_data.get("dimension_scores", {}),
                        "critical_issues": critique_data.get("critical_issues", []),
                        "improvement_recommendations": critique_data.get("improvement_recommendations", []),
                        "final_recommendation": critique_data.get("final_recommendation", ""),
                        "revision_priority": critique_data.get("revision_priority", [])
                    },
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # 如果需要重大修改，发布警告
            if critique_data.get("final_recommendation") in ["需要重大修改", "拒绝"]:
                await self._publish_revision_warning(draft_id, critique_result)
            
            # 存储批判历史
            await self.blackboard.store_data(
                f"critique_{draft_id}",
                {
                    "critique_result": critique_data,
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.config.name
                }
            )
            
        except Exception as e:
            self.logger.error(f"批判方案失败: {e}")
            await self._publish_critique_error(
                BlackboardEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.SOLUTION_DRAFT_CREATED,
                    source_agent="unknown",
                    data=data,
                    timestamp=datetime.now()
                ),
                str(e)
            )
    
    async def _critique_experiment_plan(self, data: Dict[str, Any]) -> None:
        """批判实验方案"""
        plan_content = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 调用LLM进行实验方案批判
        prompt = self.format_prompt("experiment_critique", experiment_plan=plan_content)
        response = await self.call_llm(prompt, response_format="json")
        result = json.loads(response)
        
        # 发布批判结果
        await self.publish_result(
            EventType.CRITIQUE_FEEDBACK,
            {
                "target_type": "experiment_plan",
                "experiment_critique": result,
                "approval_status": result.get("approval_recommendation", "revise"),
                "timestamp": datetime.now().isoformat(),
                "critic": self.config.name
            }
        )
        
        # 如果不推荐通过，发布改进建议
        if result.get("approval_recommendation") in ["revise", "reject"]:
            await self._publish_improvement_suggestions(result)
    
    async def _analyze_verification_report(self, data: Dict[str, Any]) -> None:
        """分析验证报告并提供意见"""
        verification_results = data.get("verification_results", [])
        overall_status = data.get("overall_status", "unknown")
        
        # 基于验证结果给出批判意见
        critique_points = []
        
        for verification in verification_results:
            if verification.get("status") == "failed":
                critique_points.append(f"验证发现严重问题: {verification.get('verification_type')}")
            elif verification.get("status") == "warning":
                critique_points.append(f"验证发现潜在问题: {verification.get('verification_type')}")
        
        if critique_points:
            await self.publish_result(
                EventType.CRITIQUE_FEEDBACK,
                {
                    "target_verification": data.get("target_draft_id", ""),
                    "critique_points": critique_points,
                    "verification_analysis": "验证报告显示方案存在需要关注的问题",
                    "recommendations": ["根据验证结果修改方案", "加强相关方面的论证"],
                    "critic": self.config.name
                }
            )
    
    async def _analyze_conflict(self, data: Dict[str, Any]) -> None:
        """分析冲突并提供解决建议"""
        conflict_type = data.get("conflict_type", "")
        details = data.get("details", {})
        
        # 根据冲突类型提供不同的分析
        if conflict_type == "information_inconsistency":
            await self._handle_information_conflict(details)
        elif conflict_type == "verification_failed":
            await self._handle_verification_conflict(details)
        else:
            self.logger.info(f"分析其他类型冲突: {conflict_type}")
    
    async def _handle_information_conflict(self, details: Dict[str, Any]):
        """处理信息冲突"""
        affected_events = details.get("affected_events", [])
        
        # 获取冲突信息进行分析
        conflict_info = []
        for event_id in affected_events[-3:]:  # 分析最近3个相关事件
            # 这里应该从黑板获取具体事件信息
            conflict_info.append(f"事件 {event_id} 的相关信息")
        
        if conflict_info:
            prompt = self.format_prompt(
                "cross_validation",
                information_sources="\n".join(conflict_info)
            )
            
            response = await self.call_llm(prompt, response_format="json")
            result = json.loads(response)
            
            await self.publish_result(
                EventType.CRITIQUE_FEEDBACK,
                {
                    "conflict_analysis": result,
                    "conflict_resolution": "信息冲突分析完成",
                    "recommended_actions": result.get("resolution_suggestions", []),
                    "critic": self.config.name
                }
            )
    
    async def _handle_verification_conflict(self, details: Dict[str, Any]):
        """处理验证冲突"""
        critical_issues = details.get("critical_issues", [])
        
        await self.publish_result(
            EventType.CRITIQUE_FEEDBACK,
            {
                "verification_conflict_analysis": "验证发现严重问题需要立即处理",
                "critical_issues": critical_issues,
                "urgency_level": "high",
                "recommendations": [
                    "立即停止当前方案推进",
                    "重新审视方案设计",
                    "补充必要的安全措施"
                ],
                "critic": self.config.name
            }
        )
    
    def _determine_severity(self, problems: List[Dict[str, Any]]) -> str:
        """确定问题严重程度"""
        if not problems:
            return "low"
        
        high_severity_count = sum(1 for p in problems if p.get("severity") == "high")
        medium_severity_count = sum(1 for p in problems if p.get("severity") == "medium")
        
        if high_severity_count > 0:
            return "high"
        elif medium_severity_count > 1:
            return "medium"
        else:
            return "low"
    
    async def _publish_revision_warning(self, draft_id: str, critique_result: CritiqueResult):
        """发布修订警告"""
        await self.publish_result(
            EventType.CONFLICT_WARNING,
            {
                "conflict_type": "requires_major_revision",
                "target_draft_id": draft_id,
                "severity": critique_result.severity,
                "key_issues": critique_result.evidence,
                "recommendations": critique_result.recommendation,
                "requires_attention": True
            }
        )
    
    async def _publish_improvement_suggestions(self, critique_result: Dict[str, Any]):
        """发布改进建议"""
        await self.publish_result(
            EventType.CRITIQUE_FEEDBACK,
            {
                "improvement_focus": "实验方案需要改进",
                "safety_concerns": critique_result.get("safety_concerns", []),
                "methodological_issues": critique_result.get("methodological_issues", []),
                "improvement_suggestions": critique_result.get("improvement_suggestions", []),
                "priority": "high" if critique_result.get("approval_recommendation") == "reject" else "medium"
            }
        )
    
    async def _publish_critique_error(self, original_event: BlackboardEvent, error_msg: str):
        """发布批判错误"""
        await self.publish_result(
            EventType.CONFLICT_WARNING,
            {
                "conflict_type": "critique_error",
                "original_event_id": original_event.event_id,
                "error_message": error_msg,
                "requires_attention": True
            }
        )

    async def _enhanced_critical_analysis(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """增强的批判性分析"""
        try:
            # 1. 多维度质量评估
            quality_assessment = await self._multi_dimensional_quality_assessment(task_data, session_id)
            
            # 2. 逻辑一致性检查
            logical_consistency = await self._logical_consistency_check(task_data, session_id)
            
            # 3. 创新性评估
            innovation_assessment = await self._innovation_assessment(task_data, session_id)
            
            # 4. 可行性分析
            feasibility_analysis = await self._feasibility_analysis(task_data, session_id)
            
            # 5. 风险识别与评估
            risk_assessment = await self._risk_assessment(task_data, session_id)
            
            # 6. 改进建议生成
            improvement_suggestions = await self._generate_improvement_suggestions(
                quality_assessment, logical_consistency, innovation_assessment, 
                feasibility_analysis, risk_assessment, session_id
            )
            
            # 7. 综合评分计算
            overall_score = await self._calculate_comprehensive_score(
                quality_assessment, logical_consistency, innovation_assessment, 
                feasibility_analysis, risk_assessment, session_id
            )
            
            enhanced_critique = {
                "critique_id": f"enhanced_critique_{uuid.uuid4().hex[:8]}",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "enhanced_critical_analysis",
                "quality_assessment": quality_assessment,
                "logical_consistency": logical_consistency,
                "innovation_assessment": innovation_assessment,
                "feasibility_analysis": feasibility_analysis,
                "risk_assessment": risk_assessment,
                "improvement_suggestions": improvement_suggestions,
                "overall_score": overall_score,
                "confidence_level": self._calculate_confidence_level(task_data),
                "recommendation": self._generate_recommendation(overall_score)
            }
            
            # 记录增强批判分析
            await self._record_llm_chain_step(
                f"增强批判性分析完成: 综合评分 {overall_score}/10",
                f"改进建议: {len(improvement_suggestions)}条, 置信度: {enhanced_critique['confidence_level']}",
                session_id
            )
            
            return enhanced_critique
            
        except Exception as e:
            self.logger.error(f"增强批判性分析失败: {e}")
            return await self._basic_critical_analysis(task_data, session_id)

    async def _multi_dimensional_quality_assessment(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """多维度质量评估"""
        try:
            assessment_prompt = f"""
            对以下研究成果进行多维度质量评估：
            
            研究内容：{json.dumps(task_data, ensure_ascii=False, indent=2)[:1500]}
            
            请从以下维度进行评估（每个维度1-10分）：
            
            1. 科学严谨性 (Scientific Rigor)
               - 方法论的合理性
               - 数据的可靠性
               - 推理的逻辑性
            
            2. 内容完整性 (Content Completeness)
               - 覆盖范围的全面性
               - 关键要素的完备性
               - 细节的充分性
            
            3. 技术深度 (Technical Depth)
               - 技术分析的深度
               - 专业知识的运用
               - 复杂问题的处理
            
            4. 表达清晰度 (Expression Clarity)
               - 语言表达的清晰性
               - 结构组织的合理性
               - 概念阐述的准确性
            
            5. 参考文献质量 (Reference Quality)
               - 文献来源的权威性
               - 引用的相关性
               - 文献的时效性
            
            6. 数据支撑度 (Data Support)
               - 数据的充分性
               - 证据的说服力
               - 统计分析的合理性
            
            对每个维度，请提供：
            - 评分 (1-10)
            - 评估理由
            - 具体问题点
            - 改进空间
            
            以JSON格式返回评估结果。
            """
            
            response = await self.call_llm(
                assessment_prompt,
                temperature=0.2,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                quality_assessment = json.loads(response)
                return quality_assessment
            except json.JSONDecodeError:
                self.logger.warning("质量评估响应解析失败")
                return {"overall_quality": 5, "dimensions": {}}
            
        except Exception as e:
            self.logger.error(f"多维度质量评估失败: {e}")
            return {"overall_quality": 5, "dimensions": {}}

    async def _logical_consistency_check(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """逻辑一致性检查"""
        try:
            consistency_prompt = f"""
            检查以下研究内容的逻辑一致性：
            
            研究内容：{json.dumps(task_data, ensure_ascii=False, indent=2)[:1500]}
            
            请检查以下方面的逻辑一致性：
            
            1. 假设与结论的一致性
               - 基本假设是否合理
               - 结论是否从假设合理推导
               - 是否存在逻辑跳跃
            
            2. 方法与目标的一致性
               - 研究方法是否适合研究目标
               - 技术路径是否合理
               - 评估标准是否恰当
            
            3. 数据与分析的一致性
               - 数据是否支持分析结论
               - 分析方法是否适合数据类型
               - 是否存在数据误用
            
            4. 内部论证的一致性
               - 各部分论述是否自洽
               - 是否存在自相矛盾
               - 论证链条是否完整
            
            5. 外部参照的一致性
               - 与已有研究的一致性
               - 与理论框架的符合度
               - 与实际情况的吻合度
            
            对每个方面，请提供：
            - 一致性评分 (1-10)
            - 发现的问题
            - 问题严重程度
            - 修正建议
            
            以JSON格式返回检查结果。
            """
            
            response = await self.call_llm(
                consistency_prompt,
                temperature=0.1,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                consistency_check = json.loads(response)
                return consistency_check
            except json.JSONDecodeError:
                self.logger.warning("逻辑一致性检查响应解析失败")
                return {"overall_consistency": 7, "issues": []}
            
        except Exception as e:
            self.logger.error(f"逻辑一致性检查失败: {e}")
            return {"overall_consistency": 7, "issues": []}

    async def _innovation_assessment(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """创新性评估"""
        try:
            innovation_prompt = f"""
            评估以下研究内容的创新性：
            
            研究内容：{json.dumps(task_data, ensure_ascii=False, indent=2)[:1500]}
            
            请从以下角度评估创新性：
            
            1. 概念创新 (Conceptual Innovation)
               - 是否提出新概念或理论
               - 概念的原创性程度
               - 理论贡献的价值
            
            2. 方法创新 (Methodological Innovation)
               - 是否采用新的研究方法
               - 方法的创新程度
               - 技术路径的新颖性
            
            3. 应用创新 (Application Innovation)
               - 是否开拓新的应用领域
               - 应用场景的创新性
               - 实际价值的突破性
            
            4. 跨学科创新 (Interdisciplinary Innovation)
               - 是否实现跨学科融合
               - 融合的深度和广度
               - 交叉创新的价值
            
            5. 技术创新 (Technical Innovation)
               - 技术方案的创新性
               - 技术突破的程度
               - 实现难度与价值
            
            对每个角度，请提供：
            - 创新性评分 (1-10)
            - 创新点描述
            - 创新程度评估
            - 潜在影响预测
            
            以JSON格式返回评估结果。
            """
            
            response = await self.call_llm(
                innovation_prompt,
                temperature=0.3,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                innovation_assessment = json.loads(response)
                return innovation_assessment
            except json.JSONDecodeError:
                self.logger.warning("创新性评估响应解析失败")
                return {"overall_innovation": 6, "innovation_points": []}
            
        except Exception as e:
            self.logger.error(f"创新性评估失败: {e}")
            return {"overall_innovation": 6, "innovation_points": []}

    async def _feasibility_analysis(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """可行性分析"""
        try:
            feasibility_prompt = f"""
            分析以下研究方案的可行性：
            
            研究内容：{json.dumps(task_data, ensure_ascii=False, indent=2)[:1500]}
            
            请从以下维度分析可行性：
            
            1. 技术可行性 (Technical Feasibility)
               - 技术方案的成熟度
               - 实现的技术难度
               - 所需技术资源
            
            2. 资源可行性 (Resource Feasibility)
               - 人力资源需求
               - 设备和工具需求
               - 资金需求评估
            
            3. 时间可行性 (Time Feasibility)
               - 研究周期的合理性
               - 各阶段时间分配
               - 关键路径分析
            
            4. 环境可行性 (Environmental Feasibility)
               - 外部环境支持
               - 政策法规符合性
               - 伦理道德考量
            
            5. 市场可行性 (Market Feasibility)
               - 应用前景分析
               - 市场需求评估
               - 商业化潜力
            
            对每个维度，请提供：
            - 可行性评分 (1-10)
            - 主要挑战
            - 风险因素
            - 解决方案建议
            
            以JSON格式返回分析结果。
            """
            
            response = await self.call_llm(
                feasibility_prompt,
                temperature=0.2,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                feasibility_analysis = json.loads(response)
                return feasibility_analysis
            except json.JSONDecodeError:
                self.logger.warning("可行性分析响应解析失败")
                return {"overall_feasibility": 7, "challenges": []}
            
        except Exception as e:
            self.logger.error(f"可行性分析失败: {e}")
            return {"overall_feasibility": 7, "challenges": []}

    async def _risk_assessment(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """风险识别与评估"""
        try:
            risk_prompt = f"""
            识别和评估以下研究方案的风险：
            
            研究内容：{json.dumps(task_data, ensure_ascii=False, indent=2)[:1500]}
            
            请识别以下类型的风险：
            
            1. 技术风险 (Technical Risks)
               - 技术实现失败的可能性
               - 技术路径选择错误
               - 技术更新换代风险
            
            2. 资源风险 (Resource Risks)
               - 资源不足的风险
               - 成本超支风险
               - 人员流失风险
            
            3. 时间风险 (Schedule Risks)
               - 进度延误风险
               - 关键节点失控
               - 时间窗口错失
            
            4. 质量风险 (Quality Risks)
               - 研究质量不达标
               - 结果可靠性问题
               - 重现性风险
            
            5. 外部风险 (External Risks)
               - 政策环境变化
               - 竞争对手超越
               - 市场需求变化
            
            对每个风险，请提供：
            - 风险等级 (低/中/高)
            - 发生概率 (1-10)
            - 影响程度 (1-10)
            - 风险描述
            - 预防措施
            - 应对策略
            
            以JSON格式返回风险评估结果。
            """
            
            response = await self.call_llm(
                risk_prompt,
                temperature=0.2,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                risk_assessment = json.loads(response)
                return risk_assessment
            except json.JSONDecodeError:
                self.logger.warning("风险评估响应解析失败")
                return {"overall_risk": "medium", "risks": []}
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            return {"overall_risk": "medium", "risks": []}

    async def _generate_improvement_suggestions(self, quality_assessment: Dict[str, Any], 
                                              logical_consistency: Dict[str, Any],
                                              innovation_assessment: Dict[str, Any],
                                              feasibility_analysis: Dict[str, Any],
                                              risk_assessment: Dict[str, Any],
                                              session_id: str) -> List[Dict[str, Any]]:
        """生成改进建议"""
        try:
            improvement_prompt = f"""
            基于以下综合分析结果，生成具体的改进建议：
            
            质量评估：{json.dumps(quality_assessment, ensure_ascii=False, indent=2)[:500]}
            逻辑一致性：{json.dumps(logical_consistency, ensure_ascii=False, indent=2)[:500]}
            创新性评估：{json.dumps(innovation_assessment, ensure_ascii=False, indent=2)[:500]}
            可行性分析：{json.dumps(feasibility_analysis, ensure_ascii=False, indent=2)[:500]}
            风险评估：{json.dumps(risk_assessment, ensure_ascii=False, indent=2)[:500]}
            
            请生成具体的改进建议，包括：
            
            1. 优先级改进建议（高优先级）
               - 需要立即解决的关键问题
               - 具体改进措施
               - 预期改进效果
            
            2. 质量提升建议（中优先级）
               - 质量改进的具体方向
               - 实施步骤和方法
               - 质量控制措施
            
            3. 创新增强建议（中优先级）
               - 创新点的进一步发掘
               - 创新方法的改进
               - 创新价值的提升
            
            4. 风险缓解建议（根据风险等级）
               - 高风险的缓解措施
               - 预防性措施
               - 应急预案
            
            5. 长期优化建议（低优先级）
               - 长期发展方向
               - 持续改进机制
               - 未来拓展可能
            
            对每个建议，请提供：
            - 建议类型
            - 优先级
            - 具体措施
            - 实施难度
            - 预期效果
            - 所需资源
            
            以JSON格式返回改进建议列表。
            """
            
            response = await self.call_llm(
                improvement_prompt,
                temperature=0.4,
                max_tokens=2500,
                response_format="json",
                session_id=session_id
            )
            
            try:
                improvement_suggestions = json.loads(response)
                if isinstance(improvement_suggestions, list):
                    return improvement_suggestions
                else:
                    return []
            except json.JSONDecodeError:
                self.logger.warning("改进建议生成响应解析失败")
                return []
            
        except Exception as e:
            self.logger.error(f"改进建议生成失败: {e}")
            return []

    async def _calculate_comprehensive_score(self, quality_assessment: Dict[str, Any], 
                                           logical_consistency: Dict[str, Any],
                                           innovation_assessment: Dict[str, Any],
                                           feasibility_analysis: Dict[str, Any],
                                           risk_assessment: Dict[str, Any],
                                           session_id: str) -> float:
        """计算综合评分"""
        try:
            # 权重配置
            weights = {
                "quality": 0.25,
                "logic": 0.20,
                "innovation": 0.20,
                "feasibility": 0.20,
                "risk": 0.15
            }
            
            # 提取各维度评分
            quality_score = quality_assessment.get("overall_quality", 5)
            logic_score = logical_consistency.get("overall_consistency", 7)
            innovation_score = innovation_assessment.get("overall_innovation", 6)
            feasibility_score = feasibility_analysis.get("overall_feasibility", 7)
            
            # 风险评分转换（风险越高，评分越低）
            risk_level = risk_assessment.get("overall_risk", "medium")
            risk_score = {"low": 9, "medium": 6, "high": 3}.get(risk_level, 6)
            
            # 计算加权平均
            comprehensive_score = (
                quality_score * weights["quality"] +
                logic_score * weights["logic"] +
                innovation_score * weights["innovation"] +
                feasibility_score * weights["feasibility"] +
                risk_score * weights["risk"]
            )
            
            return round(comprehensive_score, 2)
            
        except Exception as e:
            self.logger.error(f"综合评分计算失败: {e}")
            return 6.0

    def _calculate_confidence_level(self, task_data: Dict[str, Any]) -> str:
        """计算置信度等级"""
        try:
            # 基于数据完整性和来源可靠性计算置信度
            data_completeness = len(str(task_data)) / 1000  # 简单的数据完整性指标
            
            if data_completeness >= 2.0:
                return "high"
            elif data_completeness >= 1.0:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            self.logger.error(f"置信度计算失败: {e}")
            return "medium"

    def _generate_recommendation(self, overall_score: float) -> str:
        """生成推荐建议"""
        try:
            if overall_score >= 8.0:
                return "excellent - 建议直接推进实施"
            elif overall_score >= 7.0:
                return "good - 建议适当优化后实施"
            elif overall_score >= 6.0:
                return "acceptable - 建议重点改进后实施"
            elif overall_score >= 5.0:
                return "needs_improvement - 建议大幅改进后再考虑实施"
            else:
                return "poor - 建议重新设计方案"
                
        except Exception as e:
            self.logger.error(f"推荐建议生成失败: {e}")
            return "needs_review - 需要进一步评估"

    async def _basic_critical_analysis(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """基础批判性分析（降级方案）"""
        try:
            basic_prompt = f"""
            对以下研究内容进行批判性分析：
            
            {json.dumps(task_data, ensure_ascii=False, indent=2)[:1000]}
            
            请提供：
            1. 主要优点
            2. 主要问题
            3. 改进建议
            4. 整体评价
            """
            
            response = await self.call_llm(
                basic_prompt,
                temperature=0.3,
                max_tokens=1000,
                session_id=session_id
            )
            
            return {
                "critique_id": f"basic_critique_{uuid.uuid4().hex[:8]}",
                "session_id": session_id,
                "analysis_type": "basic_critical_analysis",
                "content": response,
                "overall_score": 6.0,
                "recommendation": "needs_review"
            }
            
        except Exception as e:
            self.logger.error(f"基础批判性分析失败: {e}")
            return {"error": str(e)} 