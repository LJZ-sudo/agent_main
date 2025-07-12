"""
实验设计Agent - 负责将理论方案转化为具体的实验设计和实施计划
扮演AI团队中的"实验专家"角色
根据docs要求实现完整的实验设计功能
"""
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import Blackboard, BlackboardEvent, EventType, ReasoningStep


@dataclass
class ExperimentStep:
    """实验步骤数据结构"""
    step_id: str
    title: str
    description: str
    materials: List[str]
    procedures: List[str]
    expected_outcome: str
    duration: int  # 预计时间(分钟)
    risk_level: str  # low, medium, high
    dependencies: List[str] = field(default_factory=list)
    quality_control: List[str] = field(default_factory=list)
    safety_measures: List[str] = field(default_factory=list)


@dataclass
class ExperimentPlan:
    """完整实验计划数据结构"""
    plan_id: str
    title: str
    objective: str
    hypothesis: str
    methodology: str
    materials: List[str]
    equipment: List[str]
    conditions: List[str]
    variables: Dict[str, List[str]]
    steps: List[ExperimentStep]
    safety_assessment: Dict[str, Any]
    quality_control: Dict[str, Any]
    expected_outcomes: List[str]
    timeline: Dict[str, int]
    resource_requirements: Dict[str, Any]
    risk_analysis: Dict[str, Any]


class ExperimentDesignAgent(BaseAgent):
    """
    实验设计Agent - 科学实验设计专家
    
    符合docs要求的完整功能：
    - 将理论方案转化为具体实验步骤
    - 设计实验流程和方法学  
    - 评估实验可行性和资源需求
    - 制定安全和质量控制措施
    - 支持多种实验类型的设计
    """

    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="ExperimentDesignAgent",
            agent_type="experiment_designer",
            description="实验设计Agent - 实验专家",
            subscribed_events=[
                EventType.SOLUTION_DRAFT_CREATED,
                EventType.DESIGN_REQUEST,
                EventType.VERIFICATION_REPORT,
                EventType.TASK_ASSIGNED
            ],
            max_concurrent_tasks=3
        )
        super().__init__(config, blackboard, llm_client)
        
        # 实验类型支持
        self.experiment_types = {
            "材料合成": "material_synthesis",
            "催化反应": "catalytic_reaction", 
            "电化学": "electrochemical",
            "光化学": "photochemical",
            "生物实验": "biological",
            "物理测试": "physical_testing",
            "分析检测": "analytical"
        }
        
        # 安全等级定义
        self.safety_levels = {
            "低风险": {"code": "low", "requirements": ["基础防护", "通风良好"]},
            "中风险": {"code": "medium", "requirements": ["专业防护", "安全培训", "监督操作"]},
            "高风险": {"code": "high", "requirements": ["严格防护", "专家监督", "应急预案", "特殊环境"]}
        }
        
        # 质量控制标准
        self.quality_standards = {
            "precision": 0.95,      # 精度要求
            "accuracy": 0.98,       # 准确度要求  
            "reproducibility": 0.9,  # 重现性要求
            "reliability": 0.95     # 可靠性要求
        }

    async def _load_prompt_templates(self):
        """加载完整的实验设计Prompt模板"""
        self.prompt_templates = {
            "comprehensive_experiment_design": """
系统角色：你是一位资深的科研实验设计专家，擅长根据研究目标制定完整、安全、可行的实验方案。

输入信息：
研究背景：{background}
实验目标：{objective}
理论假设：{hypothesis}
约束条件：{constraints}
已有信息：{existing_information}

请设计一个符合科学研究标准的完整实验方案，包含以下所有要素：

**1. 实验设计原理**
- 实验的科学依据和理论基础
- 实验设计思路和创新点
- 预期解决的科学问题

**2. 实验目标与假设**
- 具体、可测量的实验目标
- 明确的科学假设
- 成功标准的定义

**3. 实验材料与设备**
- 详细的材料清单（规格、纯度、来源）
- 所需设备清单（型号、精度要求）
- 试剂和消耗品列表

**4. 实验条件控制**
- 温度、压力、湿度等环境条件
- 时间控制要求
- 其他关键控制参数

**5. 变量设计**
- 自变量（可控制的实验因素）
- 因变量（观测指标）
- 控制变量（需要保持恒定的因素）
- 干扰变量的识别和控制

**6. 详细实验步骤**
- 预处理步骤
- 主要实验流程（按时间顺序）
- 数据采集方法
- 后处理步骤

**7. 安全评估与防护**
- 潜在危险因素识别
- 安全防护措施
- 应急处理预案
- 环境保护措施

**8. 质量控制**
- 质量控制检查点
- 数据质量保证方法
- 误差控制措施
- 重现性验证方案

**9. 数据处理与分析**
- 数据收集方法
- 统计分析方法
- 结果评价标准
- 不确定度分析

**10. 时间安排与资源需求**
- 详细时间计划
- 人力资源需求
- 经费预算估算
- 关键里程碑

请以JSON格式返回，严格遵循以下结构：
{{
    "experiment_plan": {{
        "title": "实验方案标题",
        "objective": "实验目标",
        "hypothesis": "实验假设",
        "scientific_basis": "科学依据",
        "innovation_points": ["创新点1", "创新点2"],
        "materials": [
            {{
                "name": "材料名称",
                "specification": "规格要求",
                "quantity": "用量",
                "supplier": "供应商或来源",
                "purity": "纯度要求",
                "storage_conditions": "存储条件"
            }}
        ],
        "equipment": [
            {{
                "name": "设备名称",
                "model": "型号要求",
                "precision": "精度要求",
                "purpose": "用途说明"
            }}
        ],
        "experimental_conditions": {{
            "temperature": "温度范围或设定值",
            "pressure": "压力条件", 
            "humidity": "湿度要求",
            "atmosphere": "气氛条件",
            "other_conditions": ["其他条件1", "条件2"]
        }},
        "variables": {{
            "independent": [
                {{
                    "name": "自变量名称",
                    "range": "变化范围",
                    "levels": ["水平1", "水平2"],
                    "control_method": "控制方法"
                }}
            ],
            "dependent": [
                {{
                    "name": "因变量名称", 
                    "measurement_method": "测量方法",
                    "expected_range": "预期范围",
                    "precision": "测量精度"
                }}
            ],
            "controlled": [
                {{
                    "name": "控制变量名称",
                    "fixed_value": "固定值",
                    "control_importance": "控制重要性"
                }}
            ]
        }},
        "detailed_procedures": [
            {{
                "step_number": 1,
                "phase": "预处理/主实验/后处理",
                "title": "步骤标题",
                "description": "详细操作描述",
                "duration": "预计时间(分钟)",
                "key_points": ["关键要点1", "要点2"],
                "quality_checks": ["质量检查1", "检查2"],
                "safety_notes": ["安全注意事项1", "事项2"]
            }}
        ],
        "safety_assessment": {{
            "risk_level": "高/中/低",
            "hazard_identification": [
                {{
                    "hazard": "危险因素",
                    "severity": "严重程度",
                    "probability": "发生概率",
                    "mitigation": "缓解措施"
                }}
            ],
            "protective_equipment": ["防护设备1", "设备2"],
            "emergency_procedures": ["应急程序1", "程序2"],
            "environmental_considerations": ["环境考虑1", "考虑2"]
        }},
        "quality_control": {{
            "checkpoints": [
                {{
                    "stage": "实验阶段",
                    "check_item": "检查项目",
                    "acceptance_criteria": "接受标准",
                    "frequency": "检查频率"
                }}
            ],
            "calibration_requirements": ["校准要求1", "要求2"],
            "documentation_requirements": ["记录要求1", "要求2"],
            "validation_methods": ["验证方法1", "方法2"]
        }},
        "data_analysis": {{
            "collection_methods": ["数据收集方法1", "方法2"],
            "statistical_methods": ["统计方法1", "方法2"],
            "analysis_software": "推荐分析软件",
            "acceptance_criteria": "结果接受标准"
        }},
        "timeline": {{
            "total_duration": "总时长",
            "phases": [
                {{
                    "phase": "阶段名称",
                    "duration": "持续时间",
                    "milestones": ["里程碑1", "里程碑2"]
                }}
            ]
        }},
        "resource_requirements": {{
            "personnel": "人员需求",
            "estimated_cost": "预估成本",
            "special_facilities": ["特殊设施要求1", "要求2"],
            "external_services": ["外部服务1", "服务2"]
        }},
        "expected_outcomes": [
            {{
                "outcome": "预期结果描述",
                "measurement": "测量指标",
                "success_criteria": "成功标准"
            }}
        ],
        "limitations": ["实验局限性1", "局限性2"],
        "future_work": ["后续工作建议1", "建议2"]
    }}
}}
""",

            "feasibility_analysis": """
作为实验设计专家，请对以下实验方案进行全面的可行性分析：

实验方案：
{experiment_plan}

请从以下维度进行深度分析：

**技术可行性**：
- 所需技术是否成熟可用
- 技术难点和挑战分析
- 设备和材料的可获得性
- 方法学的科学合理性

**资源可行性**：
- 人力资源需求和可用性
- 设备设施的需求和成本
- 材料试剂的采购和成本
- 时间资源的合理性

**安全可行性**：
- 安全风险评估
- 防护措施的充分性
- 应急响应的完备性
- 法规合规性检查

**经济可行性**：
- 成本效益分析
- 预算合理性评估
- 资源配置优化建议
- 替代方案的经济性

**执行可行性**：
- 操作复杂度评估
- 技能要求和培训需求
- 执行环境的适宜性
- 项目管理的可操作性

输出JSON格式：
{{
    "feasibility_assessment": {{
        "overall_score": 0-100,
        "overall_recommendation": "强烈推荐/推荐/有条件推荐/不推荐",
        "technical_feasibility": {{
            "score": 0-100,
            "strengths": ["技术优势1", "优势2"],
            "challenges": ["技术挑战1", "挑战2"],
            "risk_factors": ["风险因素1", "因素2"],
            "recommendations": ["技术建议1", "建议2"]
        }},
        "resource_feasibility": {{
            "score": 0-100,
            "availability": "资源可用性评估",
            "cost_analysis": "成本分析",
            "bottlenecks": ["资源瓶颈1", "瓶颈2"],
            "optimization_suggestions": ["优化建议1", "建议2"]
        }},
        "safety_feasibility": {{
            "score": 0-100,
            "risk_assessment": "风险评估结果",
            "safety_level": "安全等级",
            "required_measures": ["必要措施1", "措施2"],
            "compliance_status": "合规性状态"
        }},
        "economic_feasibility": {{
            "score": 0-100,
            "cost_breakdown": "成本分解",
            "roi_estimation": "投资回报预估",
            "cost_optimization": ["成本优化建议1", "建议2"]
        }},
        "execution_feasibility": {{
            "score": 0-100,
            "complexity_level": "复杂度等级",
            "skill_requirements": ["技能要求1", "要求2"],
            "training_needs": ["培训需求1", "需求2"],
            "timeline_assessment": "时间线评估"
        }},
        "critical_success_factors": ["关键成功因素1", "因素2"],
        "major_risks": [
            {{
                "risk": "风险描述",
                "impact": "影响程度",
                "probability": "发生概率",
                "mitigation": "缓解策略"
            }}
        ],
        "improvement_recommendations": [
            {{
                "area": "改进领域",
                "suggestion": "具体建议",
                "expected_benefit": "预期收益",
                "implementation_difficulty": "实施难度"
            }}
        ]
    }}
}}
""",

            "protocol_optimization": """
作为实验优化专家，请对现有实验方案进行优化改进：

当前实验方案：
{current_plan}

已知问题或改进需求：
{improvement_requirements}

请提供优化建议：

**效率优化**：
- 实验流程的简化和加速
- 并行操作的可能性
- 自动化改进机会
- 资源利用效率提升

**精度优化**：
- 测量精度的改进
- 误差来源的控制
- 重现性的提升
- 数据质量的保证

**安全优化**：
- 安全风险的进一步降低
- 防护措施的改进
- 环境友好性提升
- 废物处理优化

**成本优化**：
- 材料使用的优化
- 设备利用率提升
- 人力成本的控制
- 替代方案的评估

输出JSON格式的优化方案。
"""
        }

    async def _process_event_impl(self, event: BlackboardEvent) -> Any:
        """处理黑板事件的具体实现"""
        try:
            # 记录事件处理推理步骤
            event_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="event_processing",
                description=f"处理{event.event_type.value}事件",
                input_data={"event_type": event.event_type.value, "agent_id": event.agent_id},
                reasoning_text=f"实验设计Agent收到{event.event_type.value}事件，开始处理"
            )
            await self.blackboard.record_reasoning_step(event_step)
            
            if event.event_type == EventType.TASK_ASSIGNED:
                if event.target_agent == self.agent_id or event.data.get("task_type") == "experiment_design":
                    await self._handle_experiment_design_task(event)
            elif event.event_type == EventType.SOLUTION_DRAFT_CREATED:
                await self._design_experiment_for_solution(event)
            elif event.event_type == EventType.DESIGN_REQUEST:
                await self._handle_design_request(event)
            elif event.event_type == EventType.VERIFICATION_REPORT:
                await self._handle_verification_feedback(event)
                
        except Exception as e:
            logger.error(f"实验设计Agent事件处理失败: {e}")
            await self._publish_error_event(event, str(e))

    async def _handle_experiment_design_task(self, event: BlackboardEvent):
        """处理实验设计任务"""
        task_data = event.data
        session_id = event.session_id or "default"
        
        logger.info(f"开始实验设计任务: {task_data.get('user_input', '')[:50]}...")
        
        # 记录任务开始推理步骤
        task_start_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="task_start",
            description="开始实验设计任务",
            input_data=task_data,
            reasoning_text="收到实验设计任务，开始分析需求并制定实验方案"
        )
        await self.blackboard.record_reasoning_step(task_start_step)
        
        try:
            # 分析实验需求
            experiment_requirements = await self._analyze_experiment_requirements(task_data, session_id)
            
            # 设计完整实验方案
            experiment_plan = await self._design_comprehensive_experiment(experiment_requirements, session_id)
            
            # 可行性分析
            feasibility_analysis = await self._conduct_feasibility_analysis(experiment_plan, session_id)
            
            # 安全评估
            safety_assessment = await self._conduct_safety_assessment(experiment_plan, session_id)
            
            # 整合最终方案
            final_plan = {
                "plan_id": str(uuid.uuid4()),
                "session_id": session_id,
                "experiment_plan": experiment_plan,
                "feasibility_analysis": feasibility_analysis,
                "safety_assessment": safety_assessment,
                "creation_time": datetime.now().isoformat(),
                "agent_id": self.agent_id
            }
            
            # 发布实验方案事件
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.EXPERIMENT_PLAN,
                agent_id=self.agent_id,
                session_id=session_id,
                data=final_plan
            ))
            
            # 记录任务完成推理步骤
            completion_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="completion",
                description="实验设计任务完成",
                input_data=experiment_requirements,
                output_data={"plan_id": final_plan["plan_id"]},
                reasoning_text="完成了完整的实验方案设计，包括可行性分析和安全评估",
                confidence=0.9
            )
            await self.blackboard.record_reasoning_step(completion_step)
            
            logger.info(f"实验设计完成: {final_plan['plan_id']}")
            
        except Exception as e:
            logger.error(f"实验设计任务失败: {e}")
            await self._publish_error_event(event, str(e))

    async def _analyze_experiment_requirements(self, task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """分析实验需求"""
        user_input = task_data.get("user_input", "")
        previous_results = task_data.get("previous_results", {})
        subtask_info = task_data.get("subtask_info", {})
        
        # 提取实验背景信息
        background_info = self._extract_background_information(user_input, previous_results)
        
        requirements = {
            "user_input": user_input,
            "background": background_info,
            "objective": subtask_info.get("description", user_input),
            "constraints": self._identify_constraints(task_data),
            "experiment_type": self._classify_experiment_type(user_input),
            "complexity_level": self._assess_complexity(user_input, previous_results)
        }
        
        return requirements

    async def _design_comprehensive_experiment(self, requirements: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """设计完整实验方案"""
        # 使用LLM设计详细实验方案
        design_prompt = self.prompt_templates["comprehensive_experiment_design"].format(
            background=requirements.get("background", ""),
            objective=requirements.get("objective", ""),
            hypothesis=requirements.get("hypothesis", "待制定"),
            constraints=requirements.get("constraints", ""),
            existing_information=json.dumps(requirements, ensure_ascii=False, indent=2)
        )
        
        # 记录设计推理步骤
        design_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="design",
            description="使用LLM设计完整实验方案",
            input_data=requirements,
            reasoning_text="调用LLM进行详细的实验方案设计，包括所有必要的实验要素"
        )
        await self.blackboard.record_reasoning_step(design_step)
        
        try:
            response = await self.llm_client.generate_text(
                design_prompt,
                temperature=0.2,
                max_tokens=4000
            )
            
            if response.success:
                experiment_plan = json.loads(response.content)
                return experiment_plan.get("experiment_plan", {})
            else:
                logger.error(f"实验设计LLM调用失败: {response.error}")
                return self._create_basic_experiment_plan(requirements)
                
        except json.JSONDecodeError:
            logger.warning("LLM返回的不是有效JSON，使用基础实验方案")
            return self._create_basic_experiment_plan(requirements)
        except Exception as e:
            logger.error(f"实验方案设计异常: {e}")
            return self._create_basic_experiment_plan(requirements)

    async def _conduct_feasibility_analysis(self, experiment_plan: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """进行可行性分析"""
        analysis_prompt = self.prompt_templates["feasibility_analysis"].format(
            experiment_plan=json.dumps(experiment_plan, ensure_ascii=False, indent=2)
        )
        
        try:
            response = await self.llm_client.generate_text(
                analysis_prompt,
                temperature=0.1,
                max_tokens=3000
            )
            
            if response.success:
                analysis = json.loads(response.content)
                return analysis.get("feasibility_assessment", {})
            else:
                return self._create_basic_feasibility_analysis(experiment_plan)
                
        except json.JSONDecodeError:
            return self._create_basic_feasibility_analysis(experiment_plan)
        except Exception as e:
            logger.error(f"可行性分析异常: {e}")
            return self._create_basic_feasibility_analysis(experiment_plan)

    async def _conduct_safety_assessment(self, experiment_plan: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """进行安全评估"""
        # 基于实验方案进行安全风险评估
        safety_assessment = {
            "overall_risk_level": self._assess_overall_risk(experiment_plan),
            "hazard_analysis": self._analyze_hazards(experiment_plan),
            "safety_measures": self._recommend_safety_measures(experiment_plan),
            "emergency_procedures": self._define_emergency_procedures(experiment_plan),
            "compliance_check": self._check_safety_compliance(experiment_plan)
        }
        
        return safety_assessment

    def _extract_background_information(self, user_input: str, previous_results: Dict[str, Any]) -> str:
        """提取背景信息"""
        background = f"用户需求: {user_input}\n"
        
        if "information_enhanced" in previous_results:
            info_result = previous_results["information_enhanced"]
            background += f"文献调研结果: {str(info_result)[:200]}...\n"
        
        if "verification" in previous_results:
            verification_result = previous_results["verification"]
            background += f"验证分析结果: {str(verification_result)[:200]}...\n"
            
        return background

    def _identify_constraints(self, task_data: Dict[str, Any]) -> str:
        """识别约束条件"""
        constraints = []
        
        # 从用户输入中识别约束
        user_input = task_data.get("user_input", "")
        if "成本" in user_input or "预算" in user_input:
            constraints.append("成本预算限制")
        if "时间" in user_input:
            constraints.append("时间限制")
        if "安全" in user_input:
            constraints.append("安全要求")
            
        return "; ".join(constraints) if constraints else "无特殊约束"

    def _classify_experiment_type(self, user_input: str) -> str:
        """分类实验类型"""
        for exp_type, code in self.experiment_types.items():
            if exp_type in user_input:
                return exp_type
        return "通用实验"

    def _assess_complexity(self, user_input: str, previous_results: Dict[str, Any]) -> str:
        """评估复杂度"""
        complexity_indicators = len(previous_results)
        if "合成" in user_input or "反应" in user_input:
            complexity_indicators += 1
        if "多步" in user_input or "复杂" in user_input:
            complexity_indicators += 2
            
        if complexity_indicators >= 3:
            return "高"
        elif complexity_indicators >= 1:
            return "中"
        else:
            return "低"

    def _create_basic_experiment_plan(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """创建基础实验方案（备用）"""
        return {
            "title": f"基于{requirements.get('objective', '用户需求')}的实验方案",
            "objective": requirements.get("objective", ""),
            "hypothesis": "根据理论分析制定的假设",
            "materials": ["待确定的实验材料"],
            "equipment": ["待确定的实验设备"],
            "experimental_conditions": {
                "temperature": "室温或特定温度",
                "pressure": "标准压力",
                "atmosphere": "空气或特定气氛"
            },
            "detailed_procedures": [
                {
                    "step_number": 1,
                    "phase": "预处理",
                    "title": "材料准备",
                    "description": "准备实验所需的材料和设备",
                    "duration": "30",
                    "key_points": ["确保材料纯度", "检查设备状态"],
                    "safety_notes": ["佩戴防护设备", "检查安全设施"]
                }
            ],
            "safety_assessment": {
                "risk_level": "中",
                "protective_equipment": ["实验服", "护目镜", "手套"],
                "emergency_procedures": ["紧急停止程序", "应急联系方式"]
            }
        }

    def _create_basic_feasibility_analysis(self, experiment_plan: Dict[str, Any]) -> Dict[str, Any]:
        """创建基础可行性分析"""
        return {
            "overall_score": 75,
            "overall_recommendation": "有条件推荐",
            "technical_feasibility": {
                "score": 80,
                "strengths": ["方法合理", "技术可行"],
                "challenges": ["需要进一步优化"],
                "recommendations": ["建议进行预实验"]
            },
            "resource_feasibility": {
                "score": 70,
                "availability": "资源基本可获得",
                "cost_analysis": "成本在合理范围内"
            },
            "safety_feasibility": {
                "score": 85,
                "risk_assessment": "风险可控",
                "safety_level": "中等"
            }
        }

    def _assess_overall_risk(self, experiment_plan: Dict[str, Any]) -> str:
        """评估总体风险等级"""
        # 简化的风险评估逻辑
        materials = experiment_plan.get("materials", [])
        risk_keywords = ["酸", "碱", "有机溶剂", "高温", "高压", "易燃", "有毒"]
        
        risk_count = 0
        for material in materials:
            for keyword in risk_keywords:
                if keyword in str(material):
                    risk_count += 1
                    
        if risk_count >= 3:
            return "高"
        elif risk_count >= 1:
            return "中"
        else:
            return "低"

    def _analyze_hazards(self, experiment_plan: Dict[str, Any]) -> List[Dict[str, str]]:
        """分析危险因素"""
        hazards = []
        
        # 基于材料分析
        materials = experiment_plan.get("materials", [])
        for material in materials:
            material_str = str(material)
            if "酸" in material_str:
                hazards.append({
                    "hazard": "腐蚀性化学品",
                    "severity": "中等",
                    "mitigation": "使用防腐蚀设备和防护用品"
                })
                
        # 基于条件分析  
        conditions = experiment_plan.get("experimental_conditions", {})
        if "高温" in str(conditions):
            hazards.append({
                "hazard": "高温烫伤",
                "severity": "中等", 
                "mitigation": "使用隔热防护设备"
            })
            
        return hazards

    def _recommend_safety_measures(self, experiment_plan: Dict[str, Any]) -> List[str]:
        """推荐安全措施"""
        measures = [
            "佩戴个人防护设备（实验服、护目镜、手套）",
            "确保实验室通风良好",
            "准备急救用品和紧急联系方式",
            "实验前检查所有设备的安全状态"
        ]
        
        # 根据风险等级添加额外措施
        risk_level = self._assess_overall_risk(experiment_plan)
        if risk_level == "高":
            measures.extend([
                "需要专业人员监督操作",
                "制定详细的应急预案",
                "使用特殊防护设备"
            ])
            
        return measures

    def _define_emergency_procedures(self, experiment_plan: Dict[str, Any]) -> List[str]:
        """定义应急程序"""
        return [
            "立即停止实验操作",
            "关闭相关设备和气体阀门", 
            "如有人员受伤，立即实施急救",
            "通知实验室安全负责人",
            "必要时拨打紧急救援电话",
            "保护现场，等待专业处理"
        ]

    def _check_safety_compliance(self, experiment_plan: Dict[str, Any]) -> Dict[str, str]:
        """检查安全合规性"""
        return {
            "regulations_check": "符合基本实验室安全规范",
            "permit_requirements": "需要检查是否需要特殊许可",
            "waste_disposal": "需要制定废物处理计划",
            "documentation": "需要完整的安全记录文档"
        }

    async def _handle_design_request(self, event: BlackboardEvent):
        """处理设计请求事件"""
        # 实现设计请求处理逻辑
        pass

    async def _handle_verification_feedback(self, event: BlackboardEvent):
        """处理验证反馈事件"""
        # 实现验证反馈处理逻辑
        pass

    async def _design_experiment_for_solution(self, event: BlackboardEvent):
        """为方案草案设计实验"""
        # 实现方案实验设计逻辑
        pass

    async def _publish_error_event(self, original_event: BlackboardEvent, error_msg: str):
        """发布错误事件"""
        await self.blackboard.publish_event(BlackboardEvent(
            event_type=EventType.ERROR_OCCURRED,
            agent_id=self.agent_id,
            data={
                "original_event": original_event.event_id,
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
        ))
