#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黑板系统 - Agent间通信和协调机制
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger # type: ignore


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 进行中
    SUCCESS = "success"      # 成功完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


class EventType(Enum):
    """事件类型枚举"""
    # 基础事件
    TASK_STARTED = "task_started"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CREATED = "task_created"
    
    # 主Agent协调事件
    PROBLEM_PARSED = "problem_parsed"
    SUBTASK_CREATED = "subtask_created"
    PLAN_UPDATED = "plan_updated"
    FINAL_INTEGRATION = "final_integration"
    
    # 信息获取Agent事件
    LITERATURE_SEARCH_REQUEST = "literature_search_request"
    LITERATURE_SEARCH_COMPLETED = "literature_search_completed"
    INFORMATION_UPDATE = "information_update"
    KNOWLEDGE_GRAPH_CREATED = "knowledge_graph_created"
    RAG_QUERY_PROCESSED = "rag_query_processed"
    
    # 验证Agent事件
    VERIFICATION_REQUEST = "verification_request"
    VERIFICATION_REPORT = "verification_report"
    CONSISTENCY_CHECK = "consistency_check"
    CONFLICT_WARNING = "conflict_warning"
    FEASIBILITY_CHECK = "feasibility_check"
    
    # 批判Agent事件
    CRITIQUE_REQUEST = "critique_request"
    CRITIQUE_FEEDBACK = "critique_feedback"
    QUALITY_ASSESSMENT = "quality_assessment"
    LOGIC_REVIEW = "logic_review"
    INNOVATION_ASSESSMENT = "innovation_assessment"
    
    # 实验设计Agent事件
    DESIGN_REQUEST = "design_request"
    EXPERIMENT_PLAN = "experiment_plan"
    EXPERIMENT_DRAFT_CREATED = "experiment_draft_created"
    SAFETY_ASSESSMENT = "safety_assessment"
    PROTOCOL_VALIDATION = "protocol_validation"
    
    # 建模Agent事件
    MODEL_REQUEST = "model_request"
    MODEL_RESULT = "model_result"
    SIMULATION_COMPLETED = "simulation_completed"
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    
    # 评估Agent事件
    EVALUATION_REQUEST = "evaluation_request"
    PERFORMANCE_REPORT = "performance_report"
    QUALITY_METRICS = "quality_metrics"
    AGENT_PERFORMANCE_UPDATE = "agent_performance_update"
    
    # 报告生成Agent事件
    REPORT_REQUEST = "report_request"
    REPORT_GENERATED = "report_generated"
    DOCUMENT_CREATED = "document_created"
    
    # 方案相关事件
    SOLUTION_DRAFT_CREATED = "solution_draft_created"
    SOLUTION_VALIDATED = "solution_validated"
    SOLUTION_CRITIQUED = "solution_critiqued"
    SOLUTION_FINALIZED = "solution_finalized"
    
    # Agent间通信
    AGENT_MESSAGE = "agent_message"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    COLLABORATION_EVENT = "collaboration_event"
    
    # 数据更新
    DATA_UPDATED = "data_updated"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    CONTEXT_UPDATED = "context_updated"
    
    # 质量控制
    QUALITY_CHECK = "quality_check"
    REVISION_REQUIRED = "revision_required"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"
    
    # 推理链记录
    REASONING_STEP = "reasoning_step"
    DECISION_MADE = "decision_made"
    INFERENCE_CHAIN = "inference_chain"
    THOUGHT_PROCESS = "thought_process"
    
    # 系统事件
    SYSTEM_STATUS = "system_status"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    RESOURCE_ALLOCATED = "resource_allocated"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


@dataclass
class ReasoningStep:
    """推理步骤数据结构"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    step_type: str = ""  # analysis, inference, decision, validation
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    reasoning_text: str = ""
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    parent_step_id: Optional[str] = None


@dataclass
class TaskRequest:
    """任务请求数据结构"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    task_type: str = ""
    description: str = ""
    assigned_agent: str = ""
    priority: int = 5  # 1-10, 越高越优先
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # 依赖的task_id列表
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: float = 0.0  # 0.0-1.0 进度百分比


@dataclass
class BlackboardEvent:
    """黑板事件数据结构"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.AGENT_MESSAGE
    agent_id: str = ""
    target_agent: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # 0-10, 越高越优先
    processed: bool = False
    session_id: Optional[str] = None  # 会话关联
    reasoning_step_id: Optional[str] = None  # 关联推理步骤
    dependencies: List[str] = field(default_factory=list)  # 依赖的事件ID


class Blackboard:
    """黑板系统 - 提供Agent间的通信和数据共享"""
    
    def __init__(self):
        self.events: List[BlackboardEvent] = []
        self.shared_data: Dict[str, Any] = {}
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[BlackboardEvent] = []
        self.max_history = 1000
        self._lock = asyncio.Lock()
        
        # 推理链管理
        self.reasoning_chains: Dict[str, List[ReasoningStep]] = {}  # session_id -> reasoning steps
        self.reasoning_steps: Dict[str, ReasoningStep] = {}  # step_id -> step
        
        # 会话管理
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 任务分解记录
        self.task_decompositions: Dict[str, Dict[str, Any]] = {}  # session_id -> decomposition data
        
        # 任务状态管理
        self.task_requests: Dict[str, TaskRequest] = {}  # task_id -> TaskRequest
        self.session_tasks: Dict[str, List[str]] = {}  # session_id -> task_id列表
        
        logger.info("🔲 黑板系统初始化完成")
    
    async def publish_event(self, event: BlackboardEvent):
        """发布事件到黑板"""
        async with self._lock:
            self.events.append(event)
            self.event_history.append(event)
            
            # 限制历史记录大小
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history:]
            
            logger.debug(f"📤 发布事件: {event.event_type.value} (ID: {event.event_id})")
            
            # 通知订阅者
            await self._notify_subscribers(event)
    
    async def _notify_subscribers(self, event: BlackboardEvent):
        """通知事件订阅者"""
        subscribers = self.subscribers.get(event.event_type, [])
        
        if subscribers:
            logger.debug(f"🔔 通知 {len(subscribers)} 个订阅者")
            
            # 并行通知所有订阅者
            notification_tasks = []
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        notification_tasks.append(callback(event))
                    else:
                        # 对于非异步回调函数，在线程池中执行
                        notification_tasks.append(
                            asyncio.get_event_loop().run_in_executor(None, callback, event)
                        )
                except Exception as e:
                    logger.error(f"❌ 订阅者回调失败: {e}")
            
            if notification_tasks:
                try:
                    await asyncio.gather(*notification_tasks, return_exceptions=True)
                except Exception as e:
                    logger.error(f"❌ 批量通知订阅者失败: {e}")
    
    async def subscribe(self, event_type: EventType, callback: Callable):
        """订阅事件"""
        async with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            
            self.subscribers[event_type].append(callback)
            logger.debug(f"📋 新增订阅: {event_type.value}")
    
    async def unsubscribe(self, event_type: EventType, callback: Callable):
        """取消订阅"""
        async with self._lock:
            if event_type in self.subscribers:
                try:
                    self.subscribers[event_type].remove(callback)
                    logger.debug(f"🚫 取消订阅: {event_type.value}")
                except ValueError:
                    logger.warning(f"⚠️ 未找到要取消的订阅: {event_type.value}")
    
    async def get_events(self, event_type: Optional[EventType] = None, 
                        agent_id: Optional[str] = None,
                        since: Optional[datetime] = None,
                        limit: int = 100) -> List[BlackboardEvent]:
        """获取事件列表"""
        async with self._lock:
            filtered_events = self.event_history.copy()
            
            # 按事件类型过滤
            if event_type:
                filtered_events = [e for e in filtered_events if e.event_type == event_type]
            
            # 按Agent ID过滤
            if agent_id:
                filtered_events = [e for e in filtered_events if e.agent_id == agent_id]
            
            # 按时间过滤
            if since:
                filtered_events = [e for e in filtered_events if e.timestamp >= since]
            
            # 按时间倒序排序并限制数量
            filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
            return filtered_events[:limit]
    
    async def store_data(self, key: str, value: Any, agent_id: Optional[str] = None):
        """存储共享数据"""
        async with self._lock:
            self.shared_data[key] = {
                "value": value,
                "timestamp": datetime.now(),
                "agent_id": agent_id
            }
            
            # 发布数据更新事件
            await self.publish_event(BlackboardEvent(
                event_type=EventType.DATA_UPDATED,
                agent_id=agent_id or "system",
                data={
                    "key": key,
                    "timestamp": datetime.now().isoformat()
                }
            ))
            
            logger.debug(f"💾 存储数据: {key}")
    
    async def get_data(self, key: str) -> Any:
        """获取共享数据"""
        async with self._lock:
            data_info = self.shared_data.get(key)
            if data_info:
                return data_info["value"]
            return None
    
    async def get_data_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取数据信息（包含元数据）"""
        async with self._lock:
            return self.shared_data.get(key)
    
    async def list_data_keys(self, agent_id: Optional[str] = None) -> List[str]:
        """列出所有数据键"""
        async with self._lock:
            if agent_id:
                return [
                    key for key, info in self.shared_data.items()
                    if info.get("agent_id") == agent_id
                ]
            return list(self.shared_data.keys())
    
    async def delete_data(self, key: str) -> bool:
        """删除共享数据"""
        async with self._lock:
            if key in self.shared_data:
                del self.shared_data[key]
                logger.debug(f"🗑️ 删除数据: {key}")
                return True
            return False
    
    async def clear_events(self, older_than: Optional[datetime] = None):
        """清理事件历史"""
        async with self._lock:
            if older_than:
                self.event_history = [
                    e for e in self.event_history 
                    if e.timestamp >= older_than
                ]
            else:
                self.event_history.clear()
            
            # 清理待处理事件
            self.events = [
                e for e in self.events
                if not e.processed and (not older_than or e.timestamp >= older_than)
            ]
            
            logger.info(f"🧹 事件历史已清理，剩余 {len(self.event_history)} 条记录")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        async with self._lock:
            recent_events = await self.get_events(limit=50)
            
            # 统计事件类型
            event_counts = {}
            for event in recent_events:
                event_type = event.event_type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # 统计活跃Agent
            active_agents = set()
            for event in recent_events:
                if event.agent_id:
                    active_agents.add(event.agent_id)
            
            return {
                "total_events": len(self.event_history),
                "pending_events": len([e for e in self.events if not e.processed]),
                "shared_data_count": len(self.shared_data),
                "recent_event_counts": event_counts,
                "active_agents": list(active_agents),
                "subscribers_count": sum(len(subs) for subs in self.subscribers.values()),
                "last_activity": recent_events[0].timestamp.isoformat() if recent_events else None
            }
    
    async def create_session_context(self, session_id: str) -> Dict[str, Any]:
        """为会话创建上下文"""
        context_key = f"session_{session_id}_context"
        context = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "events": [],
            "data": {},
            "agents": []
        }
        
        await self.store_data(context_key, context, "system")
        return context
    
    async def update_session_context(self, session_id: str, updates: Dict[str, Any]):
        """更新会话上下文"""
        context_key = f"session_{session_id}_context"
        context = await self.get_data(context_key)
        
        if context:
            context.update(updates)
            context["updated_at"] = datetime.now().isoformat()
            await self.store_data(context_key, context, "system")
    
    async def get_session_events(self, session_id: str) -> List[BlackboardEvent]:
        """获取特定会话的事件"""
        all_events = await self.get_events(limit=1000)
        session_events = []
        
        for event in all_events:
            # 检查事件是否与会话相关
            if (event.data.get("session_id") == session_id or
                event.agent_id.endswith(session_id) or
                session_id in str(event.data)):
                session_events.append(event)
        
        return session_events
    
    async def broadcast_message(self, message: str, agent_id: str = "system",
                               event_type: EventType = EventType.AGENT_MESSAGE):
        """广播消息给所有订阅者"""
        await self.publish_event(BlackboardEvent(
            event_type=event_type,
            agent_id=agent_id,
            data={
                "message": message,
                "broadcast": True,
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    async def send_message_to_agent(self, target_agent: str, message: str,
                                   sender_agent: str = "system"):
        """发送消息给特定Agent"""
        await self.publish_event(BlackboardEvent(
            event_type=EventType.AGENT_MESSAGE,
            agent_id=sender_agent,
            target_agent=target_agent,
            data={
                "message": message,
                "sender": sender_agent,
                "recipient": target_agent,
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    async def request_agent_action(self, target_agent: str, action: str, 
                                  parameters: Dict[str, Any],
                                  requester_agent: str = "system") -> str:
        """请求Agent执行特定操作"""
        request_id = str(uuid.uuid4())
        
        await self.publish_event(BlackboardEvent(
            event_type=EventType.AGENT_REQUEST,
            agent_id=requester_agent,
            target_agent=target_agent,
            data={
                "request_id": request_id,
                "action": action,
                "parameters": parameters,
                "requester": requester_agent,
                "timestamp": datetime.now().isoformat()
            }
        ))
        
        return request_id
    
    async def respond_to_request(self, request_id: str, response_data: Any,
                                agent_id: str, success: bool = True):
        """响应Agent请求"""
        await self.publish_event(BlackboardEvent(
            event_type=EventType.AGENT_RESPONSE,
            agent_id=agent_id,
            data={
                "request_id": request_id,
                "response": response_data,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        ))
    
    async def wait_for_response(self, request_id: str, timeout: float = 30.0) -> Any:
        """等待特定请求的响应"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            # 查找响应事件
            response_events = await self.get_events(
                event_type=EventType.AGENT_RESPONSE,
                since=start_time
            )
            
            for event in response_events:
                if event.data.get("request_id") == request_id:
                    return event.data.get("response")
            
            # 短暂等待后重试
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"等待响应超时: {request_id}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            status = await self.get_system_status()
            
            return {
                "status": "healthy",
                "blackboard_status": "operational",
                "event_processing": "normal",
                "data_storage": "available",
                "details": status,
                "check_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"黑板健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "check_time": datetime.now().isoformat()
            }

    async def record_reasoning_step(self, step: ReasoningStep) -> str:
        """记录推理步骤"""
        async with self._lock:
            self.reasoning_steps[step.step_id] = step
            
            # 添加到会话的推理链
            if step.agent_id:
                session_id = getattr(step, 'session_id', 'default')
                if session_id not in self.reasoning_chains:
                    self.reasoning_chains[session_id] = []
                self.reasoning_chains[session_id].append(step)
            
            # 发布推理步骤事件
            await self.publish_event(BlackboardEvent(
                event_type=EventType.REASONING_STEP,
                agent_id=step.agent_id,
                data={
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                    "description": step.description,
                    "confidence": step.confidence
                },
                reasoning_step_id=step.step_id
            ))
            
            logger.debug(f"🧠 记录推理步骤: {step.step_type} by {step.agent_id}")
            return step.step_id
    
    async def get_reasoning_chain(self, session_id: str) -> List[ReasoningStep]:
        """获取会话的推理链"""
        async with self._lock:
            return self.reasoning_chains.get(session_id, [])
    
    async def get_reasoning_step(self, step_id: str) -> Optional[ReasoningStep]:
        """获取特定推理步骤"""
        async with self._lock:
            return self.reasoning_steps.get(step_id)
    
    async def record_task_decomposition(self, session_id: str, decomposition_data: Dict[str, Any]):
        """记录任务分解"""
        async with self._lock:
            self.task_decompositions[session_id] = {
                **decomposition_data,
                "timestamp": datetime.now(),
                "session_id": session_id
            }
            
            # 发布任务分解事件
            await self.publish_event(BlackboardEvent(
                event_type=EventType.SUBTASK_CREATED,
                agent_id="main_agent",
                session_id=session_id,
                data=decomposition_data
            ))
            
            logger.debug(f"📋 记录任务分解: {session_id}")
    
    async def get_task_decomposition(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取任务分解信息"""
        async with self._lock:
            return self.task_decompositions.get(session_id)
    
    async def create_inference_chain(self, session_id: str, agent_id: str, 
                                   chain_type: str, input_data: Dict[str, Any]) -> str:
        """创建推理链"""
        chain_id = f"chain_{uuid.uuid4().hex[:8]}"
        
        # 创建起始推理步骤
        initial_step = ReasoningStep(
            agent_id=agent_id,
            step_type="chain_start",
            description=f"开始{chain_type}推理链",
            input_data=input_data,
            confidence=1.0
        )
        
        await self.record_reasoning_step(initial_step)
        
        # 发布推理链创建事件
        await self.publish_event(BlackboardEvent(
            event_type=EventType.INFERENCE_CHAIN,
            agent_id=agent_id,
            session_id=session_id,
            data={
                "chain_id": chain_id,
                "chain_type": chain_type,
                "initial_step_id": initial_step.step_id
            }
        ))
        
        return chain_id

    async def create_task_request(self, task_request: TaskRequest) -> str:
        """创建任务请求"""
        async with self._lock:
            self.task_requests[task_request.task_id] = task_request
            
            # 添加到会话任务列表
            if task_request.session_id not in self.session_tasks:
                self.session_tasks[task_request.session_id] = []
            self.session_tasks[task_request.session_id].append(task_request.task_id)
            
            logger.info(f"📝 创建任务请求: {task_request.task_id} ({task_request.task_type})")
            
            # 发布任务创建事件
            await self.publish_event(BlackboardEvent(
                event_type=EventType.TASK_CREATED,
                agent_id="system",
                target_agent=task_request.assigned_agent,
                session_id=task_request.session_id,
                data={
                    "task_id": task_request.task_id,
                    "task_type": task_request.task_type,
                    "description": task_request.description,
                    "assigned_agent": task_request.assigned_agent,
                    "priority": task_request.priority
                }
            ))
            
            return task_request.task_id
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                output_data: Optional[Dict[str, Any]] = None,
                                error_message: Optional[str] = None,
                                progress: Optional[float] = None) -> bool:
        """更新任务状态"""
        async with self._lock:
            if task_id not in self.task_requests:
                logger.warning(f"⚠️ 任务不存在: {task_id}")
                return False
            
            task = self.task_requests[task_id]
            old_status = task.status
            task.status = status
            
            # 更新时间戳
            if status == TaskStatus.RUNNING and task.started_at is None:
                task.started_at = datetime.now()
            elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
            
            # 更新输出数据
            if output_data:
                task.output_data.update(output_data)
            
            # 更新错误信息
            if error_message:
                task.error_message = error_message
            
            # 更新进度
            if progress is not None:
                task.progress = max(0.0, min(1.0, progress))
            
            logger.info(f"🔄 任务状态更新: {task_id} {old_status.value} -> {status.value}")
            
            # 发布状态更新事件
            event_type = {
                TaskStatus.RUNNING: EventType.TASK_STARTED,
                TaskStatus.SUCCESS: EventType.TASK_COMPLETED,
                TaskStatus.FAILED: EventType.TASK_FAILED
            }.get(status, EventType.DATA_UPDATED)
            
            await self.publish_event(BlackboardEvent(
                event_type=event_type,
                agent_id=task.assigned_agent,
                session_id=task.session_id,
                data={
                    "task_id": task_id,
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "progress": task.progress,
                    "output_data": output_data,
                    "error_message": error_message
                }
            ))
            
            return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.task_requests:
            return None
        
        task = self.task_requests[task_id]
        
        # 计算执行时间
        execution_time = None
        if task.started_at:
            end_time = task.completed_at or datetime.now()
            execution_time = (end_time - task.started_at).total_seconds()
        
        return {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "task_type": task.task_type,
            "description": task.description,
            "assigned_agent": task.assigned_agent,
            "status": task.status.value,
            "priority": task.priority,
            "progress": task.progress,
            "dependencies": task.dependencies,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "execution_time_seconds": execution_time,
            "error_message": task.error_message,
            "input_data": task.input_data,
            "output_data": task.output_data
        }
    
    async def get_session_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有任务状态"""
        if session_id not in self.session_tasks:
            return []
        
        tasks = []
        for task_id in self.session_tasks[session_id]:
            task_status = await self.get_task_status(task_id)
            if task_status:
                tasks.append(task_status)
        
        return tasks
    
    async def get_tasks_by_status(self, status: TaskStatus, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """根据状态获取任务列表"""
        tasks = []
        
        for task_id, task in self.task_requests.items():
            if task.status == status:
                if session_id is None or task.session_id == session_id:
                    task_status = await self.get_task_status(task_id)
                    if task_status:
                        tasks.append(task_status)
        
        return tasks
    
    async def get_pending_tasks(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取待执行的任务"""
        tasks = []
        
        for task_id, task in self.task_requests.items():
            if task.status == TaskStatus.PENDING:
                if agent_id is None or task.assigned_agent == agent_id:
                    # 检查依赖是否满足
                    dependencies_met = True
                    for dep_task_id in task.dependencies:
                        if dep_task_id in self.task_requests:
                            dep_task = self.task_requests[dep_task_id]
                            if dep_task.status != TaskStatus.SUCCESS:
                                dependencies_met = False
                                break
                    
                    if dependencies_met:
                        task_status = await self.get_task_status(task_id)
                        if task_status:
                            tasks.append(task_status)
        
        # 按优先级排序
        tasks.sort(key=lambda x: x["priority"], reverse=True)
        return tasks
    
    async def get_task_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            "total": 0,
            "pending": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "cancelled": 0,
            "completion_rate": 0.0,
            "average_execution_time": 0.0
        }
        
        execution_times = []
        
        for task_id, task in self.task_requests.items():
            if session_id is None or task.session_id == session_id:
                stats["total"] += 1
                stats[task.status.value] += 1
                
                # 计算执行时间
                if task.started_at and task.completed_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    execution_times.append(execution_time)
        
        # 计算完成率
        if stats["total"] > 0:
            completed = stats["success"] + stats["failed"] + stats["cancelled"]
            stats["completion_rate"] = completed / stats["total"]
        
        # 计算平均执行时间
        if execution_times:
            stats["average_execution_time"] = sum(execution_times) / len(execution_times)
        
        return stats


# 全局黑板实例
_global_blackboard: Optional[Blackboard] = None


def get_blackboard() -> Blackboard:
    """获取全局黑板实例"""
    global _global_blackboard
    if _global_blackboard is None:
        _global_blackboard = Blackboard()
    return _global_blackboard


def create_blackboard() -> Blackboard:
    """创建新的黑板实例"""
    return Blackboard() 