"""
信息获取Agent - 集成关键词驱动和主题建模两种文献调研方法
基于"文献调研分析Agent技术方案 V1.0.pdf"实现的增强版文献调研Agent
"""

import asyncio
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import numpy as np

from backend.core.base_agent import BaseAgent
from backend.core.blackboard import Blackboard, BlackboardEvent, EventType, ReasoningStep
from backend.utils.literature_search import LiteratureSearchEngine, LiteratureSearchResult


@dataclass
class LiteratureDocument:
    """文献文档数据结构"""
    doc_id: str
    title: str
    authors: List[str]
    journal: str
    year: int
    abstract: str
    keywords: List[str]
    citation_count: int
    journal_impact_factor: float
    relevance_score: float
    quality_score: float
    source_database: str
    doi: str = ""
    full_text: str = ""


@dataclass 
class ResearchTopic:
    """研究主题数据结构"""
    topic_id: str
    topic_name: str
    keywords: List[str]
    description: str
    coherence_score: float
    document_count: int
    representative_docs: List[str]
    trend_indicator: str  # "emerging", "stable", "declining"


@dataclass
class KnowledgeGraph:
    """知识图谱数据结构"""
    graph_id: str
    nodes: List[Dict[str, Any]]  # 概念节点
    edges: List[Dict[str, Any]]  # 关系边
    central_concepts: List[str]
    connection_strength: Dict[str, float]


class InformationAgent(BaseAgent):
    """
    增强版信息获取Agent - 智能文献调研专家
    
    实现三种调研方法：
    1. 关键词驱动文献检索方法
    2. 主题建模智能发现方法  
    3. 混合模式调研方法
    符合docs要求的完整RAG功能
    """

    def __init__(self, blackboard: Blackboard, llm_client=None):
        super().__init__("information_agent", blackboard)
        
        # 调研方法配置
        self.research_methods = {
            "keyword_driven": "关键词驱动文献检索",
            "topic_modeling": "主题建模智能发现",
            "hybrid": "混合模式调研"
        }
        
        # 数据库配置
        self.search_databases = ["IEEE", "ACM", "SpringerLink", "PubMed", "arXiv", "CNKI", "Web of Science"]
        
        # 质量评估配置
        self.quality_weights = {
            "journal_impact": 0.25,    # 期刊影响因子
            "citation_count": 0.20,    # 引用次数  
            "author_authority": 0.20,  # 作者权威性
            "methodology": 0.20,       # 研究方法质量
            "relevance": 0.15          # 内容相关性
        }
        
        # 调研参数
        self.quality_threshold = 7.0
        self.max_papers_per_search = 100
        self.min_topic_coherence = 0.6
        
        # 缓存和状态
        self.literature_cache: Dict[str, LiteratureDocument] = {}
        self.topic_cache: Dict[str, ResearchTopic] = {}
        self.knowledge_graphs: Dict[str, KnowledgeGraph] = {}
        self.search_engine = LiteratureSearchEngine()
        self.search_databases = ["PubMed", "arXiv", "CrossRef", "GoogleScholar"]
        
        # 设置Agent类型
        self.agent_type = "information_gatherer"
        self.specializations = ["literature_search", "knowledge_graph", "research_analysis"]

    async def _process_task_impl(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """实现BaseAgent要求的任务处理方法"""
        try:
            # 根据任务类型选择处理方法
            task_type = task_data.get("task_type", "literature_search")
            
            if task_type == "literature_search":
                # 执行文献搜索
                keywords = task_data.get("keywords", [])
                if isinstance(keywords, str):
                    keywords = [keywords]
                
                documents = await self._parallel_database_search(keywords)
                
                return {
                    "task_type": task_type,
                    "documents": documents,
                    "document_count": len(documents),
                    "keywords_used": keywords
                }
            elif task_type == "research_analysis":
                # 执行研究分析
                method = task_data.get("method", "hybrid")
                result = await self._execute_literature_research(task_data, method)
                return result
            else:
                # 默认处理
                return {
                    "task_type": task_type,
                    "status": "completed",
                    "message": f"处理了{task_type}类型的任务"
                }
                
        except Exception as e:
            return {
                "task_type": task_data.get("task_type", "unknown"),
                "status": "failed",
                "error": str(e)
            }

    async def _load_prompt_templates(self):
        """加载Prompt模板"""
        self.prompt_templates = {
            "keyword_extraction": """
系统：你是一位专业的文献调研专家。请从以下研究需求中提取3-5个核心关键词。

研究需求：{research_request}
研究领域：{domain}
研究目标：{objectives}

要求：
1. 关键词应该是学术术语或技术名词
2. 具有较强的检索能力和代表性
3. 覆盖主要研究方向
4. 避免过于宽泛或过于具体
5. 考虑中英文表达

请以JSON格式返回：
{{
    "core_keywords": ["关键词1", "关键词2", "关键词3"],
    "expanded_keywords": {{
        "关键词1": ["同义词1", "相关词1"],
        "关键词2": ["同义词2", "相关词2"]
    }},
    "search_strategy": "关键词组合检索策略描述"
}}
""",
            
            "literature_quality_assessment": """
系统：你是文献质量评估专家。请评估以下文献的质量和相关性。

文献信息：
标题：{title}
作者：{authors}
期刊：{journal}
年份：{year}
摘要：{abstract}
引用次数：{citation_count}

            评估维度：
1. 研究方法质量 (0-10分)
2. 内容相关性 (0-10分)  
3. 学术权威性 (0-10分)
4. 创新性 (0-10分)
5. 可信度 (0-10分)

请以JSON格式返回：
{{
    "quality_scores": {{
        "methodology": 8.5,
        "relevance": 9.0,
        "authority": 8.0,
        "innovation": 7.5,
        "credibility": 8.5
    }},
    "overall_score": 8.3,
    "assessment_summary": "评估总结",
    "key_contributions": ["贡献1", "贡献2"],
    "limitations": ["局限1", "局限2"]
}}
""",

            "topic_discovery": """
系统：你是主题建模专家。请从以下文献集合中发现潜在的研究主题。

文献摘要集合：{abstracts}

分析要求：
1. 识别3-5个主要研究主题
2. 为每个主题提供描述性标题
3. 列出每个主题的关键概念
4. 评估主题的研究热度和发展趋势
5. 识别跨主题的联系

请以JSON格式返回：
{{
    "discovered_topics": [
        {{
            "topic_id": "topic_1",
            "topic_name": "主题名称",
            "keywords": ["关键词1", "关键词2"],
            "description": "主题描述",
            "document_count": 15,
            "trend": "emerging/stable/declining",
            "coherence_score": 0.85
        }}
    ],
    "topic_connections": [
        {{
            "topic1": "topic_1",
            "topic2": "topic_2", 
            "connection_strength": 0.7,
            "connection_type": "methodological/conceptual"
        }}
    ],
    "research_landscape": "研究全景分析"
}}
""",

            "knowledge_graph_construction": """
系统：你是知识图谱构建专家。请从文献信息中构建知识图谱。

文献数据：{literature_data}

构建要求：
1. 识别核心概念和实体
2. 构建概念间的关系
3. 计算概念的重要性权重
4. 识别知识集群和桥接概念

请以JSON格式返回：
{{
    "knowledge_graph": {{
        "nodes": [
            {{
                "id": "concept_1",
                "label": "概念名称",
                "type": "concept/method/application",
                "importance": 0.9,
                "description": "概念描述"
            }}
        ],
        "edges": [
            {{
                "source": "concept_1",
                "target": "concept_2",
                "relation": "relates_to/depends_on/enables",
                "strength": 0.8
            }}
        ]
    }},
    "central_concepts": ["核心概念1", "核心概念2"],
    "knowledge_clusters": ["集群1", "集群2"],
    "bridging_concepts": ["桥接概念1"]
}}
""",

            "research_trend_analysis": """
系统：你是研究趋势分析专家。请分析以下文献的时间序列数据，识别研究趋势。

文献时间数据：{temporal_data}
关键词演变：{keyword_evolution}

分析要求：
1. 识别研究热点的兴起和衰落
2. 预测未来研究方向
3. 识别新兴技术和方法
4. 分析研究重点的转移

请以JSON格式返回：
{{
    "trend_analysis": {{
        "emerging_trends": ["新兴趋势1", "新兴趋势2"],
        "declining_trends": ["衰落趋势1", "衰落趋势2"],
        "stable_areas": ["稳定领域1", "稳定领域2"],
        "future_directions": ["未来方向1", "未来方向2"]
    }},
    "hotspot_evolution": [
        {{
            "period": "2020-2022",
            "hotspots": ["热点1", "热点2"],
            "intensity": 0.8
        }}
    ],
    "prediction_confidence": 0.75,
    "recommendation": "基于趋势分析的调研建议"
}}
"""
        }

    async def _process_event_impl(self, event: BlackboardEvent) -> Any:
        """处理信息获取相关事件"""
        try:
            # 记录事件处理推理步骤
            event_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="event_processing",
                description=f"处理{event.event_type.value}事件",
                input_data={"event_type": event.event_type.value, "source_agent": event.agent_id},
                reasoning_text=f"信息获取Agent收到{event.event_type.value}事件，开始文献调研"
            )
            await self.blackboard.record_reasoning_step(event_step)
            
            if event.event_type == EventType.TASK_ASSIGNED:
                if event.target_agent == self.agent_id or event.data.get("task_type") == "information_enhanced":
                    return await self._handle_information_task(event)
            elif event.event_type == EventType.TASK_CREATED:
                return await self._handle_research_task(event.data)
            elif event.event_type == EventType.LITERATURE_SEARCH_REQUEST:
                return await self._handle_literature_search_request(event.data)
            elif event.event_type == EventType.DESIGN_REQUEST:
                return await self._handle_information_design_request(event.data)
            else:
                self.logger.warning(f"未处理的事件类型: {event.event_type}")

        except Exception as e:
            self.logger.error(f"信息获取处理失败: {e}")
            await self._publish_error_event(event, str(e))

    async def _handle_information_task(self, event: BlackboardEvent):
        """处理信息获取任务分配"""
        task_data = event.data
        session_id = event.session_id or "default"
        
        self.logger.info(f"开始信息获取任务: {task_data.get('user_input', '')[:50]}...")
        
        # 记录任务开始推理步骤
        task_start_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="task_start",
            description="开始信息获取和文献调研任务",
            input_data=task_data,
            reasoning_text="收到信息获取任务，开始执行智能文献调研和知识图谱构建"
        )
        await self.blackboard.record_reasoning_step(task_start_step)
        
        try:
            # 选择最适合的调研方法
            research_method = await self._select_optimal_research_method(task_data, session_id)
            
            # 记录方法选择推理步骤
            method_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="decision",
                description=f"选择{research_method}调研方法",
                input_data={"selected_method": research_method},
                reasoning_text=f"根据任务复杂度和需求分析，选择{research_method}作为最优调研策略",
                confidence=0.8
            )
            await self.blackboard.record_reasoning_step(method_step)
            
            # 执行文献调研
            research_result = await self._execute_literature_research(task_data, research_method)
            
            # 增强RAG功能处理
            rag_enhanced_result = await self._apply_rag_enhancement(research_result, task_data, session_id)
            
            # 发布信息更新事件
            await self.blackboard.publish_event(BlackboardEvent(
                event_type=EventType.INFORMATION_UPDATE,
                agent_id=self.agent_id,
                session_id=session_id,
                data={
                    "research_result": rag_enhanced_result,
                    "method": research_method,
                    "task_completed": True,
                    "timestamp": datetime.now().isoformat()
                }
            ))
            
            # 记录任务完成推理步骤
            completion_step = ReasoningStep(
                agent_id=self.agent_id,
                step_type="completion",
                description="信息获取任务完成",
                input_data=task_data,
                output_data={
                    "documents_found": len(rag_enhanced_result.get("literature_documents", [])),
                    "knowledge_graph_nodes": len(rag_enhanced_result.get("knowledge_graph", {}).get("nodes", []))
                },
                reasoning_text=f"成功完成文献调研，获得{len(rag_enhanced_result.get('literature_documents', []))}篇高质量文献",
                confidence=0.9
            )
            await self.blackboard.record_reasoning_step(completion_step)
            
            self.logger.info(f"信息获取完成，获得{len(rag_enhanced_result.get('literature_documents', []))}篇文献")
            
            return rag_enhanced_result
            
        except Exception as e:
            self.logger.error(f"信息获取任务失败: {e}")
            await self._publish_error_event(event, str(e))

    async def _select_optimal_research_method(self, task_data: Dict[str, Any], session_id: str) -> str:
        """选择最优调研方法"""
        user_input = task_data.get("user_input", "")
        
        # 简化的方法选择逻辑
        if "关键词" in user_input or "specific" in user_input.lower():
            return "keyword_driven"
        elif "主题" in user_input or "topic" in user_input.lower():
            return "topic_modeling"
        else:
            return "hybrid"

    async def _apply_rag_enhancement(self, research_result: Dict[str, Any], task_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """应用RAG增强功能"""
        # 记录RAG处理推理步骤
        rag_step = ReasoningStep(
            agent_id=self.agent_id,
            step_type="enhancement",
            description="应用RAG增强处理",
            input_data={"base_result": "research_result_summary"},
            reasoning_text="对基础调研结果应用RAG技术，增强知识检索和语义理解能力"
        )
        await self.blackboard.record_reasoning_step(rag_step)
        
        # 增强知识图谱
        if "knowledge_graph" in research_result:
            enhanced_kg = await self._enhance_knowledge_graph_with_rag(
                research_result["knowledge_graph"], 
                task_data.get("user_input", ""),
                session_id
            )
            research_result["knowledge_graph"] = enhanced_kg
        
        # 增强文献摘要和关键信息提取
        if "literature_documents" in research_result:
            enhanced_docs = await self._enhance_documents_with_rag(
                research_result["literature_documents"],
                task_data.get("user_input", ""),
                session_id
            )
            research_result["literature_documents"] = enhanced_docs
        
        # 添加智能问答能力
        research_result["rag_qa_capability"] = await self._build_rag_qa_system(
            research_result, task_data.get("user_input", ""), session_id
        )
        
        return research_result

    async def _enhance_knowledge_graph_with_rag(self, knowledge_graph: Dict[str, Any], user_query: str, session_id: str) -> Dict[str, Any]:
        """使用RAG技术增强知识图谱"""
        # 基于用户查询增强节点和边的相关性评分
        enhanced_nodes = []
        for node in knowledge_graph.get("nodes", []):
            # 计算节点与查询的语义相似度
            relevance_score = await self._calculate_semantic_relevance(node.get("name", ""), user_query)
            node["query_relevance"] = relevance_score
            enhanced_nodes.append(node)
        
        knowledge_graph["nodes"] = enhanced_nodes
        knowledge_graph["rag_enhanced"] = True
        knowledge_graph["query_context"] = user_query
        
        return knowledge_graph

    async def _enhance_documents_with_rag(self, documents: List[Any], user_query: str, session_id: str) -> List[Any]:
        """使用RAG技术增强文献文档"""
        enhanced_docs = []
        
        for doc in documents:
            if hasattr(doc, 'abstract') or isinstance(doc, dict):
                # 生成基于查询的关键信息摘要
                key_insights = await self._extract_query_relevant_insights(doc, user_query)
                
                if isinstance(doc, dict):
                    doc["rag_insights"] = key_insights
                    doc["query_relevance"] = await self._calculate_semantic_relevance(
                        doc.get("abstract", ""), user_query
                    )
                else:
                    # 如果是LiteratureDocument对象，转换为dict
                    doc_dict = {
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "authors": doc.authors,
                        "abstract": doc.abstract,
                        "keywords": doc.keywords,
                        "quality_score": doc.quality_score,
                        "rag_insights": key_insights,
                        "query_relevance": await self._calculate_semantic_relevance(doc.abstract, user_query)
                    }
                    doc = doc_dict
                
                enhanced_docs.append(doc)
        
        return enhanced_docs

    async def _build_rag_qa_system(self, research_result: Dict[str, Any], user_query: str, session_id: str) -> Dict[str, Any]:
        """构建RAG问答系统"""
        # 构建知识库
        knowledge_base = []
        
        # 从文献中提取知识
        for doc in research_result.get("literature_documents", []):
            knowledge_base.append({
                "source": "literature",
                "content": doc.get("abstract", "") if isinstance(doc, dict) else doc.abstract,
                "title": doc.get("title", "") if isinstance(doc, dict) else doc.title,
                "relevance": doc.get("query_relevance", 0) if isinstance(doc, dict) else 0
            })
        
        # 从知识图谱中提取知识
        kg = research_result.get("knowledge_graph", {})
        for node in kg.get("nodes", []):
            knowledge_base.append({
                "source": "knowledge_graph",
                "content": node.get("description", ""),
                "entity": node.get("name", ""),
                "relevance": node.get("query_relevance", 0)
            })
        
        return {
            "knowledge_base": knowledge_base,
            "query_capabilities": ["factual_qa", "conceptual_explanation", "comparison_analysis"],
            "supported_question_types": ["What", "How", "Why", "Compare", "Explain"],
            "ready": True
        }

    async def _calculate_semantic_relevance(self, text: str, query: str) -> float:
        """计算语义相关性（简化实现）"""
        # 简化的相关性计算，实际应用中可以使用更复杂的语义相似度模型
        text_lower = text.lower()
        query_lower = query.lower()
        
        # 基于关键词重叠的简单相关性
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        
        overlap = len(query_words.intersection(text_words))
        relevance = overlap / max(len(query_words), 1)
        
        return min(relevance * 2, 1.0)  # 归一化到0-1范围

    async def _extract_query_relevant_insights(self, doc: Any, user_query: str) -> List[str]:
        """提取与查询相关的关键洞察"""
        # 简化的洞察提取
        insights = []
        
        doc_text = doc.get("abstract", "") if isinstance(doc, dict) else getattr(doc, 'abstract', "")
        
        # 基于查询关键词提取相关句子
        sentences = doc_text.split('.')
        query_words = set(user_query.lower().split())
        
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            if len(query_words.intersection(sentence_words)) >= 1:
                insights.append(sentence.strip())
        
        return insights[:3]  # 返回最多3个关键洞察

    async def _handle_research_task(self, task_data: Dict[str, Any]) -> None:
        """处理研究任务"""
        task_type = task_data.get("task_type", "")
        
        if task_type not in ["information_retrieval", "literature_search", "keyword_driven_search", 
                           "topic_modeling_search", "hybrid_research"]:
            return

        self.logger.info(f"开始处理信息获取任务: {task_type}")
        
        # 确定调研方法
        if task_type == "keyword_driven_search":
            method = "keyword_driven"
        elif task_type == "topic_modeling_search":
            method = "topic_modeling"
        else:
            method = "hybrid"
        
        # 执行调研
        research_result = await self._execute_literature_research(task_data, method)
        
        # 发布调研完成事件
        await self.publish_result(
            EventType.ENHANCED_INFORMATION_RESEARCH_COMPLETED,
            {
                "task_id": task_data.get("task_id"),
                "research_result": research_result,
                "method": method,
                "session_id": task_data.get("session_id")
            }
        )

    async def _execute_literature_research(self, task_data: Dict[str, Any], method: str) -> Dict[str, Any]:
        """执行文献调研"""
        self.logger.info(f"执行{self.research_methods[method]}")
        
        if method == "keyword_driven":
            return await self._keyword_driven_research(task_data)
        elif method == "topic_modeling":
            return await self._topic_modeling_research(task_data)
        else:  # hybrid
            return await self._hybrid_research(task_data)

    async def _keyword_driven_research(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """方法一：关键词驱动文献检索方法"""
        self.logger.info("执行关键词驱动文献调研")
        
        try:
            # 1. 关键词提取和扩展
            keywords_result = await self._extract_and_expand_keywords(task_data)
            
            # 2. 多数据库并行检索
            search_results = await self._parallel_database_search(keywords_result["core_keywords"])
            
            # 3. 文献质量评估和筛选
            filtered_literature = await self._quality_assessment_and_filtering(search_results)
            
            # 4. 构建知识图谱
            knowledge_graph = await self._enhanced_knowledge_graph_construction(filtered_literature, task_data.get("session_id"))
            
            # 5. 生成调研报告
            research_report = await self._generate_keyword_driven_report(
                keywords_result, filtered_literature, knowledge_graph
            )
            
            # 发布关键词提取完成事件
            await self.publish_result(
                EventType.KEYWORD_EXTRACTION_COMPLETED,
                {
                    "keywords": keywords_result,
                    "literature_count": len(filtered_literature)
                }
            )
            
            # 发布知识图谱更新事件
            await self.publish_result(
                EventType.KNOWLEDGE_GRAPH_UPDATED,
                {
                    "knowledge_graph": knowledge_graph,
                    "method": "keyword_driven"
                }
            )
            
            return {
                "method": "keyword_driven",
                "keywords_result": keywords_result,
                "literature_documents": filtered_literature,
                "knowledge_graph": knowledge_graph,
                "research_report": research_report,
                "performance_metrics": {
                    "documents_retrieved": len(search_results),
                    "documents_after_filtering": len(filtered_literature),
                    "precision": len(filtered_literature) / max(len(search_results), 1),
                    "avg_quality_score": np.mean([doc.quality_score for doc in filtered_literature]) if filtered_literature else 0
                }
            }

        except Exception as e:
            self.logger.error(f"关键词驱动调研失败: {e}")
            return {"error": str(e), "method": "keyword_driven"}

    async def _topic_modeling_research(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """方法二：主题建模智能发现方法"""
        self.logger.info("执行主题建模文献调研")
        
        try:
            # 1. 收集种子文献
            seed_documents = await self._collect_seed_documents(task_data)
            
            # 2. 主题建模和发现
            discovered_topics = await self._discover_research_topics(seed_documents)
            
            # 3. 基于主题的扩展检索
            expanded_literature = await self._topic_based_expansion_search(discovered_topics)
            
            # 4. 语义聚类分析
            literature_clusters = await self._perform_semantic_clustering(expanded_literature)
            
            # 5. 研究趋势分析
            trend_analysis = await self._analyze_research_trends(expanded_literature)
            
            # 6. 专家知识验证
            validated_results = await self._expert_knowledge_validation(
                discovered_topics, literature_clusters, trend_analysis
            )
            
            # 7. 生成智能调研报告
            intelligent_report = await self._generate_topic_modeling_report(validated_results)
            
            # 发布主题建模完成事件
            await self.publish_result(
                EventType.TOPIC_MODELING_COMPLETED,
                {
                    "discovered_topics": discovered_topics,
                    "literature_clusters": literature_clusters
                }
            )
            
            # 发布研究趋势识别事件
            await self.publish_result(
                EventType.RESEARCH_TREND_IDENTIFIED,
                {
                    "trend_analysis": trend_analysis,
                    "method": "topic_modeling"
                }
            )
            
            return {
                "method": "topic_modeling",
                "discovered_topics": discovered_topics,
                "literature_clusters": literature_clusters,
                "trend_analysis": trend_analysis,
                "validated_results": validated_results,
                "intelligent_report": intelligent_report,
                "performance_metrics": {
                    "topics_discovered": len(discovered_topics),
                    "literature_processed": len(expanded_literature),
                    "cluster_coherence": np.mean([topic.coherence_score for topic in discovered_topics]),
                    "trend_confidence": trend_analysis.get("prediction_confidence", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"主题建模调研失败: {e}")
            return {"error": str(e), "method": "topic_modeling"}

    async def _hybrid_research(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """方法三：混合模式调研方法"""
        self.logger.info("执行混合模式文献调研")
        
        try:
            # 并行执行两种方法
            keyword_task = asyncio.create_task(self._keyword_driven_research(task_data))
            topic_task = asyncio.create_task(self._topic_modeling_research(task_data))
            
            keyword_result, topic_result = await asyncio.gather(keyword_task, topic_task)
            
            # 结果融合
            merged_results = await self._merge_research_results(keyword_result, topic_result)
            
            # 交叉验证
            cross_validated_results = await self._cross_validate_results(merged_results)
            
            # 综合质量评估
            comprehensive_quality = await self._comprehensive_quality_assessment(cross_validated_results)
            
            # 生成混合调研报告
            hybrid_report = await self._generate_hybrid_research_report(cross_validated_results)
            
            # 发布交叉验证完成事件
            await self.publish_result(
                EventType.CROSS_VALIDATION_COMPLETED,
                {
                    "validation_results": cross_validated_results,
                    "quality_assessment": comprehensive_quality
                }
            )
            
            return {
                "method": "hybrid",
                "keyword_driven_result": keyword_result,
                "topic_modeling_result": topic_result,
                "merged_results": merged_results,
                "cross_validated_results": cross_validated_results,
                "comprehensive_quality": comprehensive_quality,
                "hybrid_report": hybrid_report,
                "performance_metrics": {
                    "total_coverage": comprehensive_quality.get("coverage_score", 0),
                    "result_reliability": comprehensive_quality.get("reliability_score", 0),
                    "method_agreement": comprehensive_quality.get("agreement_score", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"混合模式调研失败: {e}")
            return {"error": str(e), "method": "hybrid"}

    async def _extract_and_expand_keywords(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取和扩展关键词"""
        prompt = self.format_prompt(
            "keyword_extraction",
            research_request=task_data.get("description", ""),
            domain=task_data.get("domain", ""),
            objectives=json.dumps(task_data.get("objectives", []), ensure_ascii=False)
        )
        
        response = await self.call_llm(prompt, response_format="json")
        return json.loads(response)

    async def _parallel_database_search(self, keywords: List[str]) -> List[LiteratureDocument]:
        """并行多数据库检索（真实API）"""
        search_tasks = []
        for database in self.search_databases:
            for keyword in keywords:
                task = asyncio.create_task(self._search_single_database(database, keyword))
                search_tasks.append(task)
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        # 合并和去重
        all_documents = []
        seen_titles = set()
        for result in search_results:
            if isinstance(result, list):
                for doc in result:
                    if doc.title not in seen_titles:
                        all_documents.append(doc)
                        seen_titles.add(doc.title)
        return all_documents

    async def _search_single_database(self, database: str, keyword: str) -> List[LiteratureDocument]:
        """单个数据库检索（真实API）"""
        limit = 20
        try:
            if database == "PubMed":
                results = self.search_engine.search_pubmed(keyword, limit)
            elif database == "arXiv":
                results = self.search_engine.search_arxiv(keyword, limit)
            elif database == "CrossRef":
                results = self.search_engine.search_crossref(keyword, limit)
            elif database == "GoogleScholar":
                try:
                    results = self.search_engine.search_serpapi_google_scholar(keyword, limit)
                except Exception as e:
                    self.logger.warning(f"GoogleScholar API异常: {e}")
                    results = []
            else:
                self.logger.warning(f"未知数据库: {database}")
                results = []
        except Exception as e:
            self.logger.warning(f"{database} 检索异常: {e}")
            results = []

        # 转换为 LiteratureDocument
        docs = []
        for i, item in enumerate(results):
            doc = LiteratureDocument(
                doc_id=f"doc_{database}_{keyword}_{i}",
                title=item.title,
                authors=item.authors,
                journal=item.journal,
                year=int(item.publication_date[:4]) if item.publication_date and item.publication_date[:4].isdigit() else 0,
                abstract=item.abstract,
                keywords=[keyword],
                citation_count=item.citation_count,
                journal_impact_factor=0.0,
                relevance_score=0.0,
                quality_score=0.0,
                source_database=item.source_database,
                doi=item.doi or "",
                full_text=""
            )
            docs.append(doc)
        self.logger.info(f"{database} 返回 {len(docs)} 条，高质量待评估")
        return docs

    async def _quality_assessment_and_filtering(self, documents: List[LiteratureDocument]) -> List[LiteratureDocument]:
        """文献质量评估和筛选"""
        assessed_documents = []
        
        for doc in documents:
            try:
                # 调用LLM进行质量评估
                assessment = await self._assess_single_document_quality(doc)
                
                # 更新文档的质量分数
                doc.quality_score = assessment["overall_score"]
                doc.relevance_score = assessment["quality_scores"]["relevance"]
                
                # 根据质量阈值筛选
                if doc.quality_score >= self.quality_threshold:
                    assessed_documents.append(doc)
                    
            except Exception as e:
                self.logger.warning(f"文档质量评估失败: {e}")
                continue
        
        # 发布文献质量评估完成事件
        await self.publish_result(
            EventType.LITERATURE_QUALITY_ASSESSED,
            {
                "total_documents": len(documents),
                "qualified_documents": len(assessed_documents),
                "avg_quality_score": np.mean([doc.quality_score for doc in assessed_documents]) if assessed_documents else 0
            }
        )
        
        return assessed_documents

    async def _assess_single_document_quality(self, doc: LiteratureDocument) -> Dict[str, Any]:
        """评估单个文档质量"""
        prompt = self.format_prompt(
            "literature_quality_assessment",
            title=doc.title,
            authors=", ".join(doc.authors),
            journal=doc.journal,
            year=doc.year,
            abstract=doc.abstract,
            citation_count=doc.citation_count
        )
        
        response = await self.call_llm(prompt, response_format="json")
        return json.loads(response)

    async def _enhanced_knowledge_graph_construction(self, documents: List[LiteratureDocument], 
                                                   session_id: str) -> KnowledgeGraph:
        """增强的知识图谱构建"""
        try:
            # 1. 概念提取和实体识别
            entities = await self._extract_scientific_entities(documents, session_id)
            
            # 2. 关系挖掘和语义连接
            relationships = await self._mine_semantic_relationships(entities, documents, session_id)
            
            # 3. 跨学科连接发现
            interdisciplinary_connections = await self._discover_interdisciplinary_connections(
                entities, relationships, session_id
            )
            
            # 4. 创新机会识别
            innovation_opportunities = await self._identify_innovation_opportunities(
                entities, relationships, interdisciplinary_connections, session_id
            )
            
            # 5. 构建增强知识图谱
            enhanced_kg = await self._build_enhanced_knowledge_graph(
                entities, relationships, interdisciplinary_connections, 
                innovation_opportunities, session_id
            )
            
            # 记录知识图谱构建过程
            await self._record_llm_chain_step(
                f"增强知识图谱构建完成: 实体数量 {len(entities)}",
                f"关系数量: {len(relationships)}, 跨学科连接: {len(interdisciplinary_connections)}, 创新机会: {len(innovation_opportunities)}",
                session_id
            )
            
            return enhanced_kg
            
        except Exception as e:
            self.logger.error(f"增强知识图谱构建失败: {e}")
            return await self._build_knowledge_graph(documents)

    async def _extract_scientific_entities(self, documents: List[LiteratureDocument], 
                                         session_id: str) -> List[Dict[str, Any]]:
        """提取科学实体和概念"""
        try:
            entities = []
            
            for doc in documents[:10]:  # 处理前10个文档以提高效率
                extraction_prompt = f"""
                从以下科学文献中提取关键实体和概念：
                
                标题：{doc.title}
                摘要：{doc.abstract}
                关键词：{', '.join(doc.keywords)}
                
                请提取以下类型的实体：
                
                1. 科学概念 (Scientific Concepts)
                2. 研究方法 (Research Methods)
                3. 技术术语 (Technical Terms)
                4. 材料/物质 (Materials/Substances)
                5. 理论模型 (Theoretical Models)
                6. 应用领域 (Application Domains)
                7. 研究问题 (Research Problems)
                8. 创新点 (Innovation Points)
                
                对每个实体，请提供：
                - 实体名称
                - 实体类型
                - 重要性评分 (1-10)
                - 简短描述
                - 学科领域
                
                以JSON格式返回实体列表。
                """
                
                response = await self.call_llm(
                    extraction_prompt,
                    temperature=0.3,
                    max_tokens=1500,
                    response_format="json",
                    session_id=session_id
                )
                
                try:
                    doc_entities = json.loads(response)
                    if isinstance(doc_entities, list):
                        for entity in doc_entities:
                            entity['source_doc'] = doc.doc_id
                            entity['source_title'] = doc.title
                            entities.append(entity)
                except json.JSONDecodeError:
                    self.logger.warning(f"实体提取响应解析失败: {doc.doc_id}")
                
                await asyncio.sleep(0.1)  # 避免API调用过频
            
            # 去重和聚合相似实体
            unique_entities = await self._deduplicate_entities(entities, session_id)
            
            return unique_entities
            
        except Exception as e:
            self.logger.error(f"科学实体提取失败: {e}")
            return []

    async def _mine_semantic_relationships(self, entities: List[Dict[str, Any]], 
                                         documents: List[LiteratureDocument],
                                         session_id: str) -> List[Dict[str, Any]]:
        """挖掘语义关系"""
        try:
            relationships = []
            
            # 基于实体共现挖掘关系
            entity_pairs = []
            for i, entity1 in enumerate(entities):
                for j, entity2 in enumerate(entities[i+1:], i+1):
                    if entity1.get('source_doc') == entity2.get('source_doc'):
                        entity_pairs.append((entity1, entity2))
            
            # 分批处理实体对以避免过多API调用
            for batch_start in range(0, min(len(entity_pairs), 50), 10):
                batch = entity_pairs[batch_start:batch_start+10]
                
                relationship_prompt = f"""
                分析以下实体对之间的语义关系：
                
                {json.dumps([{
                    'entity1': pair[0]['name'],
                    'entity2': pair[1]['name'],
                    'type1': pair[0]['type'],
                    'type2': pair[1]['type'],
                    'domain1': pair[0].get('domain', ''),
                    'domain2': pair[1].get('domain', '')
                } for pair in batch], ensure_ascii=False, indent=2)}
                
                对每个实体对，请识别以下类型的关系：
                
                1. 因果关系 (causal): A导致B
                2. 组成关系 (compositional): A是B的组成部分
                3. 功能关系 (functional): A用于B
                4. 相似关系 (similar): A与B相似
                5. 对立关系 (opposite): A与B对立
                6. 依赖关系 (dependency): A依赖于B
                7. 应用关系 (application): A应用于B
                8. 改进关系 (improvement): A改进B
                
                对于存在关系的实体对，请提供：
                - 关系类型
                - 关系强度 (1-10)
                - 关系描述
                - 置信度 (0-1)
                
                以JSON格式返回关系列表。
                """
                
                response = await self.call_llm(
                    relationship_prompt,
                    temperature=0.2,
                    max_tokens=1500,
                    response_format="json",
                    session_id=session_id
                )
                
                try:
                    batch_relationships = json.loads(response)
                    if isinstance(batch_relationships, list):
                        relationships.extend(batch_relationships)
                except json.JSONDecodeError:
                    self.logger.warning(f"关系挖掘响应解析失败")
                
                await asyncio.sleep(0.2)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"语义关系挖掘失败: {e}")
            return []

    async def _discover_interdisciplinary_connections(self, entities: List[Dict[str, Any]], 
                                                    relationships: List[Dict[str, Any]],
                                                    session_id: str) -> List[Dict[str, Any]]:
        """发现跨学科连接"""
        try:
            # 识别不同学科领域的实体
            domains = {}
            for entity in entities:
                domain = entity.get('domain', 'unknown')
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(entity)
            
            interdisciplinary_connections = []
            
            # 分析跨领域实体间的潜在连接
            domain_pairs = []
            domain_list = list(domains.keys())
            for i, domain1 in enumerate(domain_list):
                for domain2 in domain_list[i+1:]:
                    if domain1 != domain2:
                        domain_pairs.append((domain1, domain2))
            
            for domain1, domain2 in domain_pairs[:10]:  # 限制处理数量
                connection_prompt = f"""
                分析以下两个学科领域之间的潜在跨学科连接：
                
                领域1: {domain1}
                相关实体: {[entity['name'] for entity in domains[domain1][:5]]}
                
                领域2: {domain2}
                相关实体: {[entity['name'] for entity in domains[domain2][:5]]}
                
                请识别以下类型的跨学科连接：
                
                1. 方法迁移 (method_transfer): 一个领域的方法可应用于另一个领域
                2. 概念融合 (concept_fusion): 两个领域的概念可以结合
                3. 技术交叉 (technology_crossover): 技术在不同领域的应用
                4. 理论借鉴 (theory_borrowing): 理论框架的跨领域应用
                5. 数据共享 (data_sharing): 数据在不同领域的共同价值
                6. 工具共用 (tool_sharing): 工具和设备的跨领域使用
                
                对每个连接，请提供：
                - 连接类型
                - 连接描述
                - 创新潜力评分 (1-10)
                - 实现难度评分 (1-10)
                - 具体应用场景
                
                以JSON格式返回连接列表。
                """
                
                response = await self.call_llm(
                    connection_prompt,
                    temperature=0.4,
                    max_tokens=1500,
                    response_format="json",
                    session_id=session_id
                )
                
                try:
                    connections = json.loads(response)
                    if isinstance(connections, list):
                        for conn in connections:
                            conn['domain1'] = domain1
                            conn['domain2'] = domain2
                            interdisciplinary_connections.append(conn)
                except json.JSONDecodeError:
                    self.logger.warning(f"跨学科连接解析失败: {domain1} - {domain2}")
                
                await asyncio.sleep(0.3)
            
            return interdisciplinary_connections
            
        except Exception as e:
            self.logger.error(f"跨学科连接发现失败: {e}")
            return []

    async def _identify_innovation_opportunities(self, entities: List[Dict[str, Any]], 
                                               relationships: List[Dict[str, Any]],
                                               interdisciplinary_connections: List[Dict[str, Any]],
                                               session_id: str) -> List[Dict[str, Any]]:
        """识别创新机会"""
        try:
            innovation_opportunities = []
            
            # 基于实体和关系分析创新机会
            innovation_prompt = f"""
            基于以下科学知识图谱信息，识别潜在的创新机会：
            
            关键实体数量: {len(entities)}
            关系数量: {len(relationships)}
            跨学科连接: {len(interdisciplinary_connections)}
            
            高重要性实体: {[e['name'] for e in entities if e.get('importance', 0) >= 8][:10]}
            
            强关系: {[r for r in relationships if r.get('strength', 0) >= 8][:5]}
            
            高潜力跨学科连接: {[c for c in interdisciplinary_connections if c.get('innovation_potential', 0) >= 8][:5]}
            
            请识别以下类型的创新机会：
            
            1. 技术融合机会 (technology_fusion): 不同技术的创新性结合
            2. 方法创新机会 (method_innovation): 新方法的开发机会
            3. 应用拓展机会 (application_extension): 现有技术的新应用
            4. 理论突破机会 (theoretical_breakthrough): 理论创新的可能性
            5. 跨界合作机会 (cross_domain_collaboration): 跨领域合作的机会
            6. 技术空白机会 (technology_gap): 技术空白的填补机会
            
            对每个创新机会，请提供：
            - 机会类型
            - 机会描述
            - 创新程度评分 (1-10)
            - 实现可行性评分 (1-10)
            - 市场潜力评分 (1-10)
            - 技术难度评分 (1-10)
            - 所需资源
            - 预期影响
            
            以JSON格式返回创新机会列表。
            """
            
            response = await self.call_llm(
                innovation_prompt,
                temperature=0.5,
                max_tokens=2000,
                response_format="json",
                session_id=session_id
            )
            
            try:
                innovation_opportunities = json.loads(response)
                if not isinstance(innovation_opportunities, list):
                    innovation_opportunities = []
            except json.JSONDecodeError:
                self.logger.warning("创新机会识别响应解析失败")
                innovation_opportunities = []
            
            return innovation_opportunities
            
        except Exception as e:
            self.logger.error(f"创新机会识别失败: {e}")
            return []

    async def _build_enhanced_knowledge_graph(self, entities: List[Dict[str, Any]], 
                                            relationships: List[Dict[str, Any]],
                                            interdisciplinary_connections: List[Dict[str, Any]],
                                            innovation_opportunities: List[Dict[str, Any]],
                                            session_id: str) -> KnowledgeGraph:
        """构建增强知识图谱"""
        try:
            # 转换实体为节点
            nodes = []
            for entity in entities:
                node = {
                    "id": f"entity_{len(nodes)}",
                    "name": entity.get('name', ''),
                    "type": entity.get('type', 'concept'),
                    "domain": entity.get('domain', 'unknown'),
                    "importance": entity.get('importance', 5),
                    "description": entity.get('description', ''),
                    "source_docs": [entity.get('source_doc', '')]
                }
                nodes.append(node)
            
            # 添加跨学科连接节点
            for conn in interdisciplinary_connections:
                node = {
                    "id": f"connection_{len(nodes)}",
                    "name": f"{conn.get('domain1', '')} - {conn.get('domain2', '')} 连接",
                    "type": "interdisciplinary_connection",
                    "domain": "interdisciplinary",
                    "importance": conn.get('innovation_potential', 5),
                    "description": conn.get('description', ''),
                    "connection_type": conn.get('type', '')
                }
                nodes.append(node)
            
            # 添加创新机会节点
            for opp in innovation_opportunities:
                node = {
                    "id": f"opportunity_{len(nodes)}",
                    "name": f"创新机会: {opp.get('type', '')}",
                    "type": "innovation_opportunity",
                    "domain": "innovation",
                    "importance": opp.get('innovation_score', 5),
                    "description": opp.get('description', ''),
                    "feasibility": opp.get('feasibility', 5),
                    "market_potential": opp.get('market_potential', 5)
                }
                nodes.append(node)
            
            # 转换关系为边
            edges = []
            for rel in relationships:
                edge = {
                    "source": rel.get('entity1', ''),
                    "target": rel.get('entity2', ''),
                    "type": rel.get('type', 'related'),
                    "strength": rel.get('strength', 5),
                    "description": rel.get('description', ''),
                    "confidence": rel.get('confidence', 0.5)
                }
                edges.append(edge)
            
            # 计算中心概念
            entity_importance = {node['name']: node['importance'] for node in nodes}
            central_concepts = sorted(entity_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            central_concepts = [concept[0] for concept in central_concepts]
            
            # 计算连接强度
            connection_strength = {}
            for edge in edges:
                key = f"{edge['source']}-{edge['target']}"
                connection_strength[key] = edge.get('strength', 5)
            
            enhanced_kg = KnowledgeGraph(
                graph_id=f"enhanced_kg_{session_id}",
                nodes=nodes,
                edges=edges,
                central_concepts=central_concepts,
                connection_strength=connection_strength
            )
            
            return enhanced_kg
            
        except Exception as e:
            self.logger.error(f"增强知识图谱构建失败: {e}")
            # 返回基础知识图谱
            return KnowledgeGraph(
                graph_id=f"basic_kg_{session_id}",
                nodes=[],
                edges=[],
                central_concepts=[],
                connection_strength={}
            )

    async def _deduplicate_entities(self, entities: List[Dict[str, Any]], 
                                  session_id: str) -> List[Dict[str, Any]]:
        """去重和聚合相似实体"""
        try:
            if not entities:
                return []
            
            # 简单的基于名称相似度的去重
            unique_entities = []
            seen_names = set()
            
            for entity in entities:
                name = entity.get('name', '').lower().strip()
                if name and name not in seen_names:
                    seen_names.add(name)
                    unique_entities.append(entity)
            
            return unique_entities[:50]  # 限制实体数量
            
        except Exception as e:
            self.logger.error(f"实体去重失败: {e}")
            return entities[:50]

    async def _generate_keyword_driven_report(self, keywords_result: Dict[str, Any], 
                                            literature: List[LiteratureDocument], 
                                            knowledge_graph: KnowledgeGraph) -> Dict[str, Any]:
        """生成关键词驱动调研报告"""
        return {
            "report_type": "keyword_driven",
            "executive_summary": f"基于关键词驱动方法，检索到{len(literature)}篇高质量文献",
            "methodology": "关键词驱动文献检索策略",
            "key_findings": [
                f"识别了{len(keywords_result.get('core_keywords', []))}个核心关键词",
                f"构建了包含{len(knowledge_graph.nodes)}个节点的知识图谱",
                f"平均文献质量分数: {np.mean([doc.quality_score for doc in literature]):.2f}"
            ],
            "literature_overview": {
                "total_papers": len(literature),
                "year_distribution": self._analyze_year_distribution(literature),
                "journal_distribution": self._analyze_journal_distribution(literature)
            },
            "recommendations": [
                "基于关键词驱动方法的深入研究建议",
                "确定的高价值研究方向",
                "建议的后续调研重点"
            ]
        }

    async def _generate_topic_modeling_report(self, validated_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成主题建模调研报告"""
        return {
            "report_type": "topic_modeling",
            "executive_summary": "基于主题建模方法的智能文献分析报告",
            "methodology": "主题建模智能发现策略",
            "discovered_insights": [
                f"发现了{len(validated_results.get('validated_topics', []))}个主要研究主题",
                f"识别了{len(validated_results.get('validated_clusters', []))}个文献聚类",
                "揭示了隐含的跨学科研究联系"
            ],
            "innovation_opportunities": [
                "新兴研究主题和发展趋势",
                "跨学科研究机会",
                "研究空白和创新点"
            ],
            "recommendations": [
                "基于主题发现的研究建议",
                "新兴领域的探索方向",
                "跨学科合作机会"
            ]
        }

    async def _generate_hybrid_research_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成混合调研报告"""
        return {
            "report_type": "hybrid",
            "executive_summary": "结合关键词驱动和主题建模方法的综合文献调研报告",
            "methodology": "混合智能调研策略",
            "comprehensive_findings": [
                "整合了两种方法的优势",
                "提供了最全面的文献覆盖",
                "通过交叉验证确保了结果可靠性"
            ],
            "quality_metrics": results.get("comprehensive_quality", {}),
            "strategic_recommendations": [
                "基于综合分析的战略建议",
                "平衡精确性和发现性的研究方法",
                "多维度的研究路线图"
            ]
        }

    def _analyze_year_distribution(self, literature: List[LiteratureDocument]) -> Dict[str, int]:
        """分析年份分布"""
        year_count = {}
        for doc in literature:
            year = doc.year
            year_count[year] = year_count.get(year, 0) + 1
        return year_count

    def _analyze_journal_distribution(self, literature: List[LiteratureDocument]) -> Dict[str, int]:
        """分析期刊分布"""
        journal_count = {}
        for doc in literature:
            journal = doc.journal
            journal_count[journal] = journal_count.get(journal, 0) + 1
        return journal_count

    async def _publish_error_event(self, original_event: BlackboardEvent, error_msg: str):
        """发布错误事件"""
        await self.publish_result(
            EventType.CONFLICT_WARNING,
            {
                "error_type": "information_agent_error",
                "original_event_id": original_event.event_id,
                "error_message": error_msg,
                "agent": self.config.name
            }
        )
