"""
控制调度模块（黑板系统） - 科研多Agent系统的大脑
实现中心化黑板机制，负责事件管理、Agent调度和任务状态跟踪
"""
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

from .blackboard import Blackboard, BlackboardEvent, EventType
from .base_agent import BaseAgent, AgentConfig
from .llm_client import LLMClient


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ASSIGNED = "assigned" 
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ScheduleTask:
    """调度任务数据结构"""
    task_id: str
    task_type: str
    priority: TaskPriority
    event_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def is_ready(self) -> bool:
        """检查任务是否准备执行（依赖已满足）"""
        return self.status == TaskStatus.PENDING and len(self.dependencies) == 0
    
    @property
    def is_expired(self) -> bool:
        """检查任务是否已超时"""
        if self.started_at and self.status == TaskStatus.RUNNING:
            return datetime.now() - self.started_at > timedelta(seconds=self.timeout_seconds)
        return False
    
    @property
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED


@dataclass
class AgentCapability:
    """Agent能力描述"""
    agent_name: str
    agent_type: str
    supported_events: List[EventType]
    max_concurrent_tasks: int
    current_load: int = 0
    success_rate: float = 1.0
    avg_processing_time: float = 0.0
    last_active: Optional[datetime] = None
    is_available: bool = True
    specialized_skills: List[str] = field(default_factory=list)


class SystemScheduler:
    """
    系统调度器 - 控制调度模块核心
    
    功能目标:
    - 事件监听与发布：维护全局事件队列，监听新事件
    - Agent调度：根据事件类型和订阅关系调度Agent
    - 任务流状态管理：跟踪任务进展和状态转换
    - 数据共享：作为共享存储保存中间结果
    - 错误处理与扩展：容错和统一管理
    """

    def __init__(self, blackboard: Blackboard, llm_client: Optional[LLMClient] = None):
        self.blackboard = blackboard
        self.llm_client = llm_client
        self.logger = logging.getLogger("SystemScheduler")
        
        # 任务管理
        self.pending_tasks: Dict[str, ScheduleTask] = {}
        self.running_tasks: Dict[str, ScheduleTask] = {}
        self.completed_tasks: Dict[str, ScheduleTask] = {}
        self.failed_tasks: Dict[str, ScheduleTask] = {}
        
        # Agent管理
        self.registered_agents: Dict[str, BaseAgent] = {}
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.event_subscriptions: Dict[EventType, List[str]] = {}
        
        # 调度状态
        self.is_running = False
        self.scheduler_lock = asyncio.Lock()
        self.task_sequence = 0
        
        # 性能监控
        self.metrics = {
            "total_tasks_processed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_task_duration": 0.0,
            "agent_utilization": {},
            "system_uptime": datetime.now()
        }
        
        # 调度策略配置
        self.config = {
            "max_concurrent_tasks_per_agent": 8,  # 提高每个Agent的并发数
            "task_timeout_seconds": 120,  # 降低任务超时时间
            "health_check_interval": 15,  # 更频繁的健康检查
            "cleanup_interval": 1800,  # 更频繁的清理
            "max_retry_attempts": 2,  # 减少重试次数
            "load_balancing_enabled": True,
            "priority_boost_enabled": True,  # 启用优先级提升
            "adaptive_timeout_enabled": True,  # 启用自适应超时
            "batch_processing_enabled": True  # 启用批量处理
        }

    async def initialize(self):
        """初始化调度器"""
        self.logger.info("初始化系统调度器")
        
        try:
            # 初始化黑板
            await self.blackboard.initialize()
            
            # 创建核心Agent实例
            await self._create_agents()
            
            # 初始化所有Agent
            await self._initialize_agents()
            
            # 订阅系统级事件
            await self._subscribe_system_events()
            
            self.logger.info("系统调度器初始化完成")
            
        except Exception as e:
            self.logger.error(f"调度器初始化失败: {e}")
            raise

    async def _create_agents(self):
        """创建所有Agent实例"""
        from backend.agents.main_agent import MainAgent
        from backend.agents.critique_agent import CritiqueAgent
        from backend.agents.verification_agent import VerificationAgent
        from backend.agents.report_agent import ReportAgent
        from backend.agents.experiment_design_agent import ExperimentDesignAgent
        from backend.agents.evaluation_agent import EvaluationAgent
        from backend.agents.information_agent import InformationAgent
        from backend.agents.modeling_agent import ModelingAgent
        
        # 创建Agent实例
        agents_to_create = [
            ("MainAgent", MainAgent),
            ("CritiqueAgent", CritiqueAgent),
            ("VerificationAgent", VerificationAgent),
            ("ReportAgent", ReportAgent),
            ("ExperimentDesignAgent", ExperimentDesignAgent),
            ("EvaluationAgent", EvaluationAgent),
            ("InformationAgent", InformationAgent),
            ("ModelingAgent", ModelingAgent)
        ]
        
        for agent_name, agent_class in agents_to_create:
            try:
                agent = agent_class(self.blackboard, self.llm_client)
                self.registered_agents[agent_name] = agent
                
                # 注册Agent能力
                capability = AgentCapability(
                    agent_name=agent_name,
                    agent_type=agent.config.agent_type,
                    supported_events=agent.config.subscribed_events,
                    max_concurrent_tasks=agent.config.max_concurrent_tasks
                )
                self.agent_capabilities[agent_name] = capability
                
                # 建立事件订阅映射
                for event_type in agent.config.subscribed_events:
                    if event_type not in self.event_subscriptions:
                        self.event_subscriptions[event_type] = []
                    self.event_subscriptions[event_type].append(agent_name)
                
                self.logger.info(f"创建Agent: {agent_name}")
                
            except Exception as e:
                self.logger.error(f"创建Agent {agent_name} 失败: {e}")

    async def _initialize_agents(self):
        """初始化所有Agent"""
        for agent_name, agent in self.registered_agents.items():
            try:
                await agent.initialize()
                self.agent_capabilities[agent_name].is_available = True
                self.logger.info(f"Agent {agent_name} 初始化完成")
            except Exception as e:
                self.logger.error(f"Agent {agent_name} 初始化失败: {e}")
                self.agent_capabilities[agent_name].is_available = False

    async def _subscribe_system_events(self):
        """订阅系统级事件"""
        # 订阅任务相关事件
        await self.blackboard.subscribe(EventType.TASK_CREATED, self._handle_task_created)
        await self.blackboard.subscribe(EventType.TASK_COMPLETED, self._handle_task_completed)
        await self.blackboard.subscribe(EventType.CONFLICT_WARNING, self._handle_conflict_warning)
        await self.blackboard.subscribe(EventType.PRIORITY_INTERRUPT, self._handle_priority_interrupt)

    async def run(self):
        """启动调度器主循环"""
        if self.is_running:
            return
            
        self.is_running = True
        self.logger.info("启动系统调度器")
        
        try:
            # 启动各个调度循环
            await asyncio.gather(
                self._scheduler_loop(),
                self._monitor_loop(),
                self._cleanup_loop(),
                return_exceptions=True
            )
        except Exception as e:
            self.logger.error(f"调度器运行异常: {e}")
        finally:
            self.is_running = False

    async def _scheduler_loop(self):
        """主调度循环"""
        while self.is_running:
            try:
                async with self.scheduler_lock:
                    # 处理待处理任务
                    await self._process_pending_tasks()
                    
                    # 检查超时任务
                    await self._check_timeout_tasks()
                    
                    # 处理失败任务重试
                    await self._retry_failed_tasks()
                    
                await asyncio.sleep(1)  # 调度间隔
                
            except Exception as e:
                self.logger.error(f"调度循环异常: {e}")
                await asyncio.sleep(5)

    async def _process_pending_tasks(self):
        """处理待处理任务"""
        if not self.pending_tasks:
            return
            
        # 按优先级排序任务
        sorted_tasks = sorted(
            self.pending_tasks.values(),
            key=lambda t: (t.priority.value, t.created_at),
            reverse=True
        )
        
        for task in sorted_tasks:
            if not task.is_ready:
                continue
            
            # 找到合适的Agent
            suitable_agent = await self._find_suitable_agent(task)
            if suitable_agent:
                await self._assign_task(task, suitable_agent)

    async def _find_suitable_agent(self, task: ScheduleTask) -> Optional[str]:
        """
        根据任务类型和Agent能力找到最适合的Agent
        实现智能负载均衡和能力匹配
        """
        # 确定任务需要的事件类型
        task_event_type = self._determine_task_event_type(task)
        
        if task_event_type not in self.event_subscriptions:
            self.logger.warning(f"没有Agent订阅事件类型: {task_event_type}")
            return None
            
        # 获取可处理该事件的Agent列表
        candidate_agents = self.event_subscriptions[task_event_type]
        
        # 过滤可用的Agent
        available_agents = []
        for agent_name in candidate_agents:
            capability = self.agent_capabilities.get(agent_name)
            if (capability and capability.is_available and 
                capability.current_load < capability.max_concurrent_tasks):
                available_agents.append(agent_name)
        
        if not available_agents:
            return None

        # 负载均衡选择
        if self.config["load_balancing_enabled"]:
            # 选择负载最低的Agent
            best_agent = min(available_agents, key=lambda name: 
                           self.agent_capabilities[name].current_load)
        else:
            # 选择成功率最高的Agent
            best_agent = max(available_agents, key=lambda name:
                           self.agent_capabilities[name].success_rate)
            
        return best_agent

    def _determine_task_event_type(self, task: ScheduleTask) -> EventType:
        """根据任务类型确定对应的事件类型"""
        task_type_mapping = {
            "research_request": EventType.TASK_CREATED,
            "design_request": EventType.DESIGN_REQUEST,
            "solution_draft": EventType.SOLUTION_DRAFT_CREATED,
            "experiment_plan": EventType.EXPERIMENT_PLAN,
            "critique_feedback": EventType.CRITIQUE_FEEDBACK,
            "verification_report": EventType.VERIFICATION_REPORT,
            "information_update": EventType.INFORMATION_UPDATE,
            "model_result": EventType.MODEL_RESULT,
            "evaluation_result": EventType.EVALUATION_RESULT
        }
        
        return task_type_mapping.get(task.task_type, EventType.TASK_CREATED)

    async def _assign_task(self, task: ScheduleTask, agent_name: str):
        """分配任务给指定Agent"""
        try:
            # 更新任务状态
            task.assigned_agent = agent_name
            task.status = TaskStatus.ASSIGNED
            task.started_at = datetime.now()
            
            # 移动任务到运行队列
            self.running_tasks[task.task_id] = task
            del self.pending_tasks[task.task_id]
            
            # 更新Agent负载
            self.agent_capabilities[agent_name].current_load += 1
            self.agent_capabilities[agent_name].last_active = datetime.now()
            
            # 创建黑板事件
            event_type = self._determine_task_event_type(task)
            event = await self.blackboard.create_event(
                event_type=event_type,
                source_agent="SystemScheduler",
                data=task.event_data,
                target_agents=[agent_name],
                priority=task.priority.value
            )
            
            # 发布事件
            await self.blackboard.publish_event(event)
            
            self.logger.info(f"任务 {task.task_id} 已分配给 {agent_name}")
            
        except Exception as e:
            self.logger.error(f"任务分配失败: {e}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)

    async def _check_timeout_tasks(self):
        """检查并处理超时任务"""
        current_time = datetime.now()
        timeout_tasks = []
        
        for task in self.running_tasks.values():
            if task.is_expired:
                timeout_tasks.append(task)
        
        for task in timeout_tasks:
            self.logger.warning(f"任务超时: {task.task_id}")
            
            # 更新任务状态
            task.status = TaskStatus.TIMEOUT
            task.completed_at = current_time
            task.error_message = "任务执行超时"
            
            # 减少Agent负载
            if task.assigned_agent:
                capability = self.agent_capabilities.get(task.assigned_agent)
                if capability:
                    capability.current_load = max(0, capability.current_load - 1)
            
            # 移动到失败队列
            self.failed_tasks[task.task_id] = task
            del self.running_tasks[task.task_id]

    async def _retry_failed_tasks(self):
        """重试失败的任务"""
        retry_tasks = [task for task in self.failed_tasks.values() if task.can_retry]
        
        for task in retry_tasks:
            self.logger.info(f"重试任务: {task.task_id} (第{task.retry_count + 1}次)")
            
            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.assigned_agent = None
            task.started_at = None
            task.retry_count += 1
            task.error_message = None
            
            # 移回待处理队列
            self.pending_tasks[task.task_id] = task
            del self.failed_tasks[task.task_id]

    async def _monitor_loop(self):
        """监控循环 - 检查Agent健康状态和系统性能"""
        while self.is_running:
            try:
                # 更新系统指标
                await self._update_performance_metrics()
                
                # 检查Agent健康状态
                await self._check_agent_health()
                
                # 记录系统状态
                await self._log_system_status()
                
                await asyncio.sleep(self.config["health_check_interval"])
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")

    async def _update_performance_metrics(self):
        """更新性能指标"""
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        if total_tasks > 0:
            self.metrics["total_tasks_processed"] = total_tasks
            self.metrics["successful_tasks"] = len(self.completed_tasks)
            self.metrics["failed_tasks"] = len(self.failed_tasks)
            
            # 计算平均任务持续时间
            completed_durations = []
            for task in self.completed_tasks.values():
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    completed_durations.append(duration)
            
            if completed_durations:
                self.metrics["avg_task_duration"] = sum(completed_durations) / len(completed_durations)
        
        # 更新Agent利用率
        for agent_name, capability in self.agent_capabilities.items():
            utilization = capability.current_load / capability.max_concurrent_tasks
            self.metrics["agent_utilization"][agent_name] = utilization

    async def _check_agent_health(self):
        """检查Agent健康状态"""
        for agent_name, agent in self.registered_agents.items():
            try:
                status = agent.get_status()
                capability = self.agent_capabilities[agent_name]
                
                # 更新能力信息
                capability.success_rate = status["metrics"]["success_rate"]
                capability.avg_processing_time = status["metrics"]["avg_processing_time"]
                capability.is_available = status["initialized"] and status["enabled"]
                
            except Exception as e:
                self.logger.warning(f"检查Agent {agent_name} 健康状态失败: {e}")
                self.agent_capabilities[agent_name].is_available = False

    async def _log_system_status(self):
        """记录系统状态"""
        status = {
            "pending_tasks": len(self.pending_tasks),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "active_agents": sum(1 for cap in self.agent_capabilities.values() if cap.is_available),
            "total_agents": len(self.agent_capabilities)
        }
        
        self.logger.debug(f"系统状态: {status}")

    async def _cleanup_loop(self):
        """清理循环 - 定期清理过期数据"""
        while self.is_running:
            try:
                current_time = datetime.now()
                cleanup_threshold = current_time - timedelta(hours=24)
                
                # 清理旧的已完成任务
                old_completed = [
                    task_id for task_id, task in self.completed_tasks.items()
                    if task.completed_at and task.completed_at < cleanup_threshold
                ]
                
                for task_id in old_completed:
                    del self.completed_tasks[task_id]
                
                # 清理旧的失败任务
                old_failed = [
                    task_id for task_id, task in self.failed_tasks.items()
                    if task.completed_at and task.completed_at < cleanup_threshold
                ]
                
                for task_id in old_failed:
                    del self.failed_tasks[task_id]
                
                if old_completed or old_failed:
                    self.logger.info(f"清理了 {len(old_completed)} 个完成任务, {len(old_failed)} 个失败任务")
                
                await asyncio.sleep(self.config["cleanup_interval"])
                
            except Exception as e:
                self.logger.error(f"清理循环异常: {e}")

    def _safe_convert_priority(self, priority_value: Any) -> TaskPriority:
        """安全转换优先级值到TaskPriority枚举"""
        try:
            if isinstance(priority_value, TaskPriority):
                return priority_value
            elif isinstance(priority_value, int):
                # 将int值映射到TaskPriority枚举
                if priority_value <= 0:
                    return TaskPriority.LOW
                elif priority_value == 1:
                    return TaskPriority.NORMAL
                elif priority_value == 2:
                    return TaskPriority.HIGH
                elif priority_value == 3:
                    return TaskPriority.URGENT
                else:  # priority_value >= 4 或其他大值
                    return TaskPriority.CRITICAL
            else:
                return TaskPriority.NORMAL
        except:
            return TaskPriority.NORMAL

    async def _handle_task_created(self, event: BlackboardEvent):
        """处理任务创建事件"""
        try:
            data = event.data
            
            # 创建调度任务
            task = ScheduleTask(
                task_id=data.get("task_id", f"task_{uuid.uuid4().hex[:8]}"),
                task_type=data.get("task_type", "general"),
                priority=self._safe_convert_priority(data.get("priority", 1)),
                event_data=data,
                dependencies=data.get("dependencies", []),
                max_retries=data.get("max_retries", 3),
                timeout_seconds=data.get("timeout_seconds", 300)
            )
            
            # 添加到待处理队列
            self.pending_tasks[task.task_id] = task
            
            self.logger.info(f"新任务创建: {task.task_id} (类型: {task.task_type}, 优先级: {task.priority.value})")
            
        except Exception as e:
            self.logger.error(f"处理任务创建事件失败: {e}")

    async def _handle_task_completed(self, event: BlackboardEvent):
        """处理任务完成事件"""
        try:
            data = event.data
            task_id = data.get("task_id") or data.get("original_task_id")
        
            if not task_id:
                return
                
            # 查找运行中的任务
            task = self.running_tasks.get(task_id)
            if not task:
                return
                
            # 更新任务状态
            if data.get("status") == "failed":
                task.status = TaskStatus.FAILED
                task.error_message = data.get("error_message", "未知错误")
                self.failed_tasks[task_id] = task
            else:
                task.status = TaskStatus.COMPLETED
                self.completed_tasks[task_id] = task
            
            task.completed_at = datetime.now()
            
            # 减少Agent负载
            if task.assigned_agent:
                capability = self.agent_capabilities.get(task.assigned_agent)
                if capability:
                    capability.current_load = max(0, capability.current_load - 1)
            
            # 从运行队列移除
            del self.running_tasks[task_id]
            
            # 检查依赖任务
            await self._resolve_task_dependencies(task_id)
            
            self.logger.info(f"任务完成: {task_id} (状态: {task.status.value})")
            
        except Exception as e:
            self.logger.error(f"处理任务完成事件失败: {e}")

    async def _resolve_task_dependencies(self, completed_task_id: str):
        """解决任务依赖关系"""
        for task in self.pending_tasks.values():
            if completed_task_id in task.dependencies:
                task.dependencies.remove(completed_task_id)
                self.logger.debug(f"任务 {task.task_id} 依赖 {completed_task_id} 已解决")

    async def _handle_conflict_warning(self, event: BlackboardEvent):
        """处理冲突警告事件"""
        self.logger.warning(f"收到冲突警告: {event.data}")
        
        # 可以实现冲突解决策略
        # 例如暂停相关任务、调用批判Agent等
        
    async def _handle_priority_interrupt(self, event: BlackboardEvent):
        """处理高优先级中断事件"""
        self.logger.info(f"收到高优先级中断: {event.data}")
        
        # 创建高优先级任务
        interrupt_task = ScheduleTask(
            task_id=str(uuid.uuid4()),
            task_type=event.data.get("task_type", "priority_task"),
            priority=TaskPriority.CRITICAL,
            event_data=event.data
        )
        
        self.pending_tasks[interrupt_task.task_id] = interrupt_task

    async def submit_task(self, task_type: str, data: Dict[str, Any], priority: int = 1) -> str:
        """提交任务到调度器"""
        task_id = str(uuid.uuid4())
        
        # 发布任务创建事件
        await self.blackboard.create_event(
            EventType.TASK_CREATED,
            "SystemScheduler",
            {
                "task_id": task_id,
                "task_type": task_type,
                "priority": priority,
                **data
            }
        )
        
        return task_id

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "scheduler_running": self.is_running,
            "task_queues": {
                "pending": len(self.pending_tasks),
                "running": len(self.running_tasks),
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks)
            },
            "agents": {
                name: {
                    "available": cap.is_available,
                    "current_load": cap.current_load,
                    "max_load": cap.max_concurrent_tasks,
                    "success_rate": cap.success_rate
                }
                for name, cap in self.agent_capabilities.items()
            },
            "metrics": self.metrics,
            "uptime": (datetime.now() - self.metrics["system_uptime"]).total_seconds()
        }

    async def shutdown(self):
        """关闭调度器"""
        self.logger.info("开始关闭系统调度器")
        
        self.is_running = False
        
        # 等待所有运行中的任务完成或超时
        if self.running_tasks:
            self.logger.info(f"等待 {len(self.running_tasks)} 个任务完成...")
            timeout = 30  # 30秒超时
            start_time = datetime.now()
            
            while self.running_tasks and (datetime.now() - start_time).total_seconds() < timeout:
                await asyncio.sleep(1)
        
        # 关闭所有Agent
        for agent_name, agent in self.registered_agents.items():
            try:
                await agent.shutdown()
                self.logger.info(f"Agent {agent_name} 已关闭")
            except Exception as e:
                self.logger.error(f"关闭Agent {agent_name} 失败: {e}")
        
        self.logger.info("系统调度器已关闭")

    async def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            "total_tasks": len(self.pending_tasks) + len(self.running_tasks) + len(self.completed_tasks),
            "pending_tasks": len(self.pending_tasks),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "agent_capabilities": {
                name: {
                    "current_load": cap.current_load,
                    "success_rate": cap.success_rate,
                    "is_available": cap.is_available
                }
                for name, cap in self.agent_capabilities.items()
            },
            "is_running": self.is_running
        }
