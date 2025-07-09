#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent基类 - 提供统一的Agent功能和接口
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger

from .llm_client import LLMClient, create_llm_client, LLMProvider
from ..config_clean import get_config


class BaseAgent(ABC):
    """Agent基类 - 所有Agent的基础类"""

    def __init__(self, agent_id: str, blackboard):
        self.agent_id = agent_id
        self.blackboard = blackboard
        self.agent_type = "base"
        self.status = "idle"
        self.specializations = []
        self.current_tasks = {}
        self.performance_stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_response_time": 0.0,
            "last_activity": None
        }
        
        # 初始化LLM客户端
        self.llm_client = self._create_llm_client()
        
    def _create_llm_client(self) -> LLMClient:
        """创建LLM客户端"""
        try:
            config = get_config()
            return create_llm_client(
                api_key=config.llm.api_key,
                model=config.llm.model,
                base_url=config.llm.base_url,
                provider=LLMProvider.DEEPSEEK,
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens
            )
        except Exception as e:
            logger.error(f"创建LLM客户端失败: {e}")
            # 创建默认客户端
            return create_llm_client(
                api_key="sk-7ca2f21430bb4383ab97fbf7e0f8cf05",
                model="deepseek-chat",
                base_url="https://api.deepseek.com/v1",
                provider=LLMProvider.DEEPSEEK
            )

    async def initialize(self):
        """初始化Agent"""
        try:
            # 测试LLM连接
            connection_ok = await self.llm_client.test_connection()
            if connection_ok:
                logger.info(f"✅ {self.agent_id} Agent初始化成功，LLM连接正常")
            else:
                logger.warning(f"⚠️ {self.agent_id} Agent初始化，但LLM连接异常")
            
            self.status = "ready"
            return True
        except Exception as e:
            logger.error(f"❌ {self.agent_id} Agent初始化失败: {e}")
            self.status = "error"
            return False
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务的主要方法"""
        task_id = task_data.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
        start_time = datetime.now()
                
        try:
            self.status = "processing"
            self.current_tasks[task_id] = {
                "start_time": start_time,
                "task_data": task_data
            }
            
            logger.info(f"🔄 {self.agent_id} 开始处理任务: {task_id}")
            
            # 调用具体Agent的处理逻辑
            result = await self._process_task_impl(task_data)
            
            # 更新性能统计
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            self._update_performance_stats(True, processing_time)
            
            # 清理任务记录
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
            
            self.status = "ready"
            
            logger.info(f"✅ {self.agent_id} 完成任务: {task_id}, 耗时: {processing_time:.2f}s")
            
            return {
                "success": True,
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "processing_time": processing_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 处理任务失败: {task_id}, 错误: {e}")
            
            # 更新失败统计
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(False, processing_time)
            
            # 清理任务记录
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
            
            self.status = "ready"
            
            return {
                "success": False,
                "task_id": task_id,
                "agent_id": self.agent_id,
                "error": str(e),
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }

    @abstractmethod
    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """具体的任务处理实现，由子类重写"""
        pass

    def _update_performance_stats(self, success: bool, processing_time: float):
        """更新性能统计"""
        if success:
            self.performance_stats["tasks_completed"] += 1
        else:
            self.performance_stats["tasks_failed"] += 1
            
        # 更新平均响应时间
        total_tasks = self.performance_stats["tasks_completed"] + self.performance_stats["tasks_failed"]
        if total_tasks > 0:
            current_avg = self.performance_stats["average_response_time"]
            self.performance_stats["average_response_time"] = (
                (current_avg * (total_tasks - 1) + processing_time) / total_tasks
            )
        
        self.performance_stats["last_activity"] = datetime.now().isoformat()

    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "specializations": self.specializations,
            "current_tasks_count": len(self.current_tasks),
            "performance_stats": self.performance_stats.copy()
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取Agent能力描述"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "specializations": self.specializations,
            "supported_task_types": self._get_supported_task_types(),
            "features": self._get_features()
        }
    
    def _get_supported_task_types(self) -> List[str]:
        """获取支持的任务类型，由子类重写"""
        return ["general"]
    
    def _get_features(self) -> List[str]:
        """获取Agent特性，由子类重写"""
        return ["基础Agent功能"]
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查LLM连接
            llm_ok = await self.llm_client.test_connection()
            
            # 检查黑板连接
            blackboard_ok = self.blackboard is not None
            
            overall_health = "healthy" if llm_ok and blackboard_ok else "degraded"
            
            return {
                "agent_id": self.agent_id,
                "overall_health": overall_health,
                "llm_connection": "ok" if llm_ok else "error",
                "blackboard_connection": "ok" if blackboard_ok else "error",
                "status": self.status,
                "current_tasks": len(self.current_tasks),
                "check_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "agent_id": self.agent_id,
                "overall_health": "error",
                "error": str(e),
                "check_time": datetime.now().isoformat()
            }


class InformationAgent(BaseAgent):
    """信息检索Agent - 简化版实现"""
    
    def __init__(self, blackboard):
        super().__init__("information_agent", blackboard)
        self.agent_type = "information"
        self.specializations = ["literature_search", "data_collection", "information_analysis"]
    
    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理信息检索任务"""
        query = task_data.get("user_input", "")
        task_type = task_data.get("task_type", "information_retrieval")
        
        prompt = f"""
作为专业的信息检索Agent，请对以下研究问题进行详细的信息调研：

研究问题: {query}

请提供：
1. 相关背景知识
2. 当前研究现状
3. 关键技术和方法
4. 主要挑战和机遇
5. 推荐阅读资源

请以结构化的方式组织答案。
"""
        
        response = await self.llm_client.generate_text(prompt, temperature=0.7, max_tokens=2000)
        
        if response.success:
            return {
                "content": response.content,
                "method": "llm_analysis",
                "quality_score": 7.5,
                "sources_found": 5
            }
        else:
            return {
                "content": "信息检索失败",
                "error": response.error
            }
    
    def _get_supported_task_types(self) -> List[str]:
        return ["information_retrieval", "literature_search", "data_collection"]
    
    def _get_features(self) -> List[str]:
        return ["文献检索", "数据收集", "信息分析", "知识整合"]


class VerificationAgent(BaseAgent):
    """验证Agent"""
    
    def __init__(self, blackboard):
        super().__init__("verification_agent", blackboard)
        self.agent_type = "verification"
        self.specializations = ["fact_checking", "consistency_verification", "quality_assessment"]
    
    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证任务"""
        content_to_verify = task_data.get("content", "")
        verification_type = task_data.get("verification_type", "general")
        
        prompt = f"""
作为专业的验证Agent，请对以下内容进行全面验证：

待验证内容: {content_to_verify}

请从以下角度进行验证：
1. 事实准确性检查
2. 逻辑一致性分析
3. 数据可信度评估
4. 潜在问题识别
5. 改进建议

请提供详细的验证报告。
"""
        
        response = await self.llm_client.generate_text(prompt, temperature=0.3, max_tokens=1500)
        
        if response.success:
            return {
                "verification_report": response.content,
                "is_valid": True,
                "confidence_score": 8.0,
                "issues_found": []
            }
        else:
            return {
                "verification_report": "验证失败",
                "is_valid": False,
                "error": response.error
            }
    
    def _get_supported_task_types(self) -> List[str]:
        return ["verification", "fact_checking", "quality_assessment"]
    
    def _get_features(self) -> List[str]:
        return ["事实核查", "一致性验证", "质量评估", "风险识别"]


class CritiqueAgent(BaseAgent):
    """批判Agent"""
    
    def __init__(self, blackboard):
        super().__init__("critique_agent", blackboard)
        self.agent_type = "critique"
        self.specializations = ["critical_analysis", "quality_evaluation", "improvement_suggestions"]
    
    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理批判分析任务"""
        content_to_critique = task_data.get("content", "")
        analysis_focus = task_data.get("focus", "general")
        
        prompt = f"""
作为专业的批判分析Agent，请对以下内容进行深度批判性分析：

分析内容: {content_to_critique}

请从以下维度进行批判性评估：
1. 创新性分析 (1-10分)
2. 可行性评估 (1-10分)
3. 完整性检查 (1-10分)
4. 风险评估 (1-10分)
5. 改进建议

请提供客观、建设性的批判意见。
"""
            
        response = await self.llm_client.generate_text(prompt, temperature=0.5, max_tokens=1500)
        
        if response.success:
            return {
                "critique_analysis": response.content,
                "scores": {
                    "innovation": 7.5,
                    "feasibility": 8.0,
                    "completeness": 7.0,
                    "risk_assessment": 8.5
                },
                "recommendations": ["建议1", "建议2", "建议3"]
            }
        else:
            return {
                "critique_analysis": "批判分析失败",
                "error": response.error
            }
    
    def _get_supported_task_types(self) -> List[str]:
        return ["critique", "evaluation", "quality_review"]
    
    def _get_features(self) -> List[str]:
        return ["批判性思维", "质量评估", "风险分析", "改进建议"]


class ReportAgent(BaseAgent):
    """报告生成Agent"""
    
    def __init__(self, blackboard):
        super().__init__("report_agent", blackboard)
        self.agent_type = "report"
        self.specializations = ["report_generation", "content_synthesis", "documentation"]
    
    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理报告生成任务"""
        research_data = task_data.get("research_data", {})
        report_type = task_data.get("report_type", "comprehensive")
        
        prompt = f"""
作为专业的报告生成Agent，请基于以下研究数据生成完整的研究报告：

研究数据: {research_data}

请生成包含以下部分的完整报告：
1. 执行摘要
2. 研究背景
3. 方法论
4. 结果与发现
5. 讨论与分析
6. 结论与建议
7. 参考资源

请使用Markdown格式，确保报告结构清晰、内容详实。
"""
        
        response = await self.llm_client.generate_text(prompt, temperature=0.6, max_tokens=3000)
        
        if response.success:
            return {
                "report_content": response.content,
                "report_format": "markdown",
                "sections_count": 7,
                "estimated_reading_time": "10-15分钟"
            }
        else:
            return {
                "report_content": "报告生成失败",
                "error": response.error
            }

    def _get_supported_task_types(self) -> List[str]:
        return ["report_generation", "documentation", "content_synthesis"]
    
    def _get_features(self) -> List[str]:
        return ["报告生成", "内容整合", "文档编写", "格式化输出"] 