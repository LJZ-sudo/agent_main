#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent管理器 - 负责管理所有Agent的生命周期和协调
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Type
from loguru import logger

from .blackboard import Blackboard, BlackboardEvent, EventType, get_blackboard
from .base_agent import BaseAgent, InformationAgent, VerificationAgent, CritiqueAgent, ReportAgent
from ..agents.main_agent import MainAgent


class AgentManager:
    """Agent管理器 - 管理所有Agent的生命周期"""
    
    def __init__(self, blackboard: Optional[Blackboard] = None):
        self.blackboard = blackboard or get_blackboard()
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_types: Dict[str, Type[BaseAgent]] = {
            "main": MainAgent,
            "information": InformationAgent,
            "verification": VerificationAgent,
            "critique": CritiqueAgent,
            "report": ReportAgent
        }
        self.running = False
        self.task_queue = asyncio.Queue()
        self.max_concurrent_tasks = 10
        self.task_semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
    async def initialize(self):
        """初始化Agent管理器"""
        try:
            logger.info("🚀 开始初始化Agent管理器...")
            
            # 创建所有Agent实例
            await self._create_agents()
            
            # 初始化所有Agent
            await self._initialize_agents()
            
            # 设置事件监听
            await self._setup_event_listeners()
            
            self.running = True
            logger.info("✅ Agent管理器初始化完成")
            
        except Exception as e:
            logger.error(f"❌ Agent管理器初始化失败: {e}")
            raise
    
    async def _create_agents(self):
        """创建Agent实例"""
        logger.info("📦 创建Agent实例...")
        
        try:
            # 创建主Agent
            self.agents["main"] = MainAgent(self.blackboard)
            
            # 创建功能Agent
            self.agents["information"] = InformationAgent(self.blackboard)
            self.agents["verification"] = VerificationAgent(self.blackboard)
            self.agents["critique"] = CritiqueAgent(self.blackboard)
            self.agents["report"] = ReportAgent(self.blackboard)
            
            logger.info(f"📦 成功创建 {len(self.agents)} 个Agent实例")
            
        except Exception as e:
            logger.error(f"❌ 创建Agent实例失败: {e}")
            raise
    
    async def _initialize_agents(self):
        """初始化所有Agent"""
        logger.info("🔧 初始化所有Agent...")
        
        initialization_results = []
        for agent_id, agent in self.agents.items():
            try:
                result = await agent.initialize()
                initialization_results.append((agent_id, result))
                logger.info(f"✅ Agent {agent_id} 初始化{'成功' if result else '失败'}")
            except Exception as e:
                logger.error(f"❌ Agent {agent_id} 初始化异常: {e}")
                initialization_results.append((agent_id, False))
        
        successful_count = sum(1 for _, success in initialization_results if success)
        logger.info(f"🎯 Agent初始化完成: {successful_count}/{len(self.agents)} 成功")
    
    async def _setup_event_listeners(self):
        """设置事件监听器"""
        logger.info("👂 设置事件监听器...")
        
        # 监听任务相关事件
        await self.blackboard.subscribe(EventType.TASK_STARTED, self._handle_task_started)
        await self.blackboard.subscribe(EventType.TASK_ASSIGNED, self._handle_task_assigned)
        await self.blackboard.subscribe(EventType.AGENT_REQUEST, self._handle_agent_request)
        
        logger.info("👂 事件监听器设置完成")
    
    async def _handle_task_started(self, event: BlackboardEvent):
        """处理任务开始事件"""
        logger.debug(f"📋 处理任务开始事件: {event.event_id}")
        
        # 更新系统状态
        await self.blackboard.store_data(
            "system_status",
            {
                "status": "processing",
                "current_session": event.data.get("session_id"),
                "last_activity": datetime.now().isoformat()
            },
            "system"
        )
    
    async def _handle_task_assigned(self, event: BlackboardEvent):
        """处理任务分配事件"""
        target_agent = event.target_agent
        task_data = event.data
        
        logger.info(f"📤 分配任务给 {target_agent}: {task_data.get('task_type', 'unknown')}")
        
        # 将任务添加到队列
        await self.task_queue.put({
            "event": event,
            "target_agent": target_agent,
            "task_data": task_data
        })
    
    async def _handle_agent_request(self, event: BlackboardEvent):
        """处理Agent请求事件"""
        target_agent = event.target_agent
        request_data = event.data
        
        logger.debug(f"📨 Agent请求: {event.agent_id} -> {target_agent}")
        
        # 将请求添加到队列
        await self.task_queue.put({
            "event": event,
            "target_agent": target_agent,
            "task_data": request_data,
            "type": "request"
        })
    
    async def start_processing(self):
        """开始处理任务队列"""
        if not self.running:
            await self.initialize()
        
        logger.info("🔄 开始处理任务队列...")
        
        # 启动多个工作协程
        workers = []
        for i in range(min(5, self.max_concurrent_tasks)):
            worker = asyncio.create_task(self._task_worker(f"worker-{i}"))
            workers.append(worker)
        
        try:
            await asyncio.gather(*workers)
        except Exception as e:
            logger.error(f"❌ 任务处理异常: {e}")
        finally:
            logger.info("🛑 任务处理已停止")
    
    async def _task_worker(self, worker_name: str):
        """任务工作协程"""
        logger.debug(f"👷 启动任务工作者: {worker_name}")
        
        while self.running:
            try:
                # 从队列获取任务（带超时）
                try:
                    task_item = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 处理任务
                async with self.task_semaphore:
                    await self._process_task_item(task_item, worker_name)
                
            except Exception as e:
                logger.error(f"❌ 工作者 {worker_name} 处理任务失败: {e}")
                await asyncio.sleep(1)
    
    async def _process_task_item(self, task_item: Dict[str, Any], worker_name: str):
        """处理单个任务项"""
        event = task_item["event"]
        target_agent = task_item["target_agent"]
        task_data = task_item["task_data"]
        task_type = task_item.get("type", "task")
        
        logger.debug(f"🔧 {worker_name} 处理 {task_type}: {target_agent}")
        
        try:
            # 获取目标Agent
            agent = await self._get_agent_by_name(target_agent)
            if not agent:
                logger.error(f"❌ 未找到目标Agent: {target_agent}")
                return
            
            # 执行任务
            if task_type == "request":
                await self._handle_agent_request_execution(agent, event, task_data)
            else:
                await self._handle_task_execution(agent, event, task_data)
            
        except Exception as e:
            logger.error(f"❌ 任务执行失败: {e}")
            
            # 发布错误事件
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.ERROR_OCCURRED,
                agent_id="agent_manager",
                data={
                    "error": str(e),
                    "original_event_id": event.event_id,
                    "target_agent": target_agent,
                    "timestamp": datetime.now().isoformat()
                }
            ))
    
    async def _get_agent_by_name(self, agent_name: str) -> Optional[BaseAgent]:
        """根据名称获取Agent"""
        # 直接匹配
        if agent_name in self.agents:
            return self.agents[agent_name]
        
        # 模糊匹配
        for agent_id, agent in self.agents.items():
            if (agent_name.lower() in agent_id.lower() or
                agent_name.lower() in agent.agent_type.lower()):
                return agent
        
        # 特殊映射
        agent_mapping = {
            "information_enhanced": "information",
            "enhanced_information": "information",
            "info": "information",
            "verify": "verification",
            "critic": "critique",
            "reporting": "report"
        }
        
        mapped_name = agent_mapping.get(agent_name.lower())
        if mapped_name and mapped_name in self.agents:
            return self.agents[mapped_name]
        
        return None
    
    async def _handle_task_execution(self, agent: BaseAgent, event: BlackboardEvent, 
                                   task_data: Dict[str, Any]):
        """处理常规任务执行"""
        try:
            # 执行任务
            result = await agent.process_task(task_data)
            
            # 发布完成事件
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.TASK_COMPLETED,
                agent_id=agent.agent_id,
                data={
                    "original_event_id": event.event_id,
                    "task_result": result,
                    "session_id": task_data.get("session_id"),
                    "timestamp": datetime.now().isoformat()
                }
            ))
            
        except Exception as e:
            # 发布失败事件
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.TASK_FAILED,
                agent_id=agent.agent_id,
                data={
                    "original_event_id": event.event_id,
                    "error": str(e),
                    "session_id": task_data.get("session_id"),
                    "timestamp": datetime.now().isoformat()
                }
            ))
    
    async def _handle_agent_request_execution(self, agent: BaseAgent, event: BlackboardEvent,
                                            request_data: Dict[str, Any]):
        """处理Agent请求执行"""
        action = request_data.get("action", "")
        parameters = request_data.get("parameters", {})
        request_id = request_data.get("request_id", "")
        
        try:
            # 根据action执行相应方法
            if hasattr(agent, action):
                method = getattr(agent, action)
                if callable(method):
                    if asyncio.iscoroutinefunction(method):
                        result = await method(**parameters)
                    else:
                        result = method(**parameters)
                else:
                    result = {"error": f"属性 {action} 不是可调用方法"}
            else:
                result = {"error": f"Agent {agent.agent_id} 不支持操作: {action}"}
            
            # 发布响应
            await self.blackboard.respond_to_request(
                request_id=request_id,
                response_data=result,
                agent_id=agent.agent_id,
                success=True
            )
            
        except Exception as e:
            # 发布错误响应
            await self.blackboard.respond_to_request(
                request_id=request_id,
                response_data={"error": str(e)},
                agent_id=agent.agent_id,
                success=False
            )
    
    async def process_research_request(self, user_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """处理研究请求"""
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🔬 开始处理研究请求: {session_id}")
        
        try:
            # 获取主Agent
            main_agent = self.agents.get("main")
            if not main_agent:
                raise Exception("主Agent未初始化")
            
            # 调用主Agent处理请求
            result = await main_agent.process_research_request(user_input, session_id)
            
            logger.info(f"✅ 研究请求处理完成: {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 研究请求处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        try:
            main_agent = self.agents.get("main")
            if main_agent and hasattr(main_agent, 'get_session_status'):
                return await main_agent.get_session_status(session_id)
            else:
                return {
                    "status": "error",
                    "message": "主Agent不可用"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 获取黑板状态
            blackboard_status = await self.blackboard.get_system_status()
            
            # 获取所有Agent状态
            agent_statuses = {}
            for agent_id, agent in self.agents.items():
                try:
                    agent_statuses[agent_id] = agent.get_status()
                except Exception as e:
                    agent_statuses[agent_id] = {"error": str(e)}
            
            return {
                "system_status": "operational" if self.running else "stopped",
                "agent_manager_running": self.running,
                "total_agents": len(self.agents),
                "active_agents": len([a for a in agent_statuses.values() 
                                    if a.get("status") == "ready"]),
                "blackboard_status": blackboard_status,
                "agent_statuses": agent_statuses,
                "task_queue_size": self.task_queue.qsize(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查黑板健康
            blackboard_health = await self.blackboard.health_check()
            
            # 检查Agent健康
            agent_health = {}
            for agent_id, agent in self.agents.items():
                try:
                    if hasattr(agent, 'health_check'):
                        agent_health[agent_id] = await agent.health_check()
                    else:
                        agent_health[agent_id] = {
                            "status": "unknown",
                            "message": "健康检查不支持"
                        }
                except Exception as e:
                    agent_health[agent_id] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # 计算整体健康状态
            healthy_agents = len([h for h in agent_health.values() 
                                if h.get("overall_health") == "healthy"])
            total_agents = len(agent_health)
            
            overall_health = "healthy"
            if blackboard_health.get("status") != "healthy":
                overall_health = "degraded"
            elif healthy_agents < total_agents * 0.8:  # 少于80%的Agent健康
                overall_health = "degraded"
            elif healthy_agents == 0:
                overall_health = "unhealthy"
            
            return {
                "overall_health": overall_health,
                "manager_status": "running" if self.running else "stopped",
                "blackboard_health": blackboard_health,
                "agent_health": agent_health,
                "healthy_agents": f"{healthy_agents}/{total_agents}",
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "overall_health": "error",
                "error": str(e),
                "check_time": datetime.now().isoformat()
            }
    
    async def shutdown(self):
        """关闭Agent管理器"""
        logger.info("🛑 开始关闭Agent管理器...")
        
        self.running = False
        
        # 等待任务队列清空
        while not self.task_queue.empty():
            await asyncio.sleep(0.1)
        
        # 关闭所有Agent
        for agent_id, agent in self.agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    await agent.shutdown()
                logger.info(f"✅ Agent {agent_id} 已关闭")
            except Exception as e:
                logger.error(f"❌ 关闭Agent {agent_id} 失败: {e}")
        
        logger.info("✅ Agent管理器已关闭")


# 全局Agent管理器实例
_global_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """获取全局Agent管理器实例"""
    global _global_agent_manager
    if _global_agent_manager is None:
        _global_agent_manager = AgentManager()
    return _global_agent_manager


def create_agent_manager(blackboard: Optional[Blackboard] = None) -> AgentManager:
    """创建新的Agent管理器实例"""
    return AgentManager(blackboard) 