"""
文献质量评估系统
建立更精确的文献质量评估体系和指标
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JournalTier(Enum):
    """期刊级别枚举"""
    TOP_TIER = "top_tier"          # 顶级期刊 (Nature, Science, Cell等)
    HIGH_TIER = "high_tier"        # 高级期刊 (影响因子 > 10)
    MEDIUM_TIER = "medium_tier"    # 中级期刊 (影响因子 5-10)
    STANDARD_TIER = "standard_tier" # 标准期刊 (影响因子 2-5)
    LOW_TIER = "low_tier"          # 低级期刊 (影响因子 < 2)


class ResearchField(Enum):
    """研究领域枚举"""
    MATERIALS_SCIENCE = "materials_science"
    BIOMEDICAL = "biomedical"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    ENVIRONMENTAL_SCIENCE = "environmental_science"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    ENGINEERING = "engineering"
    INTERDISCIPLINARY = "interdisciplinary"


@dataclass
class QualityMetric:
    """质量评估指标"""
    metric_name: str
    weight: float
    score: float
    max_score: float = 10.0
    description: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class JournalInfo:
    """期刊信息"""
    name: str
    impact_factor: float
    tier: JournalTier
    field: ResearchField
    h_index: int = 0
    acceptance_rate: float = 0.0
    reputation_score: float = 0.0


@dataclass
class AuthorInfo:
    """作者信息"""
    name: str
    h_index: int = 0
    citation_count: int = 0
    affiliation: str = ""
    reputation_score: float = 0.0
    expertise_areas: List[str] = field(default_factory=list)


@dataclass
class LiteratureQualityAssessment:
    """文献质量评估结果"""
    document_id: str
    overall_score: float
    quality_grade: str  # A+, A, B+, B, C+, C, D
    metrics: List[QualityMetric]
    journal_info: Optional[JournalInfo] = None
    author_info: List[AuthorInfo] = field(default_factory=list)
    assessment_timestamp: datetime = field(default_factory=datetime.now)
    confidence_level: float = 0.0
    recommendation: str = ""
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)


class LiteratureQualityEvaluator:
    """
    文献质量评估器
    
    评估维度：
    1. 期刊质量 (30%)
    2. 作者声誉 (20%)
    3. 引用影响力 (25%)
    4. 内容质量 (15%)
    5. 方法学严谨性 (10%)
    """

    def __init__(self):
        # 评估权重配置
        self.evaluation_weights = {
            "journal_quality": 0.30,
            "author_reputation": 0.20,
            "citation_impact": 0.25,
            "content_quality": 0.15,
            "methodological_rigor": 0.10
        }
        
        # 期刊数据库（简化版，实际应连接真实数据库）
        self.journal_database = self._initialize_journal_database()
        
        # 评估标准
        self.quality_standards = self._initialize_quality_standards()

    def _initialize_journal_database(self) -> Dict[str, JournalInfo]:
        """初始化期刊数据库"""
        return {
            "nature": JournalInfo("Nature", 49.96, JournalTier.TOP_TIER, ResearchField.INTERDISCIPLINARY, 810, 0.08, 10.0),
            "science": JournalInfo("Science", 47.73, JournalTier.TOP_TIER, ResearchField.INTERDISCIPLINARY, 793, 0.07, 10.0),
            "cell": JournalInfo("Cell", 41.58, JournalTier.TOP_TIER, ResearchField.BIOMEDICAL, 567, 0.06, 9.8),
            "nature materials": JournalInfo("Nature Materials", 39.74, JournalTier.TOP_TIER, ResearchField.MATERIALS_SCIENCE, 445, 0.08, 9.7),
            "advanced materials": JournalInfo("Advanced Materials", 29.40, JournalTier.HIGH_TIER, ResearchField.MATERIALS_SCIENCE, 389, 0.12, 8.5),
            "proceedings of the national academy of sciences": JournalInfo("PNAS", 11.20, JournalTier.HIGH_TIER, ResearchField.INTERDISCIPLINARY, 567, 0.18, 8.2),
            "journal of the american chemical society": JournalInfo("JACS", 16.38, JournalTier.HIGH_TIER, ResearchField.CHEMISTRY, 445, 0.15, 8.8),
            "angewandte chemie": JournalInfo("Angew. Chem.", 16.82, JournalTier.HIGH_TIER, ResearchField.CHEMISTRY, 378, 0.14, 8.6),
            "physical review letters": JournalInfo("Phys. Rev. Lett.", 9.16, JournalTier.MEDIUM_TIER, ResearchField.PHYSICS, 334, 0.25, 7.5),
            "acs nano": JournalInfo("ACS Nano", 17.12, JournalTier.HIGH_TIER, ResearchField.MATERIALS_SCIENCE, 267, 0.16, 8.4)
        }

    def _initialize_quality_standards(self) -> Dict[str, Dict[str, Any]]:
        """初始化质量评估标准"""
        return {
            "journal_quality": {
                "top_tier": {"score": 10.0, "description": "顶级期刊，学术声誉极高"},
                "high_tier": {"score": 8.5, "description": "高级期刊，影响因子>10"},
                "medium_tier": {"score": 6.5, "description": "中级期刊，影响因子5-10"},
                "standard_tier": {"score": 4.5, "description": "标准期刊，影响因子2-5"},
                "low_tier": {"score": 2.5, "description": "低级期刊，影响因子<2"}
            },
            "citation_thresholds": {
                "excellent": 100,    # 引用数>100为优秀
                "good": 50,         # 引用数50-100为良好
                "average": 20,      # 引用数20-50为平均
                "poor": 5           # 引用数<5为较差
            },
            "content_quality_indicators": [
                "methodology_description",
                "experimental_design",
                "statistical_analysis",
                "reproducibility",
                "novelty",
                "significance"
            ]
        }

    async def evaluate_literature_quality(
        self, 
        document: Dict[str, Any],
        detailed_analysis: bool = True
    ) -> LiteratureQualityAssessment:
        """
        评估单篇文献的质量
        
        Args:
            document: 文献文档数据
            detailed_analysis: 是否进行详细分析
            
        Returns:
            LiteratureQualityAssessment: 质量评估结果
        """
        try:
            logger.info(f"开始评估文献质量: {document.get('title', 'Unknown')}")
            
            # 提取基本信息
            doc_id = document.get('doc_id', document.get('id', 'unknown'))
            title = document.get('title', '')
            journal = document.get('journal', '').lower()
            authors = document.get('authors', [])
            citation_count = document.get('citation_count', 0)
            year = document.get('year', datetime.now().year)
            abstract = document.get('abstract', '')
            keywords = document.get('keywords', [])
            
            # 执行各维度评估
            metrics = []
            
            # 1. 期刊质量评估
            journal_metric = await self._evaluate_journal_quality(journal, document)
            metrics.append(journal_metric)
            
            # 2. 作者声誉评估
            author_metric = await self._evaluate_author_reputation(authors, document)
            metrics.append(author_metric)
            
            # 3. 引用影响力评估
            citation_metric = await self._evaluate_citation_impact(citation_count, year)
            metrics.append(citation_metric)
            
            # 4. 内容质量评估
            content_metric = await self._evaluate_content_quality(title, abstract, keywords)
            metrics.append(content_metric)
            
            # 5. 方法学严谨性评估
            method_metric = await self._evaluate_methodological_rigor(abstract, document)
            metrics.append(method_metric)
            
            # 计算综合评分
            overall_score = self._calculate_overall_score(metrics)
            quality_grade = self._determine_quality_grade(overall_score)
            confidence_level = self._calculate_confidence_level(metrics, document)
            
            # 生成推荐意见
            recommendation = self._generate_recommendation(overall_score, metrics, document)
            
            # 详细分析（可选）
            detailed_analysis_result = {}
            if detailed_analysis:
                detailed_analysis_result = await self._perform_detailed_analysis(document, metrics)
            
            # 获取期刊信息
            journal_info = self._get_journal_info(journal)
            
            # 构建评估结果
            assessment = LiteratureQualityAssessment(
                document_id=doc_id,
                overall_score=overall_score,
                quality_grade=quality_grade,
                metrics=metrics,
                journal_info=journal_info,
                confidence_level=confidence_level,
                recommendation=recommendation,
                detailed_analysis=detailed_analysis_result
            )
            
            logger.info(f"文献质量评估完成: {quality_grade} (评分: {overall_score:.2f})")
            return assessment
            
        except Exception as e:
            logger.error(f"文献质量评估失败: {e}")
            # 返回默认评估结果
            return LiteratureQualityAssessment(
                document_id=document.get('doc_id', 'unknown'),
                overall_score=0.0,
                quality_grade="未评估",
                metrics=[],
                confidence_level=0.0,
                recommendation="评估过程出现错误，建议人工审核"
            )

    async def _evaluate_journal_quality(self, journal: str, document: Dict[str, Any]) -> QualityMetric:
        """评估期刊质量"""
        journal_info = self._get_journal_info(journal)
        
        if journal_info:
            tier = journal_info.tier
            score = self.quality_standards["journal_quality"][tier.value]["score"]
            description = self.quality_standards["journal_quality"][tier.value]["description"]
            evidence = [f"期刊: {journal_info.name}", f"影响因子: {journal_info.impact_factor}"]
        else:
            # 未知期刊，基于其他信息推断
            score = 3.0  # 默认中等偏下
            description = "未知期刊，需要进一步验证"
            evidence = [f"期刊: {journal}", "影响因子: 未知"]
        
        return QualityMetric(
            metric_name="journal_quality",
            weight=self.evaluation_weights["journal_quality"],
            score=score,
            description=description,
            evidence=evidence
        )

    async def _evaluate_author_reputation(self, authors: List[str], document: Dict[str, Any]) -> QualityMetric:
        """评估作者声誉"""
        if not authors:
            return QualityMetric(
                metric_name="author_reputation",
                weight=self.evaluation_weights["author_reputation"],
                score=2.0,
                description="无作者信息",
                evidence=["作者信息缺失"]
            )
        
        # 简化的作者声誉评估（实际应连接学者数据库）
        author_count = len(authors)
        
        # 基于作者数量和机构推断声誉
        score = 5.0  # 基础分
        evidence = [f"作者数量: {author_count}"]
        
        # 检查是否有知名机构
        affiliation_text = document.get('affiliation', '').lower()
        prestigious_institutions = ['mit', 'stanford', 'harvard', 'cambridge', 'oxford', 'tsinghua', 'peking university']
        
        for institution in prestigious_institutions:
            if institution in affiliation_text:
                score += 1.5
                evidence.append(f"知名机构: {institution}")
                break
        
        # 限制最高分
        score = min(score, 10.0)
        
        return QualityMetric(
            metric_name="author_reputation",
            weight=self.evaluation_weights["author_reputation"],
            score=score,
            description=f"基于{author_count}位作者的声誉评估",
            evidence=evidence
        )

    async def _evaluate_citation_impact(self, citation_count: int, year: int) -> QualityMetric:
        """评估引用影响力"""
        current_year = datetime.now().year
        years_since_publication = max(1, current_year - year)
        
        # 年均引用数
        annual_citations = citation_count / years_since_publication
        
        # 基于引用阈值评分
        thresholds = self.quality_standards["citation_thresholds"]
        
        if annual_citations >= thresholds["excellent"] / 5:  # 年均20次以上
            score = 10.0
            description = "引用影响力优秀"
        elif annual_citations >= thresholds["good"] / 5:     # 年均10次以上
            score = 8.0
            description = "引用影响力良好"
        elif annual_citations >= thresholds["average"] / 5:  # 年均4次以上
            score = 6.0
            description = "引用影响力平均"
        elif annual_citations >= thresholds["poor"] / 5:     # 年均1次以上
            score = 4.0
            description = "引用影响力较低"
        else:
            score = 2.0
            description = "引用影响力很低"
        
        evidence = [
            f"总引用数: {citation_count}",
            f"发表年份: {year}",
            f"年均引用: {annual_citations:.1f}"
        ]
        
        return QualityMetric(
            metric_name="citation_impact",
            weight=self.evaluation_weights["citation_impact"],
            score=score,
            description=description,
            evidence=evidence
        )

    async def _evaluate_content_quality(self, title: str, abstract: str, keywords: List[str]) -> QualityMetric:
        """评估内容质量"""
        score = 5.0  # 基础分
        evidence = []
        
        # 标题质量分析
        if title:
            title_length = len(title.split())
            if 8 <= title_length <= 15:  # 合适的标题长度
                score += 0.5
                evidence.append("标题长度适中")
            
            # 检查标题中的关键词
            quality_keywords = ['novel', 'new', 'improved', 'enhanced', 'efficient', 'innovative']
            if any(keyword in title.lower() for keyword in quality_keywords):
                score += 0.5
                evidence.append("标题体现创新性")
        
        # 摘要质量分析
        if abstract:
            abstract_length = len(abstract.split())
            if 150 <= abstract_length <= 300:  # 合适的摘要长度
                score += 1.0
                evidence.append("摘要长度适中")
            
            # 检查摘要结构
            structure_indicators = ['background', 'method', 'result', 'conclusion', 'objective']
            structure_score = sum(1 for indicator in structure_indicators if indicator in abstract.lower())
            score += structure_score * 0.3
            evidence.append(f"摘要结构完整性: {structure_score}/5")
        
        # 关键词质量
        if keywords:
            keyword_count = len(keywords)
            if 3 <= keyword_count <= 8:  # 合适的关键词数量
                score += 0.5
                evidence.append(f"关键词数量合适: {keyword_count}")
        
        # 限制最高分
        score = min(score, 10.0)
        
        return QualityMetric(
            metric_name="content_quality",
            weight=self.evaluation_weights["content_quality"],
            score=score,
            description="基于标题、摘要和关键词的内容质量评估",
            evidence=evidence
        )

    async def _evaluate_methodological_rigor(self, abstract: str, document: Dict[str, Any]) -> QualityMetric:
        """评估方法学严谨性"""
        score = 5.0  # 基础分
        evidence = []
        
        if abstract:
            abstract_lower = abstract.lower()
            
            # 检查方法学关键词
            method_keywords = {
                'experimental': 1.0,
                'statistical': 0.8,
                'control': 0.8,
                'randomized': 1.0,
                'double-blind': 1.2,
                'reproducible': 1.0,
                'validated': 0.8,
                'quantitative': 0.6,
                'systematic': 0.8
            }
            
            for keyword, weight in method_keywords.items():
                if keyword in abstract_lower:
                    score += weight
                    evidence.append(f"方法学关键词: {keyword}")
            
            # 检查统计分析
            stats_keywords = ['p-value', 'significance', 'correlation', 'regression', 'anova']
            stats_count = sum(1 for keyword in stats_keywords if keyword in abstract_lower)
            if stats_count > 0:
                score += stats_count * 0.5
                evidence.append(f"统计分析指标: {stats_count}")
        
        # 检查是否有补充材料
        if document.get('supplementary_material', False):
            score += 1.0
            evidence.append("包含补充材料")
        
        # 限制最高分
        score = min(score, 10.0)
        
        return QualityMetric(
            metric_name="methodological_rigor",
            weight=self.evaluation_weights["methodological_rigor"],
            score=score,
            description="基于方法学描述的严谨性评估",
            evidence=evidence
        )

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算综合评分"""
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for metric in metrics:
            weighted_score = metric.score * metric.weight
            total_weighted_score += weighted_score
            total_weight += metric.weight
        
        if total_weight > 0:
            overall_score = total_weighted_score / total_weight
        else:
            overall_score = 0.0
        
        return round(overall_score, 2)

    def _determine_quality_grade(self, overall_score: float) -> str:
        """确定质量等级"""
        if overall_score >= 9.0:
            return "A+"
        elif overall_score >= 8.5:
            return "A"
        elif overall_score >= 7.5:
            return "B+"
        elif overall_score >= 6.5:
            return "B"
        elif overall_score >= 5.5:
            return "C+"
        elif overall_score >= 4.0:
            return "C"
        else:
            return "D"

    def _calculate_confidence_level(self, metrics: List[QualityMetric], document: Dict[str, Any]) -> float:
        """计算置信度"""
        confidence = 0.8  # 基础置信度
        
        # 基于可用信息的完整性调整置信度
        info_completeness = 0
        total_fields = 6
        
        if document.get('title'):
            info_completeness += 1
        if document.get('abstract'):
            info_completeness += 1
        if document.get('authors'):
            info_completeness += 1
        if document.get('journal'):
            info_completeness += 1
        if document.get('year'):
            info_completeness += 1
        if document.get('citation_count', 0) > 0:
            info_completeness += 1
        
        completeness_ratio = info_completeness / total_fields
        confidence *= completeness_ratio
        
        # 基于期刊信息可用性调整
        journal = document.get('journal', '').lower()
        if self._get_journal_info(journal):
            confidence += 0.1
        
        return round(min(confidence, 1.0), 2)

    def _generate_recommendation(self, overall_score: float, metrics: List[QualityMetric], document: Dict[str, Any]) -> str:
        """生成推荐意见"""
        grade = self._determine_quality_grade(overall_score)
        
        if grade in ["A+", "A"]:
            recommendation = "强烈推荐：高质量文献，可作为重要参考"
        elif grade in ["B+", "B"]:
            recommendation = "推荐：质量良好的文献，值得参考"
        elif grade in ["C+", "C"]:
            recommendation = "谨慎使用：质量一般，需要进一步验证"
        else:
            recommendation = "不推荐：质量较低，建议寻找更好的替代文献"
        
        # 添加具体建议
        low_score_metrics = [m for m in metrics if m.score < 5.0]
        if low_score_metrics:
            weak_areas = [m.metric_name for m in low_score_metrics]
            recommendation += f"\n注意：在{', '.join(weak_areas)}方面评分较低"
        
        return recommendation

    async def _perform_detailed_analysis(self, document: Dict[str, Any], metrics: List[QualityMetric]) -> Dict[str, Any]:
        """执行详细分析"""
        analysis = {
            "strengths": [],
            "weaknesses": [],
            "improvement_suggestions": [],
            "comparative_analysis": {},
            "risk_assessment": {}
        }
        
        # 分析优势和劣势
        for metric in metrics:
            if metric.score >= 7.0:
                analysis["strengths"].append(f"{metric.metric_name}: {metric.description}")
            elif metric.score < 5.0:
                analysis["weaknesses"].append(f"{metric.metric_name}: {metric.description}")
        
        # 改进建议
        if any(m.metric_name == "citation_impact" and m.score < 5.0 for m in metrics):
            analysis["improvement_suggestions"].append("建议关注更多高引用文献")
        
        if any(m.metric_name == "journal_quality" and m.score < 6.0 for m in metrics):
            analysis["improvement_suggestions"].append("建议优先选择高影响因子期刊的文献")
        
        # 风险评估
        overall_score = self._calculate_overall_score(metrics)
        if overall_score < 5.0:
            analysis["risk_assessment"]["reliability"] = "低"
            analysis["risk_assessment"]["recommendation"] = "需要寻找更多高质量文献支撑"
        else:
            analysis["risk_assessment"]["reliability"] = "中等" if overall_score < 7.0 else "高"
            analysis["risk_assessment"]["recommendation"] = "可以作为研究参考"
        
        return analysis

    def _get_journal_info(self, journal_name: str) -> Optional[JournalInfo]:
        """获取期刊信息"""
        journal_name_lower = journal_name.lower().strip()
        return self.journal_database.get(journal_name_lower)

    async def batch_evaluate_literature(
        self, 
        documents: List[Dict[str, Any]], 
        progress_callback: Optional[callable] = None
    ) -> List[LiteratureQualityAssessment]:
        """批量评估文献质量"""
        results = []
        total_docs = len(documents)
        
        logger.info(f"开始批量评估 {total_docs} 篇文献")
        
        for i, document in enumerate(documents):
            try:
                assessment = await self.evaluate_literature_quality(document, detailed_analysis=False)
                results.append(assessment)
                
                if progress_callback:
                    progress_callback(i + 1, total_docs)
                    
            except Exception as e:
                logger.error(f"评估文献 {document.get('title', 'Unknown')} 失败: {e}")
                # 添加失败的评估结果
                results.append(LiteratureQualityAssessment(
                    document_id=document.get('doc_id', f'unknown_{i}'),
                    overall_score=0.0,
                    quality_grade="评估失败",
                    metrics=[],
                    recommendation="评估过程出现错误"
                ))
        
        logger.info(f"批量评估完成，成功评估 {len([r for r in results if r.overall_score > 0])} 篇文献")
        return results

    def generate_quality_report(self, assessments: List[LiteratureQualityAssessment]) -> Dict[str, Any]:
        """生成质量评估报告"""
        if not assessments:
            return {"error": "无评估结果"}
        
        # 统计分析
        total_docs = len(assessments)
        valid_assessments = [a for a in assessments if a.overall_score > 0]
        
        if not valid_assessments:
            return {"error": "无有效评估结果"}
        
        scores = [a.overall_score for a in valid_assessments]
        grades = [a.quality_grade for a in valid_assessments]
        
        # 基本统计
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        # 等级分布
        grade_distribution = {}
        for grade in grades:
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # 推荐文献（A级以上）
        recommended_docs = [a for a in valid_assessments if a.quality_grade in ["A+", "A"]]
        
        report = {
            "评估概览": {
                "总文献数": total_docs,
                "有效评估数": len(valid_assessments),
                "平均评分": round(avg_score, 2),
                "最高评分": max_score,
                "最低评分": min_score
            },
            "质量等级分布": grade_distribution,
            "推荐文献": [
                {
                    "文档ID": doc.document_id,
                    "评分": doc.overall_score,
                    "等级": doc.quality_grade,
                    "推荐理由": doc.recommendation
                }
                for doc in recommended_docs[:10]  # 前10篇推荐文献
            ],
            "质量分析": {
                "高质量文献比例": len([a for a in valid_assessments if a.overall_score >= 7.0]) / len(valid_assessments) * 100,
                "低质量文献比例": len([a for a in valid_assessments if a.overall_score < 5.0]) / len(valid_assessments) * 100,
                "平均置信度": sum(a.confidence_level for a in valid_assessments) / len(valid_assessments)
            },
            "改进建议": self._generate_collection_improvement_suggestions(valid_assessments)
        }
        
        return report

    def _generate_collection_improvement_suggestions(self, assessments: List[LiteratureQualityAssessment]) -> List[str]:
        """为文献集合生成改进建议"""
        suggestions = []
        
        # 分析整体质量水平
        avg_score = sum(a.overall_score for a in assessments) / len(assessments)
        
        if avg_score < 6.0:
            suggestions.append("整体文献质量偏低，建议提高筛选标准")
        
        # 分析期刊质量分布
        journal_scores = []
        for assessment in assessments:
            for metric in assessment.metrics:
                if metric.metric_name == "journal_quality":
                    journal_scores.append(metric.score)
                    break
        
        if journal_scores and sum(journal_scores) / len(journal_scores) < 6.0:
            suggestions.append("建议优先选择高影响因子期刊的文献")
        
        # 分析引用影响力
        citation_scores = []
        for assessment in assessments:
            for metric in assessment.metrics:
                if metric.metric_name == "citation_impact":
                    citation_scores.append(metric.score)
                    break
        
        if citation_scores and sum(citation_scores) / len(citation_scores) < 5.0:
            suggestions.append("建议增加高引用文献的比例")
        
        # 检查质量分布
        high_quality_ratio = len([a for a in assessments if a.overall_score >= 7.0]) / len(assessments)
        if high_quality_ratio < 0.3:
            suggestions.append("高质量文献比例偏低，建议加强文献筛选")
        
        return suggestions


# 使用示例
async def main():
    """示例用法"""
    evaluator = LiteratureQualityEvaluator()
    
    # 示例文献数据
    sample_documents = [
        {
            "doc_id": "doc_001",
            "title": "Novel Graphene-Based Composite Materials for Enhanced Electrical Conductivity",
            "authors": ["Zhang, L.", "Wang, M.", "Li, X."],
            "journal": "Nature Materials",
            "year": 2023,
            "abstract": "This study presents a novel approach to synthesize graphene-based composite materials with enhanced electrical conductivity. We developed a systematic methodology involving controlled chemical vapor deposition and surface functionalization. Statistical analysis revealed significant improvements in conductivity compared to conventional materials. The results demonstrate the potential for industrial applications.",
            "keywords": ["graphene", "composite materials", "electrical conductivity", "surface functionalization"],
            "citation_count": 45,
            "affiliation": "MIT Materials Science Department"
        },
        {
            "doc_id": "doc_002", 
            "title": "Study on Materials",
            "authors": ["Smith, J."],
            "journal": "Unknown Journal",
            "year": 2020,
            "abstract": "We studied some materials and found results.",
            "keywords": ["materials"],
            "citation_count": 2
        }
    ]
    
    # 单个文献评估
    assessment = await evaluator.evaluate_literature_quality(sample_documents[0])
    print(f"文献评估结果: {assessment.quality_grade} (评分: {assessment.overall_score})")
    print(f"推荐意见: {assessment.recommendation}")
    
    # 批量评估
    assessments = await evaluator.batch_evaluate_literature(sample_documents)
    
    # 生成报告
    report = evaluator.generate_quality_report(assessments)
    print("\n质量评估报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main()) 