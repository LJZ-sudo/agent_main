"""
验证Agent - 负责验证方案可行性和一致性检查
充当系统的"审计员"，发现明显错误和不可行之处
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re
import uuid

from core.base_agent import LLMBaseAgent, AgentConfig
from core.blackboard import Blackboard, BlackboardEvent, EventType


@dataclass
class VerificationResult:
    """验证结果数据结构"""
    verification_id: str
    target_content: str
    verification_type: str  # consistency, feasibility, safety
    status: str  # passed, warning, failed
    issues_found: List[str]
    recommendations: List[str]
    confidence_score: float
    evidence: List[str]


class VerificationAgent(LLMBaseAgent):
    """
    验证Agent - 核实方案的可行性和一致性
    
    职责:
    - 检查方案的事实准确性
    - 发现不同来源信息间的矛盾
    - 验证实验方案的可操作性
    - 评估安全合规性
    """
    
    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="VerificationAgent",
            agent_type="verifier",
            description="验证Agent - 可行性和一致性检查",
            subscribed_events=[
                EventType.SOLUTION_DRAFT_CREATED,
                EventType.EXPERIMENT_PLAN,
                EventType.INFORMATION_UPDATE,
                EventType.MODEL_RESULT
            ],
            max_concurrent_tasks=3
        )
        super().__init__(config, blackboard, llm_client)
        
        # 验证规则和知识库
        self.verification_rules = {
            "safety_keywords": ["高温", "高压", "有毒", "易燃", "易爆", "强酸", "强碱"],
            "feasibility_checks": ["设备可得性", "材料可得性", "条件可实现性"],
            "consistency_checks": ["数据一致性", "逻辑一致性", "时间一致性"]
        }
        
        # 定义输入输出Schema
        self.input_schema = {
            "type": "object",
            "properties": {
                "draft_content": {"type": "string"},
                "draft_id": {"type": "string"},
                "experiment_plan": {"type": "object"},
                "information_list": {"type": "array"}
            }
        }
        
        self.output_schema = {
            "type": "object",
            "properties": {
                "verification_type": {"type": "string"},
                "status": {"type": "string", "enum": ["passed", "warning", "failed"]},
                "issues_found": {"type": "array"},
                "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                "recommendations": {"type": "array"}
            },
            "required": ["verification_type", "status", "confidence_score"]
        }
        
    async def _load_prompt_templates(self):
        """加载提示词模板"""
        self.prompt_templates = {
            "verify_feasibility": """
系统：你是科研验证专家，请从技术可行性角度审查以下方案。

方案内容：{content}
研究领域：{domain}

请从以下维度进行深度验证：

1. **技术成熟度评估**：
   - 所需技术的当前发展水平
   - 技术实现的难度等级
   - 是否存在技术瓶颈

2. **资源可得性分析**：
   - 所需设备和材料的可获得性
   - 人力资源需求评估
   - 时间资源的合理性

3. **实施条件检查**：
   - 实验环境要求
   - 安全性考虑
   - 法规合规性

4. **成功概率预测**：
   - 基于类似研究的成功率
   - 主要风险因素识别
   - 备选方案建议

请以JSON格式返回验证结果：
{{
    "feasibility_score": 0-10的评分,
    "technical_maturity": {{
        "current_level": "描述",
        "bottlenecks": ["瓶颈1", "瓶颈2"]
    }},
    "resource_availability": {{
        "equipment": "可得性评估",
        "materials": "可得性评估",
        "expertise": "可得性评估"
    }},
    "implementation_conditions": {{
        "environment_requirements": "要求描述",
        "safety_considerations": ["考虑1", "考虑2"],
        "regulatory_compliance": "合规性分析"
    }},
    "success_probability": {{
        "overall_probability": "高/中/低",
        "main_risks": ["风险1", "风险2"],
        "mitigation_strategies": ["策略1", "策略2"]
    }},
    "recommendations": ["建议1", "建议2"],
    "confidence": 0-1的置信度
}}
""",

            "verify_safety": """
系统：你是科研安全专家，请对以下方案进行全面的安全性评估。

方案内容：{content}
涉及领域：{domain}

请从多个安全维度进行评估：

1. **实验安全风险**：
   - 化学品安全性
   - 生物安全等级
   - 物理操作风险
   - 辐射或电磁安全

2. **环境影响评估**：
   - 潜在的环境污染
   - 废弃物处理要求
   - 生态影响评估

3. **人员安全保障**：
   - 操作人员安全要求
   - 防护设备需求
   - 应急预案需求

4. **伦理合规检查**：
   - 研究伦理审查需求
   - 动物实验伦理
   - 人体试验伦理
   - 数据隐私保护

5. **知识产权风险**：
   - 专利侵权风险
   - 商业秘密保护
   - 成果归属问题

请以JSON格式返回：
{{
    "safety_assessment": {{
        "overall_risk_level": "高/中/低",
        "experimental_safety": {{
            "chemical_hazards": ["危险1", "危险2"],
            "biological_safety_level": "BSL级别",
            "physical_risks": ["风险1", "风险2"]
        }},
        "environmental_impact": {{
            "pollution_risk": "风险等级",
            "waste_management": "处理要求",
            "ecological_concerns": ["关注点1", "关注点2"]
        }},
        "personnel_safety": {{
            "ppe_requirements": ["防护设备1", "防护设备2"],
            "training_needs": ["培训需求1", "培训需求2"],
            "emergency_procedures": ["程序1", "程序2"]
        }},
        "ethical_compliance": {{
            "irb_required": true/false,
            "animal_ethics": "相关要求",
            "human_subjects": "相关要求",
            "data_privacy": "保护措施"
        }},
        "ip_risks": {{
            "patent_conflicts": ["潜在冲突1"],
            "trade_secrets": "保护建议",
            "ownership_clarity": "归属分析"
        }}
    }},
    "mandatory_requirements": ["必须满足的要求1", "要求2"],
    "recommended_safeguards": ["建议的保护措施1", "措施2"],
    "compliance_checklist": ["检查项1", "检查项2"],
    "confidence": 0-1的置信度
}}
""",
            
            "verify_consistency": """
系统：你是逻辑验证专家，请检查以下内容的内部一致性和逻辑完整性。

内容：{content}
上下文：{context}

请从以下方面进行深度验证：

1. **逻辑一致性检查**：
   - 前提与结论的逻辑关系
   - 推理过程的严密性
   - 是否存在逻辑谬误

2. **数据一致性验证**：
   - 数据之间的相互印证
   - 数值计算的准确性
   - 单位和量纲的一致性

3. **方法论一致性**：
   - 研究方法的内在一致性
   - 实验设计的合理性
   - 统计方法的适用性

4. **知识体系一致性**：
   - 与已知科学原理的符合度
   - 与领域共识的一致性
   - 创新点的合理性论证

5. **时间逻辑验证**：
   - 时间顺序的合理性
   - 进度安排的可行性
   - 依赖关系的正确性

请以JSON格式返回：
{{
    "consistency_check": {{
        "logical_consistency": {{
            "is_consistent": true/false,
            "logical_issues": ["问题1", "问题2"],
            "reasoning_quality": "优秀/良好/一般/差"
        }},
        "data_consistency": {{
            "is_consistent": true/false,
            "data_conflicts": ["冲突1", "冲突2"],
            "calculation_errors": ["错误1", "错误2"]
        }},
        "methodological_consistency": {{
            "is_consistent": true/false,
            "method_issues": ["问题1", "问题2"],
            "design_flaws": ["缺陷1", "缺陷2"]
        }},
        "knowledge_consistency": {{
            "scientific_validity": true/false,
            "consensus_alignment": "高/中/低",
            "innovation_justification": "充分/一般/不足"
        }},
        "temporal_consistency": {{
            "sequence_valid": true/false,
            "timeline_feasible": true/false,
            "dependency_errors": ["错误1", "错误2"]
        }}
    }},
    "critical_issues": ["关键问题1", "关键问题2"],
    "improvement_suggestions": ["改进建议1", "建议2"],
    "overall_consistency_score": 0-10,
    "confidence": 0-1的置信度
}}
""",
            
            "cross_reference_check": """
系统：你是信息交叉验证专家，请对比分析来自不同来源的信息。

信息源1：{source1}
信息源2：{source2}
验证重点：{focus}

请进行以下交叉验证：

1. **信息一致性对比**：
   - 核心观点是否一致
   - 数据是否吻合
   - 结论是否相同

2. **差异分析**：
   - 识别主要分歧点
   - 分析差异原因
   - 评估各自可信度

3. **互补性评估**：
   - 信息的互补关系
   - 综合后的完整性
   - 协同效应分析

4. **冲突解决建议**：
   - 冲突的性质判断
   - 解决冲突的方法
   - 需要补充的信息

请以JSON格式返回：
{{
    "cross_validation_result": {{
        "consistency_level": "高度一致/基本一致/存在分歧/严重冲突",
        "agreement_points": ["一致点1", "一致点2"],
        "disagreement_points": [
            {{
                "issue": "分歧点描述",
                "source1_view": "来源1观点",
                "source2_view": "来源2观点",
                "severity": "高/中/低"
            }}
        ],
        "complementarity": {{
            "complementary_aspects": ["互补方面1", "互补方面2"],
            "synergy_potential": "高/中/低"
        }},
        "credibility_assessment": {{
            "source1_credibility": 0-10,
            "source2_credibility": 0-10,
            "rationale": "可信度判断依据"
        }}
    }},
    "conflict_resolution": {{
        "recommended_approach": "建议的解决方法",
        "additional_info_needed": ["需要的额外信息1", "信息2"],
        "priority_source": "优先采信的来源及理由"
    }},
    "integrated_conclusion": "综合两个来源后的结论",
    "confidence": 0-1的置信度
}}
"""
        }
    
    async def _process_event_impl(self, event: BlackboardEvent) -> Any:
        """处理验证相关事件"""
        try:
            if event.event_type == EventType.SOLUTION_DRAFT_CREATED:
                return await self._verify_solution_draft(event.data)
            elif event.event_type == EventType.EXPERIMENT_PLAN:
                return await self._verify_experiment_plan(event.data)
            elif event.event_type == EventType.INFORMATION_UPDATE:
                return await self._check_information_consistency(event.data)
            elif event.event_type == EventType.MODEL_RESULT:
                return await self._verify_model_result(event.data)
            else:
                self.logger.warning(f"未处理的事件类型: {event.event_type}")
                
        except Exception as e:
            self.logger.error(f"验证处理失败: {e}")
            await self._publish_verification_error(event, str(e))
    
    async def _verify_solution_draft(self, data: Dict[str, Any]) -> None:
        """验证方案草案"""
        draft_content = data.get("draft_content", "")
        draft_id = data.get("draft_id", "")
        
        # 执行多重验证
        verifications = []
        
        # 1. 可行性检查
        feasibility_result = await self._check_feasibility(draft_content)
        verifications.append(feasibility_result)
        
        # 2. 安全合规检查
        safety_result = await self._check_safety_compliance(draft_content)
        verifications.append(safety_result)
        
        # 3. 逻辑一致性检查
        consistency_result = await self._check_internal_consistency(draft_content)
        verifications.append(consistency_result)
        
        # 综合验证结果
        overall_status = self._determine_overall_status(verifications)
        
        # 发布验证报告
        await self.publish_result(
            EventType.VERIFICATION_REPORT,
            {
                "target_draft_id": draft_id,
                "verification_results": [result.__dict__ for result in verifications],
                "overall_status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "verifier": self.config.name
            }
        )
        
        # 如果发现严重问题，发布冲突警告
        if overall_status == "failed":
            await self._publish_conflict_warning(draft_id, verifications)
    
    async def _verify_experiment_plan(self, data: Dict[str, Any]) -> None:
        """验证实验方案"""
        plan_content = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 检查实验可行性
        feasibility_result = await self._check_feasibility(plan_content)
        
        # 发布验证结果
        await self.publish_result(
            EventType.VERIFICATION_REPORT,
            {
                "target_type": "experiment_plan",
                "feasibility_check": feasibility_result.__dict__,
                "timestamp": datetime.now().isoformat(),
                "verifier": self.config.name
            }
        )
    
    async def _check_information_consistency(self, data: Dict[str, Any]) -> None:
        """检查信息一致性"""
        # 获取相关的历史信息
        recent_info = await self.blackboard.get_recent_events(20)
        info_updates = [e for e in recent_info if e.event_type == EventType.INFORMATION_UPDATE]
        
        if len(info_updates) < 2:
            return  # 信息不足，无法比较
        
        # 构建信息列表用于一致性检查
        information_list = []
        for i, event in enumerate(info_updates[-5:]):  # 只检查最近5条
            info_data = event.data
            information_list.append(f"{i+1}. {info_data.get('content', json.dumps(info_data))}")
        
        # 调用LLM进行一致性检查
        prompt = self.format_prompt(
            "verify_consistency",
            content="\n".join(information_list),
            context="信息一致性检查"
        )
        
        response = await self.call_llm(prompt, response_format="json")
        result = json.loads(response)
        
        # 如果发现矛盾，发布冲突警告
        if result.get("consistency_check", {}).get("logical_consistency", {}).get("is_consistent") == False:
            await self.publish_result(
                EventType.CONFLICT_WARNING,
                {
                    "conflict_type": "information_inconsistency",
                    "details": result,
                    "affected_events": [e.event_id for e in info_updates[-5:]]
                }
            )
    
    async def _check_feasibility(self, content: str) -> VerificationResult:
        """检查可行性"""
        prompt = self.format_prompt("verify_feasibility", content=content, domain="科研领域")
        response = await self.call_llm(prompt, response_format="json")
        result = json.loads(response)
        
        return VerificationResult(
            verification_id=f"feasibility_{datetime.now().strftime('%H%M%S')}",
            target_content=content[:200] + "...",
            verification_type="feasibility",
            status=result.get("status", "warning"),
            issues_found=result.get("issues_found", []),
            recommendations=result.get("recommendations", []),
            confidence_score=result.get("confidence", 0.5),
            evidence=result.get("resource_availability", [])
        )
    
    async def _check_safety_compliance(self, content: str) -> VerificationResult:
        """检查安全合规性"""
        prompt = self.format_prompt("verify_safety", content=content, domain="科研领域")
        response = await self.call_llm(prompt, response_format="json")
        result = json.loads(response)
        
        return VerificationResult(
            verification_id=f"safety_{datetime.now().strftime('%H%M%S')}",
            target_content=content[:200] + "...",
            verification_type="safety",
            status=result.get("status", "warning"),
            issues_found=result.get("safety_assessment", {}).get("experimental_safety", {}).get("chemical_hazards", []) +
                        result.get("safety_assessment", {}).get("experimental_safety", {}).get("biological_safety_level", "") +
                        result.get("safety_assessment", {}).get("experimental_safety", {}).get("physical_risks", []),
            recommendations=result.get("recommendations", []),
            confidence_score=result.get("confidence", 0.5),
            evidence=result.get("safety_assessment", {}).get("experimental_safety", {}).get("chemical_hazards", []) +
                        result.get("safety_assessment", {}).get("experimental_safety", {}).get("biological_safety_level", "") +
                        result.get("safety_assessment", {}).get("experimental_safety", {}).get("physical_risks", [])
        )
    
    async def _check_internal_consistency(self, content: str) -> VerificationResult:
        """检查内部一致性"""
        prompt = self.format_prompt(
            "verify_consistency", 
            content=content,
            context="方案内部一致性验证"
        )
        response = await self.call_llm(prompt, response_format="json")
        result = json.loads(response)
        
        # 判断整体状态
        consistency_check = result.get("consistency_check", {})
        
        # 收集所有不一致的问题
        issues_found = []
        
        # 检查各个维度的一致性
        if not consistency_check.get("logical_consistency", {}).get("is_consistent", True):
            issues_found.extend(consistency_check["logical_consistency"].get("logical_issues", []))
        
        if not consistency_check.get("data_consistency", {}).get("is_consistent", True):
            issues_found.extend(consistency_check["data_consistency"].get("data_conflicts", []))
            issues_found.extend(consistency_check["data_consistency"].get("calculation_errors", []))
        
        if not consistency_check.get("methodological_consistency", {}).get("is_consistent", True):
            issues_found.extend(consistency_check["methodological_consistency"].get("method_issues", []))
            issues_found.extend(consistency_check["methodological_consistency"].get("design_flaws", []))
        
        if not consistency_check.get("knowledge_consistency", {}).get("scientific_validity", True):
            issues_found.append("科学原理不一致")
        
        if not consistency_check.get("temporal_consistency", {}).get("sequence_valid", True):
            issues_found.extend(consistency_check["temporal_consistency"].get("dependency_errors", []))
        
        # 根据问题数量判断状态
        if not issues_found:
            status = "passed"
        elif len(issues_found) <= 2:
            status = "warning"
        else:
            status = "failed"
        
        return VerificationResult(
            verification_id=str(uuid.uuid4()),
            target_content=content[:200] + "...",
            verification_type="consistency",
            status=status,
            issues_found=issues_found,
            recommendations=result.get("improvement_suggestions", []),
            confidence_score=result.get("confidence", 0.5),
            evidence=result.get("critical_issues", [])
        )
    
    def _determine_overall_status(self, verifications: List[VerificationResult]) -> str:
        """确定总体验证状态"""
        failed_count = sum(1 for v in verifications if v.status == "failed")
        warning_count = sum(1 for v in verifications if v.status == "warning")
        
        if failed_count > 0:
            return "failed"
        elif warning_count > 0:
            return "warning"
        else:
            return "passed"
    
    async def _publish_conflict_warning(self, draft_id: str, verifications: List[VerificationResult]):
        """发布冲突警告"""
        critical_issues = []
        for v in verifications:
            if v.status == "failed":
                critical_issues.extend(v.issues_found)
        
        await self.publish_result(
            EventType.CONFLICT_WARNING,
            {
                "conflict_type": "verification_failed",
                "target_draft_id": draft_id,
                "critical_issues": critical_issues,
                "verification_summary": f"验证失败: {len(critical_issues)}个严重问题",
                "requires_attention": True
            }
        )
    
    async def _publish_verification_error(self, original_event: BlackboardEvent, error_msg: str):
        """发布验证错误"""
        await self.publish_result(
            EventType.CONFLICT_WARNING,
            {
                "conflict_type": "verification_error",
                "original_event_id": original_event.event_id,
                "error_message": error_msg,
                "requires_attention": True
            }
        )
    
    async def _verify_model_result(self, data: Dict[str, Any]) -> None:
        """验证模型计算结果"""
        result_content = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 简单的模型结果合理性检查
        issues = []
        
        # 检查数值合理性
        if "result" in data:
            result_value = data["result"]
            if isinstance(result_value, (int, float)):
                if result_value < 0 and "能量" in str(data):
                    issues.append("能量值不应为负数")
                if abs(result_value) > 1e10:
                    issues.append("数值过大，可能存在计算错误")
        
        # 如果发现问题，发布警告
        if issues:
            await self.publish_result(
                EventType.CONFLICT_WARNING,
                {
                    "conflict_type": "model_result_suspicious",
                    "issues": issues,
                    "model_data": data,
                    "requires_attention": True
                }
            )