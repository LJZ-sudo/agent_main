"""
评估Agent - 负责系统性能评估与优化建议
扮演AI团队中的"质量控制专家"角色
"""
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from core.base_agent import LLMBaseAgent, AgentConfig
from core.blackboard import Blackboard, BlackboardEvent, EventType


@dataclass
class EvaluationMetric:
    """评估指标数据结构"""
    metric_id: str
    name: str
    description: str
    value: float
    max_value: float
    weight: float
    category: str  # quality, efficiency, innovation, feasibility


class EvaluationAgent(LLMBaseAgent):
    """
    评估Agent - 系统性能评估与优化专家

    职责:
    - 评估各Agent的工作质量
    - 监控系统整体性能
    - 提供优化建议和改进方案
    - 生成评估报告和性能指标
    """

    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="EvaluationAgent",
            agent_type="evaluator",
            description="评估Agent - 质量控制专家",
            subscribed_events=[
                EventType.TASK_COMPLETED,
                EventType.REPORT_GENERATED,
                EventType.EXPERIMENT_PLAN,
                EventType.MODEL_RESULT
            ],
            max_concurrent_tasks=2
        )
        super().__init__(config, blackboard, llm_client)
        
        self.evaluation_history: List[Dict] = []
        self.performance_trends: Dict[str, List[float]] = {}
        
        # 定义输入输出Schema
        self.input_schema = {
            "type": "object",
            "properties": {
                "work_type": {"type": "string"},
                "content": {"type": "object"},
                "criteria": {"type": "array"}
            }
        }
        
        self.output_schema = {
            "type": "object",
            "properties": {
                "evaluation": {"type": "object"},
                "target_agent": {"type": "string"},
                "evaluation_type": {"type": "string"}
            },
            "required": ["evaluation", "evaluation_type"]
        }

    async def _load_prompt_templates(self):
        """加载评估模板"""
        self.prompt_templates = {
            "comprehensive_evaluation": """
系统：你是科研系统评估专家，请对Agent的工作成果进行全面评估。

评估对象：{evaluation_target}
工作内容：{work_content}
任务类型：{task_type}
执行时间：{execution_time}

请从以下5个维度进行综合评估：

1. **知识贡献度评估**（权重30%）：
   - 提供信息的准确性和可靠性
   - 知识的深度和广度
   - 引用来源的权威性
   - 对问题解决的实际贡献

2. **准确性评估**（权重25%）：
   - 事实正确性
   - 逻辑推理的严密性
   - 数据的精确度
   - 结论的可靠性

3. **响应效率评估**（权重15%）：
   - 任务完成时间
   - 资源利用效率
   - 处理复杂度与时间的平衡
   - 迭代优化的效率

4. **协作度评估**（权重15%）：
   - 与其他Agent的配合程度
   - 信息共享的及时性和完整性
   - 对反馈的响应和改进
   - 团队目标的贡献度

5. **创新度评估**（权重15%）：
   - 解决方案的新颖性
   - 方法的创造性
   - 突破常规的程度
   - 对领域的潜在贡献

请以JSON格式返回评估结果：
{{
    "overall_score": 0-100的综合评分,
    "dimension_scores": {{
        "knowledge_contribution": {{
            "score": 0-100,
            "evidence": ["证据1", "证据2"],
            "strengths": ["优势1", "优势2"],
            "weaknesses": ["不足1", "不足2"]
        }},
        "accuracy": {{
            "score": 0-100,
            "evidence": ["证据1", "证据2"],
            "error_count": 0,
            "error_details": ["错误描述"]
        }},
        "response_efficiency": {{
            "score": 0-100,
            "actual_time": "实际用时",
            "expected_time": "预期用时",
            "efficiency_ratio": 1.0
        }},
        "collaboration": {{
            "score": 0-100,
            "interaction_count": 0,
            "feedback_responsiveness": "高/中/低",
            "contribution_quality": "优秀/良好/一般"
        }},
        "innovation": {{
            "score": 0-100,
            "novel_aspects": ["创新点1", "创新点2"],
            "creativity_level": "突破性/渐进性/常规",
            "potential_impact": "高/中/低"
        }}
    }},
    "performance_grade": "A+/A/B+/B/C+/C/D",
    "improvement_recommendations": [
        {{
            "dimension": "需改进的维度",
            "specific_suggestion": "具体建议",
            "priority": "高/中/低"
        }}
    ],
    "commendations": ["表扬点1", "表扬点2"],
    "optimization_suggestions": {{
        "short_term": ["短期优化建议1", "建议2"],
        "long_term": ["长期改进方向1", "方向2"]
    }},
    "confidence": 0-1的评估置信度
}}
""",

            "agent_performance_comparison": """
系统：请对比分析多个Agent的性能表现。

Agent列表：{agent_list}
评估周期：{evaluation_period}
任务类型：{task_types}

请生成对比分析报告：
{{
    "performance_ranking": [
        {{
            "rank": 1,
            "agent_name": "Agent名称",
            "overall_score": 0-100,
            "key_strengths": ["优势1", "优势2"],
            "improvement_areas": ["改进点1", "改进点2"]
        }}
    ],
    "dimension_comparison": {{
        "knowledge_contribution": {{"best": "Agent名", "worst": "Agent名"}},
        "accuracy": {{"best": "Agent名", "worst": "Agent名"}},
        "efficiency": {{"best": "Agent名", "worst": "Agent名"}},
        "collaboration": {{"best": "Agent名", "worst": "Agent名"}},
        "innovation": {{"best": "Agent名", "worst": "Agent名"}}
    }},
    "collaboration_matrix": {{
        "Agent1-Agent2": "协作评分",
        "Agent1-Agent3": "协作评分"
    }},
    "system_recommendations": ["系统级优化建议1", "建议2"]
}}
""",

            "self_optimization_plan": """
系统：基于评估结果，生成Agent自优化计划。

Agent名称：{agent_name}
当前性能：{current_performance}
历史表现：{historical_data}
改进建议：{improvement_suggestions}

请生成详细的自优化计划：
{{
    "optimization_goals": [
        {{
            "goal": "优化目标描述",
            "target_metric": "目标指标",
            "current_value": "当前值",
            "target_value": "目标值",
            "timeline": "完成时间"
        }}
    ],
    "action_plan": [
        {{
            "action": "具体行动",
            "implementation_method": "实施方法",
            "resources_needed": ["资源1", "资源2"],
            "expected_outcome": "预期结果",
            "milestone": "里程碑"
        }}
    ],
    "monitoring_plan": {{
        "metrics": ["监控指标1", "指标2"],
        "frequency": "监控频率",
        "trigger_conditions": ["触发条件1", "条件2"]
    }},
    "risk_mitigation": [
        {{
            "risk": "风险描述",
            "mitigation_strategy": "缓解策略"
        }}
    ],
    "success_criteria": ["成功标准1", "标准2"]
}}
"""
        }
        
        # 定义评估维度权重
        self.evaluation_weights = {
            "knowledge_contribution": 0.30,
            "accuracy": 0.25,
            "response_efficiency": 0.15,
            "collaboration": 0.15,
            "innovation": 0.15
        }

    async def _process_event_impl(self, event: BlackboardEvent):
        """处理黑板事件的具体实现"""
        try:
            if event.event_type == EventType.TASK_COMPLETED:
                await self._evaluate_task_completion(event)
            elif event.event_type == EventType.AGENT_PERFORMANCE_UPDATE:
                await self._update_agent_performance(event)
            elif event.event_type == EventType.SYSTEM_METRICS_UPDATE:
                await self._update_system_metrics(event)
            elif event.event_type == EventType.EVALUATION_REQUEST:
                await self._handle_evaluation_request(event)

        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")

    async def _evaluate_task_completion(self, event: BlackboardEvent):
        """评估任务完成质量"""
        task_data = event.data
        agent_name = task_data.get("completed_by", "Unknown")
        task_type = task_data.get("task_type", "general")
        
        self.logger.info(f"开始评估 {agent_name} 完成的任务")
        
        try:
            # 获取任务详细信息
            task_content = task_data.get("result", {})
            execution_time = task_data.get("execution_time", "未知")
            
            # 执行综合评估
            evaluation_prompt = self.format_prompt(
                "comprehensive_evaluation",
                evaluation_target=agent_name,
                work_content=json.dumps(task_content, ensure_ascii=False),
                task_type=task_type,
                execution_time=execution_time
            )
            
            evaluation_result = await self.call_llm(
                evaluation_prompt,
                temperature=0.3,
                max_tokens=3000,
                response_format="json"
            )
            
            evaluation_data = json.loads(evaluation_result)
            
            # 创建评估指标
            metrics = []
            for dimension, weight in self.evaluation_weights.items():
                score = evaluation_data.get("dimension_scores", {}).get(dimension, {}).get("score", 0)
                metric = EvaluationMetric(
                    metric_id=f"{dimension}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    name=dimension,
                    description=self._get_dimension_description(dimension),
                    value=score,
                    max_value=100,
                    weight=weight,
                    category=self._get_dimension_category(dimension)
                )
                metrics.append(metric)
            
            # 发布评估结果
            await self._publish_evaluation_result(
                {
                    "evaluation_type": "task_completion",
                    "target_agent": agent_name,
                    "task_id": task_data.get("task_id"),
                    "overall_score": evaluation_data.get("overall_score", 0),
                    "performance_grade": evaluation_data.get("performance_grade", "C"),
                    "dimension_scores": evaluation_data.get("dimension_scores", {}),
                    "metrics": [m.__dict__ for m in metrics],
                    "improvement_recommendations": evaluation_data.get("improvement_recommendations", []),
                    "commendations": evaluation_data.get("commendations", []),
                    "optimization_suggestions": evaluation_data.get("optimization_suggestions", {})
                },
                agent_name,
                "task_evaluation"
            )
            
            # 更新Agent性能历史
            await self._update_agent_performance_history(agent_name, evaluation_data)
            
            # 如果评分较低，生成自优化计划
            if evaluation_data.get("overall_score", 0) < 70:
                await self._generate_optimization_plan(agent_name, evaluation_data)
                
        except Exception as e:
            self.logger.error(f"任务评估失败: {e}")

    def _get_dimension_description(self, dimension: str) -> str:
        """获取评估维度描述"""
        descriptions = {
            "knowledge_contribution": "知识贡献度 - 评估提供信息的价值和贡献",
            "accuracy": "准确性 - 评估结果的正确性和可靠性",
            "response_efficiency": "响应效率 - 评估任务完成的时效性",
            "collaboration": "协作度 - 评估与其他Agent的配合程度",
            "innovation": "创新度 - 评估解决方案的创新性"
        }
        return descriptions.get(dimension, dimension)

    def _get_dimension_category(self, dimension: str) -> str:
        """获取评估维度类别"""
        categories = {
            "knowledge_contribution": "quality",
            "accuracy": "quality",
            "response_efficiency": "efficiency",
            "collaboration": "teamwork",
            "innovation": "creativity"
        }
        return categories.get(dimension, "general")

    async def _update_agent_performance_history(self, agent_name: str, evaluation_data: Dict):
        """更新Agent性能历史记录"""
        history_key = f"agent_performance_history_{agent_name}"
        history = await self.blackboard.get_data(history_key) or []
        
        # 添加新的评估记录
        history.append({
            "timestamp": datetime.now().isoformat(),
            "overall_score": evaluation_data.get("overall_score", 0),
            "dimension_scores": evaluation_data.get("dimension_scores", {}),
            "performance_grade": evaluation_data.get("performance_grade", "C")
        })
        
        # 保留最近100条记录
        if len(history) > 100:
            history = history[-100:]
        
        await self.blackboard.store_data(history_key, history)

    async def _generate_optimization_plan(self, agent_name: str, evaluation_data: Dict):
        """生成Agent自优化计划"""
        # 获取历史性能数据
        history = await self.blackboard.get_data(f"agent_performance_history_{agent_name}") or []
        
        optimization_prompt = self.format_prompt(
            "self_optimization_plan",
            agent_name=agent_name,
            current_performance=json.dumps(evaluation_data, ensure_ascii=False),
            historical_data=json.dumps(history[-10:], ensure_ascii=False),  # 最近10次
            improvement_suggestions=json.dumps(
                evaluation_data.get("improvement_recommendations", []), 
                ensure_ascii=False
            )
        )
        
        optimization_result = await self.call_llm(
            optimization_prompt,
            temperature=0.5,
            max_tokens=2000,
            response_format="json"
        )
        
        optimization_plan = json.loads(optimization_result)
        
        # 存储优化计划
        await self.blackboard.store_data(
            f"agent_optimization_plan_{agent_name}",
            {
                "plan": optimization_plan,
                "created_at": datetime.now().isoformat(),
                "trigger_score": evaluation_data.get("overall_score", 0),
                "status": "pending"
            }
        )
        
        self.logger.info(f"已为 {agent_name} 生成自优化计划")

    async def _evaluate_report_quality(self, event: BlackboardEvent):
        """评估报告质量"""
        report_data = event.data
        
        evaluation = await self._perform_quality_evaluation(
            work_type="科研报告",
            content=report_data,
            criteria=["结构完整性", "内容准确性", "逻辑清晰性", "语言规范性"]
        )
        
        await self._publish_evaluation_result(evaluation, event.source_agent, "report_evaluation")

    async def _perform_quality_evaluation(self, work_type: str, content: Dict, criteria: List[str]) -> Dict:
        """执行质量评估"""
        prompt = self.format_prompt(
            "quality_evaluation",
            work_type=work_type,
            content=json.dumps(content, ensure_ascii=False),
            criteria=", ".join(criteria)
        )
        
        response = await self.call_llm(prompt, response_format="json")
        evaluation = json.loads(response)
        
        # 添加时间戳和元数据
        evaluation.update({
            "evaluation_id": str(uuid.uuid4()),
            "evaluated_at": datetime.now().isoformat(),
            "evaluator": self.config.name
        })
        
        return evaluation

    async def _publish_evaluation_result(self, evaluation: Dict, target_agent: str, evaluation_type: str):
        """发布评估结果事件"""
        event = BlackboardEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.EVALUATION_RESULT,
            source_agent=self.config.name,
            data={
                "evaluation": evaluation,
                "target_agent": target_agent,
                "evaluation_type": evaluation_type
            },
            timestamp=datetime.now(),
            target_agents=[target_agent]
        )
        
        await self.blackboard.publish_event(event)
        self.logger.info(f"评估结果已发布: {evaluation_type}")

    async def generate_system_performance_report(self) -> Dict:
        """生成系统性能报告"""
        system_state = await self.blackboard.get_system_state()
        
        # 收集性能指标
        efficiency_metrics = self._calculate_efficiency_metrics()
        quality_metrics = self._calculate_quality_metrics()
        time_stats = self._calculate_time_statistics()
        
        prompt = self.format_prompt(
            "system_performance",
            system_state=json.dumps(system_state, ensure_ascii=False),
            efficiency_metrics=json.dumps(efficiency_metrics, ensure_ascii=False),
            quality_metrics=json.dumps(quality_metrics, ensure_ascii=False),
            time_stats=json.dumps(time_stats, ensure_ascii=False)
        )
        
        response = await self.call_llm(prompt, response_format="json")
        performance_report = json.loads(response)
        
        # 存储评估历史
        self.evaluation_history.append({
            "timestamp": datetime.now(),
            "report": performance_report
        })
        
        return performance_report

    def _calculate_efficiency_metrics(self) -> Dict:
        """计算效率指标"""
        return {
            "average_task_time": 0.0,
            "throughput": 0.0,
            "resource_utilization": 0.0
        }

    def _calculate_quality_metrics(self) -> Dict:
        """计算质量指标"""
        return {
            "average_quality_score": 0.0,
            "consistency_score": 0.0,
            "innovation_index": 0.0
        }

    def _calculate_time_statistics(self) -> Dict:
        """计算时间统计"""
        return {
            "total_processing_time": 0.0,
            "average_response_time": 0.0,
            "peak_load_times": []
        }

    async def _update_agent_performance(self, event: BlackboardEvent):
        """更新Agent性能数据"""
        self.logger.info(f"更新Agent性能数据: {event.event_id}")
        # 这是一个占位符方法
        pass

    async def _update_system_metrics(self, event: BlackboardEvent):
        """更新系统指标"""
        self.logger.info(f"更新系统指标: {event.event_id}")
        # 这是一个占位符方法
        pass

    async def _handle_evaluation_request(self, event: BlackboardEvent):
        """处理评估请求"""
        self.logger.info(f"处理评估请求: {event.event_id}")
        # 这是一个占位符方法
        pass
