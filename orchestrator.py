#!/usr/bin/env python3
"""
系统编排调度器 - 科研创意多Agent系统
负责系统级别的任务调度、负载均衡和资源管理
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime, timedelta

from backend.core.blackboard import Blackboard, EventType, BlackboardEvent
from backend.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TaskRequest:
    """任务请求数据结构"""
    task_id: str
    user_id: str
    query: str
    priority: TaskPriority
    required_agents: List[str]
    max_duration: int = 300  # 最大执行时间(秒)
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class SystemMetrics:
    """系统指标数据结构"""
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    agent_utilization: Dict[str, float] = None
    avg_response_time: float = 0.0
    system_load: float = 0.0
    
    def __post_init__(self):
        if self.agent_utilization is None:
            self.agent_utilization = {}

class SystemOrchestrator:
    """系统编排调度器"""
    
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.task_queue: List[TaskRequest] = []
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.completed_tasks: Dict[str, TaskRequest] = {}
        self.failed_tasks: Dict[str, TaskRequest] = {}
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.metrics = SystemMetrics()
        self.is_running = False
        self.max_concurrent_tasks = 10  # 最大并发任务数
        
        # 性能监控
        self.performance_history: List[Dict] = []
        self.last_metrics_update = time.time()
        
        logger.info("🎯 系统编排调度器初始化完成")
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent到调度器"""
        self.agent_registry[agent.agent_id] = agent
        logger.info(f"✅ Agent {agent.agent_id} 已注册到调度器")
    
    async def start(self):
        """启动编排调度器"""
        self.is_running = True
        logger.info("🚀 系统编排调度器启动")
        
        # 启动监控任务
        asyncio.create_task(self._monitor_system())
        asyncio.create_task(self._process_task_queue())
        asyncio.create_task(self._cleanup_completed_tasks())
    
    async def stop(self):
        """停止编排调度器"""
        self.is_running = False
        logger.info("🛑 系统编排调度器停止")
    
    async def submit_task(self, task: TaskRequest) -> str:
        """提交任务到调度器"""
        # 验证任务
        if not await self._validate_task(task):
            raise ValueError(f"任务验证失败: {task.task_id}")
        
        # 添加到队列
        self.task_queue.append(task)
        
        # 按优先级排序
        self.task_queue.sort(key=lambda x: x.priority.value, reverse=True)
        
        logger.info(f"📋 任务 {task.task_id} 已提交，优先级: {task.priority.name}")
        
        return task.task_id
    
    async def _validate_task(self, task: TaskRequest) -> bool:
        """验证任务请求"""
        if not task.task_id or not task.query:
            return False
        
        # 检查所需Agent是否可用
        for agent_id in task.required_agents:
            if agent_id not in self.agent_registry:
                logger.warning(f"❌ Agent {agent_id} 未注册")
                return False
        
        return True
    
    async def _process_task_queue(self):
        """处理任务队列"""
        while self.is_running:
            try:
                # 检查并发限制
                if len(self.active_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue
                
                # 获取下一个任务
                if not self.task_queue:
                    await asyncio.sleep(0.5)
                    continue
                
                task = self.task_queue.pop(0)
                
                # 检查任务超时
                if self._is_task_expired(task):
                    self.failed_tasks[task.task_id] = task
                    logger.warning(f"⏰ 任务 {task.task_id} 已超时")
                    continue
                
                # 启动任务
                await self._execute_task(task)
                
            except Exception as e:
                logger.error(f"❌ 任务队列处理异常: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: TaskRequest):
        """执行任务"""
        task.started_at = datetime.now()
        self.active_tasks[task.task_id] = task
        
        logger.info(f"🚀 开始执行任务 {task.task_id}")
        
        try:
            # 创建任务事件
            event = BlackboardEvent(
                event_type=EventType.TASK_CREATED,
                agent_id="orchestrator",
                target_agent="main_agent",
                data={
                    "task_id": task.task_id,
                    "user_id": task.user_id,
                    "query": task.query,
                    "priority": task.priority.name,
                    "required_agents": task.required_agents
                }
            )
            
            # 发布事件到黑板
            await self.blackboard.publish_event(event)
            
            # 创建任务监控协程
            asyncio.create_task(self._monitor_task(task))
            
        except Exception as e:
            logger.error(f"❌ 任务执行失败 {task.task_id}: {e}")
            self._mark_task_failed(task, str(e))
    
    async def _monitor_task(self, task: TaskRequest):
        """监控任务执行"""
        start_time = time.time()
        
        while task.task_id in self.active_tasks:
            await asyncio.sleep(1)
            
            # 检查超时
            if time.time() - start_time > task.max_duration:
                logger.warning(f"⏰ 任务 {task.task_id} 执行超时")
                self._mark_task_failed(task, "执行超时")
                break
    
    def _mark_task_completed(self, task: TaskRequest):
        """标记任务完成"""
        task.completed_at = datetime.now()
        self.completed_tasks[task.task_id] = task
        
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        logger.info(f"✅ 任务 {task.task_id} 完成")
    
    def _mark_task_failed(self, task: TaskRequest, error: str):
        """标记任务失败"""
        task.completed_at = datetime.now()
        self.failed_tasks[task.task_id] = task
        
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        logger.error(f"❌ 任务 {task.task_id} 失败: {error}")
    
    def _is_task_expired(self, task: TaskRequest) -> bool:
        """检查任务是否过期"""
        if not task.created_at:
            return False
        
        elapsed = datetime.now() - task.created_at
        return elapsed > timedelta(seconds=task.max_duration)
    
    async def _monitor_system(self):
        """系统监控"""
        while self.is_running:
            try:
                await self._update_metrics()
                await asyncio.sleep(5)  # 每5秒更新一次
            except Exception as e:
                logger.error(f"❌ 系统监控异常: {e}")
                await asyncio.sleep(10)
    
    async def _update_metrics(self):
        """更新系统指标"""
        current_time = time.time()
        
        # 更新基础指标
        self.metrics.active_tasks = len(self.active_tasks)
        self.metrics.completed_tasks = len(self.completed_tasks)
        self.metrics.failed_tasks = len(self.failed_tasks)
        
        # 计算Agent利用率
        for agent_id, agent in self.agent_registry.items():
            # 这里可以添加Agent的性能指标计算
            self.metrics.agent_utilization[agent_id] = 0.0
        
        # 计算系统负载
        total_tasks = self.metrics.active_tasks + self.metrics.completed_tasks + self.metrics.failed_tasks
        if total_tasks > 0:
            self.metrics.system_load = self.metrics.active_tasks / self.max_concurrent_tasks
        
        # 记录性能历史
        self.performance_history.append({
            "timestamp": current_time,
            "active_tasks": self.metrics.active_tasks,
            "system_load": self.metrics.system_load,
            "completed_tasks": self.metrics.completed_tasks,
            "failed_tasks": self.metrics.failed_tasks
        })
        
        # 保持历史记录在合理范围内
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]
    
    async def _cleanup_completed_tasks(self):
        """清理完成的任务"""
        while self.is_running:
            try:
                current_time = datetime.now()
                cleanup_threshold = current_time - timedelta(hours=1)  # 1小时后清理
                
                # 清理完成的任务
                to_remove = []
                for task_id, task in self.completed_tasks.items():
                    if task.completed_at and task.completed_at < cleanup_threshold:
                        to_remove.append(task_id)
                
                for task_id in to_remove:
                    del self.completed_tasks[task_id]
                
                # 清理失败的任务
                to_remove = []
                for task_id, task in self.failed_tasks.items():
                    if task.completed_at and task.completed_at < cleanup_threshold:
                        to_remove.append(task_id)
                
                for task_id in to_remove:
                    del self.failed_tasks[task_id]
                
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except Exception as e:
                logger.error(f"❌ 任务清理异常: {e}")
                await asyncio.sleep(60)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "orchestrator_status": "running" if self.is_running else "stopped",
            "metrics": {
                "active_tasks": self.metrics.active_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "system_load": self.metrics.system_load,
                "agent_utilization": self.metrics.agent_utilization
            },
            "task_queue_length": len(self.task_queue),
            "registered_agents": list(self.agent_registry.keys()),
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 检查活动任务
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": "active",
                "priority": task.priority.name,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "duration": (datetime.now() - task.started_at).total_seconds() if task.started_at else 0
            }
        
        # 检查完成任务
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": "completed",
                "priority": task.priority.name,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "duration": (task.completed_at - task.started_at).total_seconds() if task.started_at and task.completed_at else 0
            }
        
        # 检查失败任务
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return {
                "task_id": task.task_id,
                "status": "failed",
                "priority": task.priority.name,
                "failed_at": task.completed_at.isoformat() if task.completed_at else None
            }
        
        # 检查队列中的任务
        for task in self.task_queue:
            if task.task_id == task_id:
                return {
                    "task_id": task.task_id,
                    "status": "queued",
                    "priority": task.priority.name,
                    "position": self.task_queue.index(task)
                }
        
        return None

# 全局调度器实例
_orchestrator_instance = None

def get_orchestrator() -> SystemOrchestrator:
    """获取全局调度器实例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        raise RuntimeError("调度器未初始化")
    return _orchestrator_instance

def initialize_orchestrator(blackboard: Blackboard) -> SystemOrchestrator:
    """初始化全局调度器"""
    global _orchestrator_instance
    _orchestrator_instance = SystemOrchestrator(blackboard)
    return _orchestrator_instance 