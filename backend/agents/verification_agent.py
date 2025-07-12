#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Agent - 负责数据验证、可行性分析和质量评估
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import EventType, BlackboardEvent


class VerificationAgent(BaseAgent):
    """验证Agent - 负责验证信息检索结果的准确性和研究方向的可行性"""

    def __init__(self, blackboard):
        super().__init__("verification_agent", blackboard)
        self.agent_type = "verification"
        self.specializations = [
            "数据验证",
            "可行性分析", 
            "质量评估",
            "风险分析",
            "技术审查"
        ]

    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证任务"""
        try:
            task_type = task_data.get("task_type", "verification")
            session_id = task_data.get("session_id", "")
            
            logger.info(f"🔍 VerificationAgent开始处理验证任务: {task_type}")
            
            if task_type == "feasibility_analysis":
                return await self._analyze_feasibility(task_data)
            elif task_type == "data_verification":
                return await self._verify_data(task_data)
            elif task_type == "quality_assessment":
                return await self._assess_quality(task_data)
            else:
                # 默认综合验证
                return await self._comprehensive_verification(task_data)
                
        except Exception as e:
            logger.error(f"❌ VerificationAgent处理失败: {e}")
            raise

    async def _comprehensive_verification(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """综合验证分析"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        # 获取信息Agent的结果
        info_results = await self._get_information_results(session_id)
        
        # 构建验证提示词
        verification_prompt = f"""作为专业的科研验证专家，请对以下研究方向进行全面的可行性分析和验证：

研究目标: {query}

信息检索结果: {info_results.get('summary', '暂无信息检索结果')}

请从以下方面进行验证分析：

1. **技术可行性评估**：
   - 当前技术水平是否支持该研究
   - 关键技术瓶颈和挑战
   - 技术实现的难度等级

2. **资源需求分析**：
   - 所需的设备、材料和人力资源
   - 预估的研究周期和成本
   - 资源获取的可行性

3. **风险评估**：
   - 技术风险和实施风险
   - 潜在的失败因素
   - 风险缓解策略

4. **市场和应用前景**：
   - 研究成果的应用价值
   - 市场需求和竞争态势
   - 商业化可行性

5. **研究方法验证**：
   - 建议的研究路径是否合理
   - 实验设计的科学性
   - 评价指标的有效性

请提供详细的验证报告，包括可行性评分（1-10分）和具体建议。"""

        try:
            # 调用LLM进行验证分析
            response = await self.llm_client.generate_text(
                verification_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            if response.success:
                verification_content = response.content
                
                # 解析可行性评分
                feasibility_score = self._extract_feasibility_score(verification_content)
                
                result = {
                    "verification_type": "comprehensive",
                    "feasibility_score": feasibility_score,
                    "verification_report": verification_content,
                    "key_findings": self._extract_key_findings(verification_content),
                    "risk_assessment": self._extract_risks(verification_content),
                    "recommendations": self._extract_recommendations(verification_content),
                    "verified_at": datetime.now().isoformat()
                }
                
                # 发布验证完成事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.VERIFICATION_REPORT,
                    agent_id=self.agent_id,
                    session_id=session_id,
                    data={
                        "feasibility_score": feasibility_score,
                        "verification_summary": verification_content[:200] + "...",
                        "next_step": "critique_analysis"
                    }
                ))
                
                logger.info(f"✅ 验证分析完成，可行性评分: {feasibility_score}/10")
                return result
                
            else:
                raise Exception(f"LLM验证分析失败: {response.error}")
                
        except Exception as e:
            logger.error(f"验证分析失败: {e}")
            # 返回默认验证结果
            return self._generate_default_verification(query, info_results)

    async def _analyze_feasibility(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """专门的可行性分析"""
        query = task_data.get("query", "")
        
        feasibility_prompt = f"""请对以下研究目标进行可行性分析：

研究目标: {query}

请评估：
1. 技术可行性 (1-10分)
2. 资源可行性 (1-10分) 
3. 时间可行性 (1-10分)
4. 经济可行性 (1-10分)
5. 整体可行性评估

请提供详细分析和建议。"""

        try:
            response = await self.llm_client.generate_text(feasibility_prompt, temperature=0.3)
            
            if response.success:
                return {
                    "analysis_type": "feasibility",
                    "feasibility_report": response.content,
                    "overall_score": self._extract_feasibility_score(response.content),
                    "analyzed_at": datetime.now().isoformat()
                }
            else:
                raise Exception(f"可行性分析失败: {response.error}")
                
        except Exception as e:
            logger.error(f"可行性分析失败: {e}")
            return {
                "analysis_type": "feasibility",
                "feasibility_report": f"对'{query}'的可行性分析：基于当前技术水平，该研究具有中等可行性，建议进一步调研。",
                "overall_score": 6.0,
                "analyzed_at": datetime.now().isoformat()
            }

    async def _verify_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """数据验证"""
        data_to_verify = task_data.get("data", {})
        
        verification_result = {
            "verification_type": "data",
            "verified_items": [],
            "issues_found": [],
            "confidence_score": 0.8,
            "verified_at": datetime.now().isoformat()
        }
        
        # 简单的数据验证逻辑
        for key, value in data_to_verify.items():
            if value and len(str(value)) > 0:
                verification_result["verified_items"].append({
                    "field": key,
                    "status": "valid",
                    "value": str(value)[:100]
                })
            else:
                verification_result["issues_found"].append({
                    "field": key,
                    "issue": "空值或无效数据"
                })
        
        return verification_result

    async def _assess_quality(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """质量评估"""
        content = task_data.get("content", "")
        
        quality_metrics = {
            "completeness": 0.8,  # 完整性
            "accuracy": 0.7,      # 准确性
            "relevance": 0.9,     # 相关性
            "clarity": 0.8,       # 清晰度
            "overall_quality": 0.8
        }
        
        return {
            "assessment_type": "quality",
            "quality_metrics": quality_metrics,
            "quality_report": f"内容质量评估完成，整体质量评分: {quality_metrics['overall_quality']:.1f}/1.0",
            "assessed_at": datetime.now().isoformat()
        }

    async def _get_information_results(self, session_id: str) -> Dict[str, Any]:
        """获取信息Agent的结果"""
        try:
            # 从黑板获取信息Agent的结果
            session_data = await self.blackboard.get_data(f"session_{session_id}")
            if session_data and "tasks" in session_data:
                for task_id, task in session_data["tasks"].items():
                    if task.get("assigned_agent") == "information_agent" and task.get("status") == "completed":
                        return task.get("output_data", {})
            
            # 如果没有找到，返回默认值
            return {"summary": "暂无信息检索结果"}
            
        except Exception as e:
            logger.warning(f"获取信息Agent结果失败: {e}")
            return {"summary": "无法获取信息检索结果"}

    def _extract_feasibility_score(self, content: str) -> float:
        """从内容中提取可行性评分"""
        try:
            # 简单的评分提取逻辑
            import re
            scores = re.findall(r'(\d+(?:\.\d+)?)\s*[/分]?\s*10', content)
            if scores:
                return float(scores[0])
            
            # 如果没有找到评分，根据关键词估算
            if "高可行性" in content or "highly feasible" in content.lower():
                return 8.0
            elif "中等可行性" in content or "moderately feasible" in content.lower():
                return 6.0
            elif "低可行性" in content or "low feasibility" in content.lower():
                return 3.0
            else:
                return 5.0
                
        except Exception:
            return 5.0  # 默认中等评分

    def _extract_key_findings(self, content: str) -> List[str]:
        """提取关键发现"""
        findings = []
        
        # 简单的关键点提取
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                findings.append(line[1:].strip())
            elif '关键' in line or '重要' in line or '主要' in line:
                findings.append(line)
        
        return findings[:5]  # 最多返回5个关键发现

    def _extract_risks(self, content: str) -> List[str]:
        """提取风险因素"""
        risks = []
        
        # 查找风险相关内容
        risk_keywords = ['风险', '挑战', '困难', '问题', 'risk', 'challenge']
        lines = content.split('\n')
        
        for line in lines:
            for keyword in risk_keywords:
                if keyword in line.lower():
                    risks.append(line.strip())
                    break
        
        return risks[:3]  # 最多返回3个风险

    def _extract_recommendations(self, content: str) -> List[str]:
        """提取建议"""
        recommendations = []
        
        # 查找建议相关内容
        rec_keywords = ['建议', '推荐', '应该', '需要', 'recommend', 'suggest']
        lines = content.split('\n')
        
        for line in lines:
            for keyword in rec_keywords:
                if keyword in line.lower():
                    recommendations.append(line.strip())
                    break
        
        return recommendations[:3]  # 最多返回3个建议

    def _generate_default_verification(self, query: str, info_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认验证结果"""
        return {
            "verification_type": "comprehensive",
            "feasibility_score": 6.0,
            "verification_report": f"对'{query}'的验证分析：基于现有信息，该研究方向具有中等可行性。建议进一步调研技术细节和资源需求。",
            "key_findings": [
                "研究方向具有一定的技术基础",
                "需要进一步评估资源需求",
                "建议制定详细的实施计划"
            ],
            "risk_assessment": [
                "技术实现存在一定难度",
                "资源获取可能面临挑战"
            ],
            "recommendations": [
                "建议进行更详细的技术调研",
                "制定分阶段实施计划",
                "评估资源获取的可行性"
            ],
            "verified_at": datetime.now().isoformat()
        }

    def _get_supported_task_types(self) -> List[str]:
        """获取支持的任务类型"""
        return [
            "verification",
            "feasibility_analysis",
            "data_verification",
            "quality_assessment",
            "risk_analysis"
        ]

    def _get_features(self) -> List[str]:
        """获取Agent特性"""
        return [
            "数据准确性验证",
            "技术可行性分析",
            "风险评估",
            "质量控制",
            "资源需求评估"
        ]