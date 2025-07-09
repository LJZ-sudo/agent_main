"""
实验设计Agent - 负责将理论方案转化为具体的实验设计和实施计划
扮演AI团队中的"实验专家"角色
"""
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from core.base_agent import LLMBaseAgent, AgentConfig
from core.blackboard import Blackboard, BlackboardEvent, EventType


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
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ExperimentDesignAgent(LLMBaseAgent):
    """
    实验设计Agent - 科学实验设计专家

    职责:
    - 将理论方案转化为具体实验步骤
    - 设计实验流程和方法学  
    - 评估实验可行性和资源需求
    - 制定安全和质量控制措施
    """

    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="ExperimentDesignAgent",
            agent_type="experiment_designer",
            description="实验设计Agent - 实验专家",
            subscribed_events=[
                EventType.SOLUTION_DRAFT_CREATED,
                EventType.DESIGN_REQUEST,
                EventType.VERIFICATION_REPORT
            ],
            max_concurrent_tasks=3
        )
        super().__init__(config, blackboard, llm_client)
        
        # 定义输入输出Schema
        self.input_schema = {
            "type": "object",
            "properties": {
                "solution_description": {"type": "string"},
                "solution_id": {"type": "string"},
                "objective": {"type": "string"},
                "hypothesis": {"type": "string"}
            }
        }
        
        self.output_schema = {
            "type": "object",
            "properties": {
                "experiment_plan": {"type": "object"},
                "solution_id": {"type": "string"},
                "plan_id": {"type": "string"}
            },
            "required": ["experiment_plan", "solution_id"]
        }

    async def _load_prompt_templates(self):
        """加载Prompt模板 - 完全符合文档要求的科研实验设计"""
        self.prompt_templates = {
            "experiment_design": """
系统角色：你是一位资深的科研实验设计助手，擅长根据研究目标制定材料/化学实验方案。

用户输入：
实验背景：{background}  
实验目标：{objective}  
约束条件：{constraints}

请根据以上背景和目标，设计一个完整的实验方案。方案需涵盖：
- **实验目的**（对应目标的详细描述）  
- **所需样品**（实验使用的材料、试剂等）  
- **所需设备**（实验所需的仪器设备）  
- **实验条件**（需要控制或保持的条件，如温度、时间、环境等）  
- **变量设置**（自变量、因变量及控制变量分别是什么）  
- **具体步骤**（实验的详细操作步骤，按顺序列出）

输出要求：请使用JSON格式输出实验方案，包含字段`"objective"`, `"samples"`, `"equipment"`, `"conditions"`, `"variables"`, `"steps"`，并确保结构完整清晰。

> **重要提示**：输出必须是**有效的 JSON 字符串**，不包含多余说明或 Markdown 格式，只包含纯JSON对象，并严格符合以下 JSON Schema 定义：

{{
    "type": "object",
    "properties": {{
        "objective": {{ "type": "string" }},
        "samples": {{
            "type": "array",
            "items": {{ "type": "string" }}
        }},
        "equipment": {{
            "type": "array",
            "items": {{ "type": "string" }}
        }},
        "conditions": {{
            "type": "array",
            "items": {{ "type": "string" }}
        }},
        "variables": {{
            "type": "object",
            "properties": {{
                "independent": {{
                    "type": "array", "items": {{ "type": "string" }}
                }},
                "dependent": {{
                    "type": "array", "items": {{ "type": "string" }}
                }},
                "controlled": {{
                    "type": "array", "items": {{ "type": "string" }}
                }}
            }}
        }},
        "steps": {{
            "type": "array",
            "items": {{ "type": "string" }}
        }}
    }},
    "required": ["objective", "samples", "equipment", "conditions", "variables", "steps"]
}}
            """,
            
            "feasibility_analysis": """
你是实验设计Agent，需要评估实验方案的可行性。

实验方案：
{experiment_plan}

请从以下角度分析可行性：
1. 技术可行性 - 现有技术条件是否支持
2. 资源可行性 - 所需材料设备是否容易获得
3. 时间可行性 - 实验周期是否合理
4. 成本可行性 - 预算是否在合理范围
5. 安全可行性 - 是否存在安全风险

输出JSON格式：
{{
    "feasibility_score": 8.5,
    "technical_feasibility": "评估结果",
    "resource_feasibility": "评估结果", 
    "time_feasibility": "评估结果",
    "cost_feasibility": "评估结果",
    "safety_assessment": "安全评估",
    "risks": ["风险1", "风险2"],
    "recommendations": ["建议1", "建议2"]
}}
            """,
            
            "safety_assessment": """
作为实验安全专家，请对以下实验方案进行安全风险评估：

实验步骤：
{experiment_steps}

使用材料：
{materials}

请评估：
1. 化学安全风险
2. 物理安全风险  
3. 环境影响
4. 人员安全
5. 设备安全

输出安全评估报告（JSON格式）：
{{
    "safety_level": "low/medium/high",
    "chemical_risks": ["风险描述"],
    "physical_risks": ["风险描述"],
    "environmental_impact": "环境影响评估",
    "safety_measures": ["安全措施1", "安全措施2"],
    "emergency_procedures": ["应急程序1", "程序2"]
}}
            """
        }

    async def _process_event_impl(self, event: BlackboardEvent):
        """处理黑板事件的具体实现"""
        try:
            if event.event_type == EventType.EXPERIMENT_PLAN:
                await self._refine_experiment_plan(event)
            elif event.event_type == EventType.SOLUTION_DRAFT_CREATED:
                await self._design_experiment_for_solution(event)
            elif event.event_type == EventType.VERIFICATION_REPORT:
                await self._adjust_experiment_based_on_verification(event)

        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")

    async def _design_experiment_for_solution(self, event: BlackboardEvent):
        """为解决方案设计实验"""
        solution_data = event.data
        solution_id = solution_data.get("solution_id")
        
        if not solution_id:
            return

        self.logger.info(f"开始为方案设计实验: {solution_id}")

        try:
            # 生成实验设计
            experiment_plan = await self._generate_experiment_plan(solution_data)
            
            # 发布实验计划事件
            await self._publish_experiment_plan(experiment_plan, solution_id)

        except Exception as e:
            self.logger.error(f"实验设计失败: {e}")

    async def _generate_experiment_plan(self, solution_data: Dict) -> Dict:
        """生成实验计划"""
        prompt = self.format_prompt(
            "experiment_design",
            objective=solution_data.get("title", ""),
            hypothesis=solution_data.get("rationale", ""),
            solution_description=json.dumps(solution_data, ensure_ascii=False)
        )
        
        response = await self.call_llm(prompt, response_format="json")
        return json.loads(response)

    async def _publish_experiment_plan(self, plan: Dict, solution_id: str):
        """发布实验计划事件"""
        event = BlackboardEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.EXPERIMENT_PLAN,
            source_agent=self.config.name,
            data={
                "solution_id": solution_id,
                "experiment_plan": plan,
                "plan_id": str(uuid.uuid4())
            },
            timestamp=datetime.now()
        )
        
        await self.blackboard.publish_event(event)
        self.logger.info(f"实验计划已发布")

    async def _refine_experiment_plan(self, event: BlackboardEvent):
        """优化实验计划"""
        self.logger.info(f"优化实验计划: {event.event_id}")
        # 这是一个占位符方法
        pass

    async def _adjust_experiment_based_on_verification(self, event: BlackboardEvent):
        """基于验证结果调整实验"""
        self.logger.info(f"基于验证结果调整实验: {event.event_id}")
        # 这是一个占位符方法
        pass
