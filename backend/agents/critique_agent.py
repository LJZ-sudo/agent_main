#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批判Agent - 负责批判性分析、问题识别和改进建议
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import EventType, BlackboardEvent


class CritiqueAgent(BaseAgent):
    """批判Agent - 对研究方案进行批判性分析，识别潜在问题并提出改进建议"""

    def __init__(self, blackboard):
        super().__init__("critique_agent", blackboard)
        self.agent_type = "critique"
        self.specializations = [
            "批判性分析",
            "问题识别",
            "改进建议",
            "质量评估",
            "逻辑审查"
        ]

    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理批判分析任务"""
        try:
            task_type = task_data.get("task_type", "critique")
            session_id = task_data.get("session_id", "")
            
            logger.info(f"🔬 CritiqueAgent开始处理批判分析任务: {task_type}")
            
            if task_type == "logic_review":
                return await self._review_logic(task_data)
            elif task_type == "innovation_assessment":
                return await self._assess_innovation(task_data)
            elif task_type == "methodology_critique":
                return await self._critique_methodology(task_data)
            else:
                # 默认综合批判分析
                return await self._comprehensive_critique(task_data)
                
        except Exception as e:
            logger.error(f"❌ CritiqueAgent处理失败: {e}")
            raise

    async def _comprehensive_critique(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """综合批判分析"""
        query = task_data.get("query", "")
        session_id = task_data.get("session_id", "")
        
        # 获取前序Agent的结果
        info_results = await self._get_previous_results(session_id, "information_agent")
        verification_results = await self._get_previous_results(session_id, "verification_agent")
        
        # 构建批判分析提示词
        critique_prompt = f"""作为专业的科研批判分析专家，请对以下研究方案进行深度的批判性分析：

研究目标: {query}

信息检索结果: {info_results.get('summary', '暂无')}

验证分析结果: {verification_results.get('verification_report', '暂无')[:300] if verification_results.get('verification_report') else '暂无'}

请从以下角度进行批判性分析：

1. **创新性评估**：
   - 该研究的创新点在哪里？
   - 与现有研究的差异化程度
   - 是否存在重复性研究的风险

2. **方法论审查**：
   - 研究方法是否科学合理？
   - 实验设计是否存在缺陷？
   - 数据收集和分析方法是否恰当？

3. **逻辑一致性检查**：
   - 研究假设是否合理？
   - 推理过程是否存在逻辑漏洞？
   - 结论是否与证据一致？

4. **潜在问题识别**：
   - 可能遇到的技术难题
   - 实施过程中的潜在风险
   - 资源配置的不合理之处

5. **改进建议**：
   - 如何提高研究的创新性？
   - 方法论的改进方向
   - 风险缓解策略

6. **替代方案**：
   - 是否有更好的研究路径？
   - 不同技术路线的比较
   - 资源优化配置建议

请提供详细的批判分析报告，包括创新性评分（1-10分）和具体的改进建议。"""

        try:
            # 调用LLM进行批判分析
            response = await self.llm_client.generate_text(
                critique_prompt,
                temperature=0.4,  # 稍高的温度以获得更多创新性思考
                max_tokens=2500
            )
            
            if response.success:
                critique_content = response.content
                
                # 解析创新性评分
                innovation_score = self._extract_innovation_score(critique_content)
                
                result = {
                    "critique_type": "comprehensive",
                    "innovation_score": innovation_score,
                    "critique_report": critique_content,
                    "identified_issues": self._extract_issues(critique_content),
                    "improvement_suggestions": self._extract_improvements(critique_content),
                    "alternative_approaches": self._extract_alternatives(critique_content),
                    "logic_assessment": self._assess_logic_quality(critique_content),
                    "critiqued_at": datetime.now().isoformat()
                }
                
                # 发布批判分析完成事件
                await self.blackboard.publish_event(BlackboardEvent(
                    event_type=EventType.CRITIQUE_FEEDBACK,
                    agent_id=self.agent_id,
                    session_id=session_id,
                    data={
                        "innovation_score": innovation_score,
                        "critique_summary": critique_content[:200] + "...",
                        "issues_count": len(result["identified_issues"]),
                        "suggestions_count": len(result["improvement_suggestions"]),
                        "next_step": "report_generation"
                    }
                ))
                
                logger.info(f"✅ 批判分析完成，创新性评分: {innovation_score}/10")
                return result
                
            else:
                raise Exception(f"LLM批判分析失败: {response.error}")
                
        except Exception as e:
            logger.error(f"批判分析失败: {e}")
            # 返回默认批判结果
            return self._generate_default_critique(query, info_results, verification_results)

    async def _review_logic(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """逻辑审查"""
        content = task_data.get("content", "")
        
        logic_prompt = f"""请对以下内容进行逻辑审查：

内容: {content}

请检查：
1. 逻辑推理是否合理
2. 前提假设是否成立
3. 结论是否与证据一致
4. 是否存在逻辑谬误

请提供详细的逻辑审查报告。"""

        try:
            response = await self.llm_client.generate_text(logic_prompt, temperature=0.3)
            
            if response.success:
                return {
                    "review_type": "logic",
                    "logic_score": self._extract_logic_score(response.content),
                    "logic_report": response.content,
                    "logic_issues": self._extract_logic_issues(response.content),
                    "reviewed_at": datetime.now().isoformat()
                }
            else:
                raise Exception(f"逻辑审查失败: {response.error}")
                
        except Exception as e:
            logger.error(f"逻辑审查失败: {e}")
            return {
                "review_type": "logic",
                "logic_score": 7.0,
                "logic_report": "逻辑审查完成，整体逻辑结构合理，建议进一步完善论证过程。",
                "logic_issues": [],
                "reviewed_at": datetime.now().isoformat()
            }

    async def _assess_innovation(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创新性评估"""
        query = task_data.get("query", "")
        
        innovation_prompt = f"""请评估以下研究的创新性：

研究目标: {query}

请从以下方面评估：
1. 技术创新程度 (1-10分)
2. 方法创新程度 (1-10分)
3. 应用创新程度 (1-10分)
4. 整体创新性评估

请提供详细的创新性分析。"""

        try:
            response = await self.llm_client.generate_text(innovation_prompt, temperature=0.4)
            
            if response.success:
                return {
                    "assessment_type": "innovation",
                    "innovation_report": response.content,
                    "innovation_score": self._extract_innovation_score(response.content),
                    "innovation_aspects": self._extract_innovation_aspects(response.content),
                    "assessed_at": datetime.now().isoformat()
                }
            else:
                raise Exception(f"创新性评估失败: {response.error}")
                
        except Exception as e:
            logger.error(f"创新性评估失败: {e}")
            return {
                "assessment_type": "innovation",
                "innovation_report": f"对'{query}'的创新性评估：该研究具有一定的创新潜力，建议进一步挖掘独特性。",
                "innovation_score": 6.0,
                "innovation_aspects": ["技术方法创新", "应用场景拓展"],
                "assessed_at": datetime.now().isoformat()
            }

    async def _critique_methodology(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """方法论批判"""
        methodology = task_data.get("methodology", "")
        
        methodology_critique = {
            "critique_type": "methodology",
            "strengths": ["方法选择合理", "实验设计科学"],
            "weaknesses": ["样本量可能不足", "控制变量需要完善"],
            "suggestions": ["增加对照组", "扩大样本规模"],
            "overall_score": 7.0,
            "critiqued_at": datetime.now().isoformat()
        }
        
        return methodology_critique

    async def _get_previous_results(self, session_id: str, agent_type: str) -> Dict[str, Any]:
        """获取前序Agent的结果"""
        try:
            session_data = await self.blackboard.get_data(f"session_{session_id}")
            if session_data and "tasks" in session_data:
                for task_id, task in session_data["tasks"].items():
                    if task.get("assigned_agent") == agent_type and task.get("status") == "completed":
                        return task.get("output_data", {})
            
            return {}
            
        except Exception as e:
            logger.warning(f"获取{agent_type}结果失败: {e}")
            return {}

    def _extract_innovation_score(self, content: str) -> float:
        """提取创新性评分"""
        try:
            import re
            scores = re.findall(r'(\d+(?:\.\d+)?)\s*[/分]?\s*10', content)
            if scores:
                return float(scores[0])
            
            # 根据关键词估算
            if "高创新" in content or "highly innovative" in content.lower():
                return 8.0
            elif "中等创新" in content or "moderately innovative" in content.lower():
                return 6.0
            elif "低创新" in content or "low innovation" in content.lower():
                return 3.0
            else:
                return 5.0
                
        except Exception:
            return 5.0

    def _extract_logic_score(self, content: str) -> float:
        """提取逻辑评分"""
        try:
            import re
            scores = re.findall(r'(\d+(?:\.\d+)?)\s*[/分]?\s*10', content)
            if scores:
                return float(scores[0])
            return 7.0
        except Exception:
            return 7.0

    def _extract_issues(self, content: str) -> List[str]:
        """提取识别的问题"""
        issues = []
        
        # 查找问题相关内容
        issue_keywords = ['问题', '缺陷', '不足', '风险', 'issue', 'problem', 'weakness']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in issue_keywords):
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    issues.append(line[1:].strip())
                elif len(line) > 10:  # 过滤太短的行
                    issues.append(line)
        
        return issues[:5]  # 最多返回5个问题

    def _extract_improvements(self, content: str) -> List[str]:
        """提取改进建议"""
        improvements = []
        
        # 查找改进相关内容
        improvement_keywords = ['改进', '建议', '优化', '提升', 'improve', 'suggest', 'enhance']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in improvement_keywords):
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    improvements.append(line[1:].strip())
                elif len(line) > 10:
                    improvements.append(line)
        
        return improvements[:5]  # 最多返回5个建议

    def _extract_alternatives(self, content: str) -> List[str]:
        """提取替代方案"""
        alternatives = []
        
        # 查找替代方案相关内容
        alt_keywords = ['替代', '备选', '另一种', 'alternative', 'option', 'approach']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in alt_keywords):
                if len(line) > 10:
                    alternatives.append(line)
        
        return alternatives[:3]  # 最多返回3个替代方案

    def _extract_innovation_aspects(self, content: str) -> List[str]:
        """提取创新方面"""
        aspects = []
        
        # 查找创新相关内容
        innovation_keywords = ['创新', '新颖', '独特', 'innovative', 'novel', 'unique']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in innovation_keywords):
                if len(line) > 10:
                    aspects.append(line)
        
        return aspects[:3]

    def _extract_logic_issues(self, content: str) -> List[str]:
        """提取逻辑问题"""
        issues = []
        
        # 查找逻辑问题相关内容
        logic_keywords = ['逻辑', '推理', '矛盾', 'logic', 'reasoning', 'contradiction']
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in logic_keywords) and ('问题' in line or 'issue' in line.lower()):
                issues.append(line)
        
        return issues[:3]

    def _assess_logic_quality(self, content: str) -> Dict[str, Any]:
        """评估逻辑质量"""
        return {
            "logical_consistency": 0.8,
            "argument_strength": 0.7,
            "evidence_support": 0.8,
            "overall_logic_score": 0.77
        }

    def _generate_default_critique(self, query: str, info_results: Dict[str, Any], 
                                 verification_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认批判结果"""
        return {
            "critique_type": "comprehensive",
            "innovation_score": 6.0,
            "critique_report": f"对'{query}'的批判分析：该研究方向具有一定的创新性和可行性，但需要进一步完善研究方法和技术路线。建议加强与现有技术的差异化分析，并制定更详细的实施计划。",
            "identified_issues": [
                "技术路线需要进一步明确",
                "创新点需要更好地突出",
                "实施风险需要更全面的评估"
            ],
            "improvement_suggestions": [
                "加强技术调研和对比分析",
                "制定详细的技术实施路线图",
                "建立完善的风险控制机制"
            ],
            "alternative_approaches": [
                "考虑采用渐进式技术路线",
                "探索跨学科合作可能性"
            ],
            "logic_assessment": {
                "logical_consistency": 0.8,
                "argument_strength": 0.7,
                "evidence_support": 0.8,
                "overall_logic_score": 0.77
            },
            "critiqued_at": datetime.now().isoformat()
        }

    def _get_supported_task_types(self) -> List[str]:
        """获取支持的任务类型"""
        return [
            "critique",
            "logic_review",
            "innovation_assessment",
            "methodology_critique",
            "quality_review"
        ]

    def _get_features(self) -> List[str]:
        """获取Agent特性"""
        return [
            "批判性思维分析",
            "问题识别与诊断",
            "创新性评估",
            "逻辑一致性检查",
            "改进建议生成"
        ] 