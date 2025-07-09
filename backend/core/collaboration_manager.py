"""
协作管理器 - 实现Agent间智能协作
包含：协作模式检测、任务分解与合并、知识共享机制
"""
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import networkx as nx

from core.blackboard import Blackboard, BlackboardEvent, EventType
from loguru import logger


class CollaborationMode(Enum):
    """协作模式"""
    SEQUENTIAL = "sequential"        # 顺序协作
    PARALLEL = "parallel"           # 并行协作
    HIERARCHICAL = "hierarchical"   # 层次协作
    PEER_TO_PEER = "peer_to_peer"  # 对等协作
    HYBRID = "hybrid"               # 混合协作


class CollaborationStatus(Enum):
    """协作状态"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollaborationNode:
    """协作节点"""
    agent_name: str
    role: str  # leader, collaborator, specialist, reviewer
    capabilities: List[str]
    contribution_weight: float = 1.0
    trust_score: float = 0.8
    communication_efficiency: float = 0.9


@dataclass
class CollaborationTask:
    """协作任务"""
    collaboration_id: str
    main_task_id: str
    session_id: str
    collaboration_mode: CollaborationMode
    participants: List[CollaborationNode]
    task_decomposition: List[Dict[str, Any]]
    knowledge_requirements: List[str]
    expected_outcome: str
    coordination_agent: Optional[str] = None
    status: CollaborationStatus = CollaborationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    collaboration_graph: Optional[nx.DiGraph] = None


@dataclass
class KnowledgeExchange:
    """知识交换记录"""
    exchange_id: str
    source_agent: str
    target_agent: str
    knowledge_type: str  # data, insight, method, result
    content: Dict[str, Any]
    relevance_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    usage_count: int = 0


class CollaborationManager:
    """
    协作管理器
    
    核心功能:
    1. 协作需求识别和模式选择
    2. 任务智能分解与分配
    3. Agent间知识共享
    4. 协作过程监控与优化
    5. 结果整合与评估
    """
    
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.active_collaborations: Dict[str, CollaborationTask] = {}
        self.completed_collaborations: Dict[str, CollaborationTask] = {}
        self.knowledge_repository: Dict[str, KnowledgeExchange] = {}
        self.agent_collaboration_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.collaboration_patterns: Dict[str, Dict[str, Any]] = {}
        
        # 协作网络图
        self.collaboration_network = nx.Graph()
        self.trust_matrix: Dict[Tuple[str, str], float] = {}
        
        # 性能指标
        self.collaboration_metrics = {
            "total_collaborations": 0,
            "successful_collaborations": 0,
            "average_collaboration_time": 0.0,
            "knowledge_sharing_frequency": 0.0,
            "agent_synergy_scores": {}
        }
        
        logger.info("协作管理器初始化完成")
    
    async def detect_collaboration_need(self, task_data: Dict[str, Any]) -> Optional[CollaborationMode]:
        """检测是否需要协作以及协作模式"""
        task_description = task_data.get("description", "")
        task_type = task_data.get("task_type", "")
        complexity = task_data.get("complexity_score", 0.5)
        
        # 协作需求指标
        collaboration_indicators = {
            "multi_domain": self._check_multi_domain_requirements(task_description),
            "high_complexity": complexity > 0.7,
            "explicit_collaboration": any(keyword in task_description.lower() 
                                        for keyword in ["协作", "配合", "整合", "综合", "联合"]),
            "resource_intensive": task_data.get("estimated_duration", 0) > 300,  # 5分钟以上
            "quality_critical": task_data.get("priority", 3) >= 4
        }
        
        collaboration_score = sum(collaboration_indicators.values()) / len(collaboration_indicators)
        
        if collaboration_score < 0.3:
            return None  # 不需要协作
        
        # 选择协作模式
        if collaboration_indicators["multi_domain"] and collaboration_indicators["high_complexity"]:
            return CollaborationMode.HIERARCHICAL
        elif collaboration_indicators["resource_intensive"]:
            return CollaborationMode.PARALLEL
        elif collaboration_indicators["quality_critical"]:
            return CollaborationMode.PEER_TO_PEER
        else:
            return CollaborationMode.SEQUENTIAL
    
    def _check_multi_domain_requirements(self, description: str) -> bool:
        """检查是否需要多领域专业知识"""
        domain_keywords = {
            "literature": ["文献", "论文", "研究", "调研"],
            "modeling": ["建模", "模型", "算法", "仿真"],
            "analysis": ["分析", "评估", "统计", "数据"],
            "design": ["设计", "实验", "方案", "架构"],
            "evaluation": ["评价", "验证", "测试", "检验"]
        }
        
        detected_domains = []
        for domain, keywords in domain_keywords.items():
            if any(keyword in description for keyword in keywords):
                detected_domains.append(domain)
        
        return len(detected_domains) >= 2
    
    async def initiate_collaboration(self, task_data: Dict[str, Any], 
                                   collaboration_mode: CollaborationMode) -> str:
        """发起协作"""
        try:
            collaboration_id = f"collab_{uuid.uuid4().hex[:8]}"
            
            # 选择参与者
            participants = await self._select_collaboration_participants(task_data, collaboration_mode)
            
            if len(participants) < 2:
                logger.warning("无法找到足够的协作参与者")
                return None
            
            # 任务分解
            task_decomposition = await self._decompose_collaborative_task(task_data, participants, collaboration_mode)
            
            # 构建协作图
            collaboration_graph = await self._build_collaboration_graph(participants, collaboration_mode)
            
            # 创建协作任务
            collaboration_task = CollaborationTask(
                collaboration_id=collaboration_id,
                main_task_id=task_data.get("task_id", ""),
                session_id=task_data.get("session_id", ""),
                collaboration_mode=collaboration_mode,
                participants=participants,
                task_decomposition=task_decomposition,
                knowledge_requirements=task_data.get("required_capabilities", []),
                expected_outcome=task_data.get("description", ""),
                coordination_agent=self._select_coordination_agent(participants),
                collaboration_graph=collaboration_graph
            )
            
            self.active_collaborations[collaboration_id] = collaboration_task
            
            # 发布协作开始事件
            await self.blackboard.create_event(
                EventType.TASK_CREATED,
                source_agent="CollaborationManager",
                data={
                    "collaboration_id": collaboration_id,
                    "collaboration_mode": collaboration_mode.value,
                    "participants": [p.agent_name for p in participants],
                    "task_decomposition": task_decomposition,
                    "coordination_agent": collaboration_task.coordination_agent
                },
                target_agents=[p.agent_name for p in participants]
            )
            
            # 启动协作监控
            asyncio.create_task(self._monitor_collaboration(collaboration_task))
            
            logger.info(f"协作发起成功: {collaboration_id}, 模式: {collaboration_mode.value}, 参与者: {len(participants)}")
            return collaboration_id
            
        except Exception as e:
            logger.error(f"协作发起失败: {e}")
            return None
    
    async def _select_collaboration_participants(self, task_data: Dict[str, Any], 
                                               collaboration_mode: CollaborationMode) -> List[CollaborationNode]:
        """选择协作参与者"""
        participants = []
        
        # 获取可用Agent信息（从黑板获取）
        system_state = await self.blackboard.get_system_state()
        available_agents = system_state.get("available_agents", {})
        
        # 根据任务需求和协作模式选择参与者
        required_capabilities = task_data.get("required_capabilities", [])
        task_type = task_data.get("task_type", "")
        
        # 基本能力需求映射
        capability_to_agents = {
            "literature_search": ["InformationAgent", "EnhancedInformationAgent"],
            "modeling": ["ModelingAgent"],
            "analysis": ["EvaluationAgent", "CritiqueAgent"],
            "verification": ["VerificationAgent"],
            "report": ["ReportAgent"]
        }
        
        selected_agents = set()
        
        # 1. 基于任务类型选择核心Agent
        if task_type in capability_to_agents:
            for agent_name in capability_to_agents[task_type]:
                if agent_name in available_agents:
                    selected_agents.add(agent_name)
        
        # 2. 基于需求能力选择补充Agent
        for capability in required_capabilities:
            if capability in capability_to_agents:
                for agent_name in capability_to_agents[capability]:
                    if agent_name in available_agents:
                        selected_agents.add(agent_name)
        
        # 3. 根据协作模式调整选择
        if collaboration_mode == CollaborationMode.HIERARCHICAL:
            # 确保有主导Agent
            if "MainAgent" in available_agents:
                selected_agents.add("MainAgent")
        
        elif collaboration_mode == CollaborationMode.PEER_TO_PEER:
            # 确保有质量控制Agent
            if "CritiqueAgent" in available_agents:
                selected_agents.add("CritiqueAgent")
        
        # 创建协作节点
        for agent_name in selected_agents:
            agent_info = available_agents.get(agent_name, {})
            
            # 确定角色
            role = self._determine_agent_role(agent_name, collaboration_mode)
            
            # 获取历史协作信息
            trust_score = await self._get_agent_trust_score(agent_name)
            communication_efficiency = await self._get_communication_efficiency(agent_name)
            
            node = CollaborationNode(
                agent_name=agent_name,
                role=role,
                capabilities=agent_info.get("capabilities", []),
                trust_score=trust_score,
                communication_efficiency=communication_efficiency
            )
            participants.append(node)
        
        return participants
    
    def _determine_agent_role(self, agent_name: str, collaboration_mode: CollaborationMode) -> str:
        """确定Agent在协作中的角色"""
        role_mapping = {
            "MainAgent": "leader",
            "CritiqueAgent": "reviewer",
            "VerificationAgent": "reviewer",
            "InformationAgent": "specialist",
            "EnhancedInformationAgent": "specialist",
            "ModelingAgent": "specialist",
            "EvaluationAgent": "specialist",
            "ReportAgent": "collaborator"
        }
        
        return role_mapping.get(agent_name, "collaborator")
    
    async def _get_agent_trust_score(self, agent_name: str) -> float:
        """获取Agent信任度评分"""
        history = self.agent_collaboration_history.get(agent_name, [])
        if not history:
            return 0.8  # 默认信任度
        
        # 基于历史协作成功率计算
        recent_collaborations = history[-10:]  # 最近10次协作
        success_rate = sum(1 for c in recent_collaborations if c.get("success", False)) / len(recent_collaborations)
        
        return min(max(success_rate, 0.1), 1.0)
    
    async def _get_communication_efficiency(self, agent_name: str) -> float:
        """获取Agent通信效率"""
        # 基于历史响应时间和信息质量评估
        history = self.agent_collaboration_history.get(agent_name, [])
        if not history:
            return 0.9  # 默认效率
        
        recent_interactions = history[-20:]
        avg_response_time = sum(c.get("response_time", 1.0) for c in recent_interactions) / len(recent_interactions)
        
        # 响应时间越短，效率越高
        efficiency = max(0.1, 2.0 / (1.0 + avg_response_time))
        return min(efficiency, 1.0)
    
    async def _decompose_collaborative_task(self, task_data: Dict[str, Any], 
                                          participants: List[CollaborationNode],
                                          collaboration_mode: CollaborationMode) -> List[Dict[str, Any]]:
        """分解协作任务"""
        task_description = task_data.get("description", "")
        main_task_id = task_data.get("task_id", "")
        
        subtasks = []
        
        if collaboration_mode == CollaborationMode.SEQUENTIAL:
            # 顺序协作：按照逻辑顺序分解
            sequence_steps = [
                {"step": "information_gathering", "agents": ["InformationAgent", "EnhancedInformationAgent"]},
                {"step": "analysis", "agents": ["EvaluationAgent", "ModelingAgent"]},
                {"step": "review", "agents": ["CritiqueAgent", "VerificationAgent"]},
                {"step": "synthesis", "agents": ["ReportAgent"]}
            ]
            
            for i, step in enumerate(sequence_steps):
                available_agents = [p.agent_name for p in participants if p.agent_name in step["agents"]]
                if available_agents:
                    subtasks.append({
                        "subtask_id": f"{main_task_id}_seq_{i}",
                        "step_name": step["step"],
                        "assigned_agents": available_agents[:1],  # 每步选一个主要Agent
                        "dependencies": [f"{main_task_id}_seq_{i-1}"] if i > 0 else [],
                        "description": f"执行{step['step']}阶段的{task_description}",
                        "estimated_duration": 60  # 每个子任务60秒
                    })
        
        elif collaboration_mode == CollaborationMode.PARALLEL:
            # 并行协作：同时执行不同方面
            parallel_aspects = [
                {"aspect": "literature_review", "agents": ["InformationAgent"]},
                {"aspect": "data_analysis", "agents": ["EvaluationAgent"]},
                {"aspect": "model_development", "agents": ["ModelingAgent"]},
                {"aspect": "quality_assessment", "agents": ["CritiqueAgent"]}
            ]
            
            for i, aspect in enumerate(parallel_aspects):
                available_agents = [p.agent_name for p in participants if p.agent_name in aspect["agents"]]
                if available_agents:
                    subtasks.append({
                        "subtask_id": f"{main_task_id}_par_{i}",
                        "aspect_name": aspect["aspect"],
                        "assigned_agents": available_agents,
                        "dependencies": [],
                        "description": f"从{aspect['aspect']}角度处理{task_description}",
                        "estimated_duration": 90
                    })
        
        elif collaboration_mode == CollaborationMode.HIERARCHICAL:
            # 层次协作：主导Agent分配子任务
            leader_agents = [p.agent_name for p in participants if p.role == "leader"]
            specialist_agents = [p.agent_name for p in participants if p.role == "specialist"]
            
            if leader_agents:
                # 主任务由领导Agent负责
                subtasks.append({
                    "subtask_id": f"{main_task_id}_main",
                    "task_type": "coordination",
                    "assigned_agents": leader_agents[:1],
                    "dependencies": [],
                    "description": f"协调和整合{task_description}",
                    "estimated_duration": 120
                })
                
                # 专业子任务
                for i, agent in enumerate(specialist_agents):
                    subtasks.append({
                        "subtask_id": f"{main_task_id}_spec_{i}",
                        "task_type": "specialization",
                        "assigned_agents": [agent],
                        "dependencies": [f"{main_task_id}_main"],
                        "description": f"专业化处理{task_description}的特定方面",
                        "estimated_duration": 90
                    })
        
        elif collaboration_mode == CollaborationMode.PEER_TO_PEER:
            # 对等协作：每个Agent贡献自己的专长
            for i, participant in enumerate(participants):
                subtasks.append({
                    "subtask_id": f"{main_task_id}_peer_{i}",
                    "contribution_type": f"{participant.agent_name}_expertise",
                    "assigned_agents": [participant.agent_name],
                    "dependencies": [],
                    "description": f"基于{participant.agent_name}专长贡献{task_description}",
                    "estimated_duration": 75
                })
        
        return subtasks
    
    async def _build_collaboration_graph(self, participants: List[CollaborationNode], 
                                       collaboration_mode: CollaborationMode) -> nx.DiGraph:
        """构建协作图"""
        graph = nx.DiGraph()
        
        # 添加节点
        for participant in participants:
            graph.add_node(participant.agent_name, 
                          role=participant.role,
                          trust_score=participant.trust_score,
                          capabilities=participant.capabilities)
        
        # 根据协作模式添加边
        if collaboration_mode == CollaborationMode.SEQUENTIAL:
            # 顺序连接
            for i in range(len(participants) - 1):
                graph.add_edge(participants[i].agent_name, participants[i+1].agent_name, 
                             relation="sequential", weight=1.0)
        
        elif collaboration_mode == CollaborationMode.HIERARCHICAL:
            # 层次结构
            leaders = [p for p in participants if p.role == "leader"]
            others = [p for p in participants if p.role != "leader"]
            
            for leader in leaders:
                for other in others:
                    graph.add_edge(leader.agent_name, other.agent_name, 
                                 relation="supervises", weight=1.0)
                    graph.add_edge(other.agent_name, leader.agent_name, 
                                 relation="reports_to", weight=0.8)
        
        elif collaboration_mode == CollaborationMode.PEER_TO_PEER:
            # 全连接
            for i, p1 in enumerate(participants):
                for j, p2 in enumerate(participants):
                    if i != j:
                        graph.add_edge(p1.agent_name, p2.agent_name, 
                                     relation="peer_communication", weight=0.9)
        
        return graph
    
    def _select_coordination_agent(self, participants: List[CollaborationNode]) -> Optional[str]:
        """选择协调Agent"""
        # 优先选择leader角色
        leaders = [p for p in participants if p.role == "leader"]
        if leaders:
            return max(leaders, key=lambda p: p.trust_score).agent_name
        
        # 否则选择信任度最高的
        return max(participants, key=lambda p: p.trust_score).agent_name if participants else None
    
    async def _monitor_collaboration(self, collaboration_task: CollaborationTask):
        """监控协作过程"""
        try:
            collaboration_task.status = CollaborationStatus.ACTIVE
            collaboration_task.start_time = datetime.now()
            
            logger.info(f"开始监控协作: {collaboration_task.collaboration_id}")
            
            # 监控协作进展
            while collaboration_task.status == CollaborationStatus.ACTIVE:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                # 检查协作进展
                progress = await self._check_collaboration_progress(collaboration_task)
                
                if progress["completed_ratio"] >= 1.0:
                    await self._complete_collaboration(collaboration_task)
                    break
                
                # 检查是否需要干预
                if progress["issues"]:
                    await self._handle_collaboration_issues(collaboration_task, progress["issues"])
                
                # 超时检查
                if datetime.now() - collaboration_task.start_time > timedelta(minutes=30):
                    logger.warning(f"协作超时: {collaboration_task.collaboration_id}")
                    await self._handle_collaboration_timeout(collaboration_task)
                    break
        
        except Exception as e:
            logger.error(f"协作监控失败: {collaboration_task.collaboration_id}, 错误: {e}")
            collaboration_task.status = CollaborationStatus.FAILED
    
    async def _check_collaboration_progress(self, collaboration_task: CollaborationTask) -> Dict[str, Any]:
        """检查协作进展"""
        total_subtasks = len(collaboration_task.task_decomposition)
        completed_subtasks = len([st for st in collaboration_task.task_decomposition 
                                if st.get("status") == "completed"])
        
        progress = {
            "completed_ratio": completed_subtasks / total_subtasks if total_subtasks > 0 else 0,
            "active_subtasks": len([st for st in collaboration_task.task_decomposition 
                                  if st.get("status") == "active"]),
            "issues": []
        }
        
        # 检查潜在问题
        current_time = datetime.now()
        for subtask in collaboration_task.task_decomposition:
            if subtask.get("status") == "active":
                start_time = subtask.get("start_time")
                if start_time and current_time - start_time > timedelta(minutes=5):
                    progress["issues"].append({
                        "type": "subtask_delay",
                        "subtask_id": subtask["subtask_id"],
                        "agent": subtask.get("assigned_agents", [])
                    })
        
        return progress
    
    async def _complete_collaboration(self, collaboration_task: CollaborationTask):
        """完成协作"""
        collaboration_task.status = CollaborationStatus.COMPLETED
        collaboration_task.end_time = datetime.now()
        
        # 整合结果
        final_result = await self._integrate_collaboration_results(collaboration_task)
        
        # 移动到已完成列表
        collaboration_id = collaboration_task.collaboration_id
        self.completed_collaborations[collaboration_id] = self.active_collaborations.pop(collaboration_id)
        
        # 更新协作历史
        await self._update_collaboration_history(collaboration_task, success=True)
        
        # 发布协作完成事件
        await self.blackboard.create_event(
            EventType.TASK_COMPLETED,
            source_agent="CollaborationManager",
            data={
                "collaboration_id": collaboration_id,
                "final_result": final_result,
                "duration": (collaboration_task.end_time - collaboration_task.start_time).total_seconds(),
                "participants": [p.agent_name for p in collaboration_task.participants]
            }
        )
        
        logger.info(f"协作完成: {collaboration_id}")
    
    async def _integrate_collaboration_results(self, collaboration_task: CollaborationTask) -> Dict[str, Any]:
        """整合协作结果"""
        integrated_result = {
            "collaboration_id": collaboration_task.collaboration_id,
            "collaboration_mode": collaboration_task.collaboration_mode.value,
            "participants": [p.agent_name for p in collaboration_task.participants],
            "subtask_results": collaboration_task.intermediate_results,
            "synthesis": {},
            "quality_metrics": {}
        }
        
        # 根据协作模式整合结果
        if collaboration_task.collaboration_mode == CollaborationMode.SEQUENTIAL:
            # 顺序协作：按序整合
            integrated_result["synthesis"] = self._sequential_integration(collaboration_task.intermediate_results)
        
        elif collaboration_task.collaboration_mode == CollaborationMode.PARALLEL:
            # 并行协作：合并不同方面
            integrated_result["synthesis"] = self._parallel_integration(collaboration_task.intermediate_results)
        
        elif collaboration_task.collaboration_mode == CollaborationMode.HIERARCHICAL:
            # 层次协作：层次整合
            integrated_result["synthesis"] = self._hierarchical_integration(collaboration_task.intermediate_results)
        
        elif collaboration_task.collaboration_mode == CollaborationMode.PEER_TO_PEER:
            # 对等协作：共识整合
            integrated_result["synthesis"] = self._peer_integration(collaboration_task.intermediate_results)
        
        # 计算质量指标
        integrated_result["quality_metrics"] = await self._calculate_collaboration_quality(collaboration_task)
        
        return integrated_result
    
    def _sequential_integration(self, intermediate_results: Dict[str, Any]) -> Dict[str, Any]:
        """顺序整合结果"""
        synthesis = {"integration_method": "sequential", "stages": []}
        
        # 按照时间顺序整合
        sorted_results = sorted(intermediate_results.items(), 
                              key=lambda x: x[1].get("timestamp", datetime.now()))
        
        for stage_id, result in sorted_results:
            synthesis["stages"].append({
                "stage": stage_id,
                "output": result.get("output", {}),
                "timestamp": result.get("timestamp", "").isoformat() if isinstance(result.get("timestamp"), datetime) else str(result.get("timestamp", ""))
            })
        
        return synthesis
    
    def _parallel_integration(self, intermediate_results: Dict[str, Any]) -> Dict[str, Any]:
        """并行整合结果"""
        synthesis = {"integration_method": "parallel", "aspects": {}}
        
        for aspect_id, result in intermediate_results.items():
            synthesis["aspects"][aspect_id] = {
                "contribution": result.get("output", {}),
                "quality_score": result.get("quality_score", 0.8)
            }
        
        return synthesis
    
    def _hierarchical_integration(self, intermediate_results: Dict[str, Any]) -> Dict[str, Any]:
        """层次整合结果"""
        synthesis = {"integration_method": "hierarchical", "hierarchy": {}}
        
        # 区分主任务和子任务结果
        main_results = {k: v for k, v in intermediate_results.items() if "main" in k}
        sub_results = {k: v for k, v in intermediate_results.items() if "spec" in k}
        
        synthesis["hierarchy"]["main_coordination"] = main_results
        synthesis["hierarchy"]["specialist_contributions"] = sub_results
        
        return synthesis
    
    def _peer_integration(self, intermediate_results: Dict[str, Any]) -> Dict[str, Any]:
        """对等整合结果"""
        synthesis = {"integration_method": "peer_consensus", "contributions": {}}
        
        for peer_id, result in intermediate_results.items():
            synthesis["contributions"][peer_id] = {
                "expertise_area": result.get("expertise_area", "general"),
                "contribution": result.get("output", {}),
                "confidence": result.get("confidence", 0.8)
            }
        
        return synthesis
    
    async def _calculate_collaboration_quality(self, collaboration_task: CollaborationTask) -> Dict[str, float]:
        """计算协作质量指标"""
        duration = (collaboration_task.end_time - collaboration_task.start_time).total_seconds()
        estimated_duration = sum(st.get("estimated_duration", 60) for st in collaboration_task.task_decomposition)
        
        quality_metrics = {
            "time_efficiency": min(estimated_duration / duration, 1.0) if duration > 0 else 0.0,
            "participant_satisfaction": sum(p.trust_score for p in collaboration_task.participants) / len(collaboration_task.participants),
            "result_completeness": len(collaboration_task.intermediate_results) / len(collaboration_task.task_decomposition) if collaboration_task.task_decomposition else 1.0,
            "communication_efficiency": sum(p.communication_efficiency for p in collaboration_task.participants) / len(collaboration_task.participants)
        }
        
        quality_metrics["overall_quality"] = sum(quality_metrics.values()) / len(quality_metrics)
        
        return quality_metrics
    
    async def _update_collaboration_history(self, collaboration_task: CollaborationTask, success: bool):
        """更新协作历史"""
        collaboration_record = {
            "collaboration_id": collaboration_task.collaboration_id,
            "collaboration_mode": collaboration_task.collaboration_mode.value,
            "success": success,
            "duration": (collaboration_task.end_time - collaboration_task.start_time).total_seconds() if collaboration_task.end_time else 0,
            "timestamp": datetime.now()
        }
        
        # 更新每个参与者的历史
        for participant in collaboration_task.participants:
            self.agent_collaboration_history[participant.agent_name].append(collaboration_record.copy())
        
        # 更新协作指标
        self.collaboration_metrics["total_collaborations"] += 1
        if success:
            self.collaboration_metrics["successful_collaborations"] += 1
    
    async def _handle_collaboration_issues(self, collaboration_task: CollaborationTask, issues: List[Dict[str, Any]]):
        """处理协作问题"""
        for issue in issues:
            if issue["type"] == "subtask_delay":
                logger.warning(f"检测到子任务延迟: {issue['subtask_id']}")
                # 可以实施干预措施，如重新分配或提供帮助
    
    async def _handle_collaboration_timeout(self, collaboration_task: CollaborationTask):
        """处理协作超时"""
        collaboration_task.status = CollaborationStatus.FAILED
        collaboration_task.end_time = datetime.now()
        
        # 移动到失败列表
        collaboration_id = collaboration_task.collaboration_id
        if collaboration_id in self.active_collaborations:
            del self.active_collaborations[collaboration_id]
        
        await self._update_collaboration_history(collaboration_task, success=False)
        
        logger.error(f"协作超时失败: {collaboration_id}")
    
    def get_collaboration_status(self, collaboration_id: str) -> Optional[Dict[str, Any]]:
        """获取协作状态"""
        if collaboration_id in self.active_collaborations:
            task = self.active_collaborations[collaboration_id]
            return {
                "collaboration_id": collaboration_id,
                "status": task.status.value,
                "mode": task.collaboration_mode.value,
                "participants": [p.agent_name for p in task.participants],
                "progress": len(task.intermediate_results) / len(task.task_decomposition) if task.task_decomposition else 0,
                "start_time": task.start_time.isoformat() if task.start_time else None
            }
        
        if collaboration_id in self.completed_collaborations:
            task = self.completed_collaborations[collaboration_id]
            return {
                "collaboration_id": collaboration_id,
                "status": task.status.value,
                "mode": task.collaboration_mode.value,
                "completed": True,
                "duration": (task.end_time - task.start_time).total_seconds() if task.end_time and task.start_time else 0
            }
        
        return None
    
    def get_collaboration_metrics(self) -> Dict[str, Any]:
        """获取协作指标"""
        success_rate = (self.collaboration_metrics["successful_collaborations"] / 
                       self.collaboration_metrics["total_collaborations"] 
                       if self.collaboration_metrics["total_collaborations"] > 0 else 0)
        
        return {
            "total_collaborations": self.collaboration_metrics["total_collaborations"],
            "success_rate": success_rate,
            "active_collaborations": len(self.active_collaborations),
            "average_collaboration_time": self.collaboration_metrics.get("average_collaboration_time", 0),
            "collaboration_network_size": self.collaboration_network.number_of_nodes(),
            "knowledge_exchanges": len(self.knowledge_repository)
        } 