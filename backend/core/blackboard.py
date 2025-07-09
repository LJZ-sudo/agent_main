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
from loguru import logger


class EventType(Enum):
    """事件类型枚举"""
    # 基础事件
    TASK_STARTED = "task_started"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # Agent间通信
    AGENT_MESSAGE = "agent_message"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    
    # 数据更新
    DATA_UPDATED = "data_updated"
    INFORMATION_UPDATE = "information_update"
    MODEL_RESULT = "model_result"
    
    # 质量控制
    VERIFICATION_REPORT = "verification_report"
    CRITIQUE_FEEDBACK = "critique_feedback"
    QUALITY_CHECK = "quality_check"
    
    # 系统事件
    SYSTEM_STATUS = "system_status"
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"


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


class Blackboard:
    """黑板系统 - 提供Agent间的通信和数据共享"""
    
    def __init__(self):
        self.events: List[BlackboardEvent] = []
        self.shared_data: Dict[str, Any] = {}
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[BlackboardEvent] = []
        self.max_history = 1000
        self._lock = asyncio.Lock()
        
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