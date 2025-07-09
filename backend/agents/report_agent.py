"""
报告生成Agent - 负责将各模块成果整合为结构化科研报告
扮演AI团队中的"技术写作专家"角色
"""
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from core.base_agent import LLMBaseAgent, AgentConfig
from core.blackboard import Blackboard, BlackboardEvent, EventType


@dataclass
class ReportSection:
    """报告章节数据结构"""
    section_id: str
    title: str
    content: str
    level: int  # 章节级别 1,2,3...
    order: int  # 排序
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ReportTemplate:
    """报告模板数据结构"""
    template_id: str
    name: str
    description: str
    sections: List[str]  # 章节标题列表
    formatting_rules: Dict[str, Any]


class ReportAgent(LLMBaseAgent):
    """
    报告生成Agent - 结构化科研报告生成专家

    职责:
    - 整合各Agent产出的信息
    - 生成结构化的科研报告
    - 处理格式规范和引用标准
    - 确保逻辑连贯性和可读性
    """

    def __init__(self, blackboard: Blackboard, llm_client=None):
        config = AgentConfig(
            name="ReportAgent",
            agent_type="reporter",
            description="报告生成Agent - 技术写作专家",
            subscribed_events=[
                EventType.TASK_COMPLETED,
                EventType.VERIFICATION_REPORT,
                EventType.CRITIQUE_FEEDBACK,
                EventType.EVALUATION_RESULT,
                EventType.MODEL_RESULT
            ],
            max_concurrent_tasks=2
        )
        super().__init__(config, blackboard, llm_client)

        # 报告模板和配置
        self.report_templates: Dict[str, ReportTemplate] = {}
        self.current_reports: Dict[str, Dict[str, Any]] = {}
        self.formatting_rules = {
            "citation_style": "IEEE",
            "max_section_length": 2000,
            "language": "zh-CN",
            "include_figures": True,
            "include_tables": True
        }

    async def _load_prompt_templates(self):
        """加载报告生成模板"""
        self.prompt_templates = {
            "research_report": """
系统：你是专业的科研报告撰写专家，请根据提供的研究成果生成一份结构化的研究报告。

研究信息：
{research_data}

**重要要求**：
1. 必须基于实际提供的研究数据生成具体内容，严禁使用占位符如"发现A"、"主题A"等
2. 如果研究问题涉及具体领域（如质子导体、催化剂等），必须生成该领域的专业内容
3. 所有章节内容必须与用户的具体研究问题相关
4. 引用和发现必须基于实际的研究背景
5. 避免模糊的描述，提供具体的科学内容

请按照以下结构生成报告（JSON格式）：
{{
    "title": "基于实际研究问题的具体标题",
    "research_question": "从研究数据中提取的用户原始问题",
    "executive_summary": {{
        "key_findings": ["具体的科学发现1", "具体的科学发现2", "具体的科学发现3"],
        "innovations": ["具体的创新点1", "具体的创新点2"],
        "recommendations": ["具体的建议1", "具体的建议2"],
        "impact": "基于实际研究内容的预期影响描述"
    }},
    "introduction": {{
        "background": "基于用户问题的具体研究背景",
        "motivation": "针对具体问题的研究动机",
        "objectives": ["具体的研究目标1", "具体的研究目标2"],
        "scope": "明确的研究范围和边界"
    }},
    "literature_review": {{
        "current_state": "该具体领域的当前研究现状",
        "key_references": [
            {{
                "title": "相关的具体文献标题",
                "authors": ["具体作者1", "具体作者2"],
                "year": 2024,
                "contribution": "该文献的具体贡献"
            }}
        ],
        "research_gap": "基于实际分析的研究空白",
        "our_approach": "我们针对具体问题的方法"
    }},
    "methodology": {{
        "research_design": "针对具体问题的研究设计",
        "methods": ["具体方法1", "具体方法2"],
        "data_collection": "具体的数据收集方式",
        "analysis_approach": "具体的分析方法"
    }},
    "results": {{
        "main_findings": [
            {{
                "finding": "具体的研究发现描述",
                "evidence": "支撑该发现的具体证据",
                "significance": "该发现在具体领域的重要性说明"
            }}
        ],
        "data_visualization": [
            {{
                "type": "图表类型",
                "title": "具体的图表标题",
                "description": "图表的具体说明",
                "key_insights": ["具体洞察1", "具体洞察2"]
            }}
        ],
        "statistical_analysis": {{
            "key_metrics": "具体的关键指标",
            "confidence_levels": "具体的置信水平",
            "correlations": "发现的具体相关性"
        }}
    }},
    "discussion": {{
        "interpretation": "基于具体结果的解释",
        "implications": ["具体的理论意义", "具体的实践意义"],
        "limitations": ["具体的局限性1", "具体的局限性2"],
        "future_directions": ["具体的未来方向1", "具体的未来方向2"]
    }},
    "conclusion": {{
        "summary": "基于实际研究的总结",
        "contributions": ["具体贡献1", "具体贡献2"],
        "practical_applications": ["具体应用1", "具体应用2"],
        "final_remarks": "针对研究问题的结语"
    }},
    "references": [
        {{
            "id": "ref1",
            "citation": "具体的完整引用格式"
        }}
    ],
    "appendices": [
        {{
            "title": "具体的附录标题",
            "content": "相关的附录内容"
        }}
    ]
}}

**再次强调**：绝对不要使用"发现A"、"主题A"、"建议1"这样的占位符，所有内容必须基于实际研究数据生成具体的科学内容。
""",

            "markdown_converter": """
系统：将JSON格式的研究报告转换为美观的Markdown格式。

JSON报告：
{json_report}

转换要求：
1. 使用适当的Markdown标记（标题、列表、表格、代码块等）
2. 保持层次结构清晰
3. 突出重要信息（加粗、斜体等）
4. 格式化引用和参考文献
5. 确保可读性和美观性
6. 保持所有具体的科学内容，不要转换为占位符

请生成格式化的Markdown报告，包括：
- 多级标题结构
- 项目符号和编号列表
- 表格（如适用）
- 引用块
- 代码块（如适用）
- 图表占位符和说明
""",

            "section_content": """
系统：为研究报告的特定章节生成具体内容。

章节标题：{section_title}
章节描述：{section_description}
相关数据：{relevant_data}
上下文：{context}
最大长度：{max_length}字符

**重要要求**：
1. 内容必须具体且与章节标题相关
2. 基于提供的相关数据生成真实内容
3. 避免使用占位符或通用描述
4. 如果涉及科学领域，使用专业术语和概念
5. 确保内容的科学准确性和专业性

请生成该章节的具体内容：
""",

            "html_converter": """
系统：将研究报告转换为专业的HTML格式，包含样式。

报告内容：
{report_content}

HTML要求：
1. 使用语义化HTML5标签
2. 包含内联CSS样式
3. 响应式设计考虑
4. 专业的配色方案
5. 清晰的排版布局
6. 保持所有具体内容不变

请生成包含以下特性的HTML：
- 导航目录
- 章节编号
- 图表容器
- 打印友好样式
- 可折叠/展开的章节
""",

            "executive_summary_generator": """
系统：基于完整研究报告生成执行摘要。

完整报告：
{full_report}

摘要要求：
1. 控制在1-2页内容
2. 突出最重要的发现
3. 强调实际价值和影响
4. 提供关键数据支撑
5. 明确的行动建议
6. 基于实际研究内容，避免占位符

请生成包含以下部分的执行摘要：
{{
    "overview": "基于实际研究的项目概述（2-3句话）",
    "key_findings": ["具体发现1（含实际数据）", "具体发现2", "具体发现3"],
    "business_impact": "具体的商业/学术影响",
    "recommendations": [
        {{
            "action": "具体的建议行动",
            "rationale": "基于研究的理由",
            "timeline": "现实的时间框架"
        }}
    ],
    "next_steps": ["具体的下一步1", "具体的下一步2"],
    "conclusion": "基于实际研究的结论（1-2句话）"
}}
"""
        }

    async def _process_event_impl(self, event: BlackboardEvent):
        """处理黑板事件的具体实现"""
        try:
            if event.event_type == EventType.TASK_COMPLETED:
                await self._collect_task_results(event)
            elif event.event_type == EventType.VERIFICATION_REPORT:
                await self._integrate_verification(event)
            elif event.event_type == EventType.CRITIQUE_FEEDBACK:
                await self._integrate_critique(event)
            elif event.event_type == EventType.EVALUATION_RESULT:
                await self._integrate_evaluation(event)
            elif event.event_type == EventType.MODEL_RESULT:
                await self._integrate_model_results(event)

        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")

    async def _collect_task_results(self, event: BlackboardEvent):
        """收集任务完成结果"""
        task_data = event.data
        task_id = task_data.get("task_id")
        
        if not task_id:
            return

        # 获取任务相关的所有信息
        report_id = task_data.get("report_id", "default")
        
        if report_id not in self.current_reports:
            self.current_reports[report_id] = {
                "sections": {},
                "metadata": {},
                "status": "collecting",
                "created_at": datetime.now()
            }

        # 存储任务结果
        self.current_reports[report_id]["sections"][task_id] = {
            "content": task_data.get("result", ""),
            "source": event.source_agent,
            "timestamp": event.timestamp
        }

        self.logger.info(f"收集任务结果: {task_id} from {event.source_agent}")

    async def generate_report(self, report_id: str, template_name: str = "standard") -> str:
        """生成研究报告"""
        self.logger.info(f"开始生成报告: {report_id}, 模板: {template_name}")
        
        try:
            # 获取报告数据
            report_data = self.current_reports.get(report_id, {})
            if not report_data:
                self.logger.warning(f"未找到报告数据: {report_id}")
                return ""
            
            # 生成结构化报告
            structure = await self._generate_report_structure(report_data)
            
            # 生成各部分内容
            sections_content = {}
            for section in structure.get("sections", []):
                content = await self._generate_section_content(section, report_data)
                sections_content[section["id"]] = content
            
            # 整合最终报告
            final_report = await self._integrate_final_report(sections_content, report_data)
            
            # 生成不同格式的报告
            json_report = await self._generate_json_report(report_data)
            markdown_report = await self._convert_to_markdown(json_report)
            html_report = await self._convert_to_html(markdown_report)
            executive_summary = await self._generate_executive_summary(json_report)
            
            # 存储不同格式的报告
            await self._store_reports(report_id, {
                "json": json_report,
                "markdown": markdown_report,
                "html": html_report,
                "executive_summary": executive_summary,
                "full_text": final_report
            })
            
            # 发布报告生成完成事件
            await self._publish_report_generated(report_id, final_report)
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            raise

    async def _generate_report_structure(self, report_data: Dict) -> Dict:
        """生成报告结构"""
        collected_info = self._extract_information(report_data)
        
        prompt = self.format_prompt(
            "research_report",
            research_data=json.dumps(collected_info, ensure_ascii=False, indent=2)
        )
        
        response = await self.call_llm(
            prompt,
            temperature=0.3,
            max_tokens=8000,
            response_format="json"
        )
        
        return json.loads(response)

    async def _generate_section_content(self, section: Dict, report_data: Dict) -> str:
        """生成章节内容"""
        relevant_data = self._extract_relevant_data(section, report_data)
        
        prompt = self.format_prompt(
            "section_content",
            section_title=section["title"],
            section_description=section.get("description", ""),
            relevant_data=json.dumps(relevant_data, ensure_ascii=False),
            context=json.dumps(report_data.get("metadata", {}), ensure_ascii=False),
            max_length=self.formatting_rules["max_section_length"]
        )
        
        return await self.call_llm(prompt)

    async def _integrate_final_report(self, sections_content: Dict, report_data: Dict) -> str:
        """整合最终报告"""
        prompt = self.format_prompt(
            "research_report",
            research_data=json.dumps(sections_content, ensure_ascii=False, indent=2)
        )
        
        response = await self.call_llm(
            prompt,
            temperature=0.3,
            max_tokens=8000,
            response_format="json"
        )
        
        return json.loads(response)

    def _extract_information(self, report_data: Dict) -> Dict:
        """提取报告相关信息"""
        info = {}
        
        # 从各个Agent的结果中提取信息
        for section_id, section_data in report_data.get("sections", {}).items():
            source = section_data.get("source", "")
            content = section_data.get("content", "")
            
            if source not in info:
                info[source] = []
            info[source].append(content)
        
        return info

    def _extract_relevant_data(self, section: Dict, report_data: Dict) -> Dict:
        """提取章节相关数据"""
        section_title = section["title"].lower()
        relevant_data = {}
        
        # 根据章节标题匹配相关数据
        if "方法" in section_title or "实验" in section_title:
            relevant_data["experiment_data"] = report_data.get("model_results", [])
        elif "结果" in section_title or "分析" in section_title:
            relevant_data["results"] = report_data.get("evaluation", {})
        elif "验证" in section_title:
            relevant_data["verification"] = report_data.get("verification", [])
        
        return relevant_data

    async def _generate_json_report(self, report_data: Dict) -> Dict:
        """生成JSON格式的结构化报告"""
        prompt = self.format_prompt(
            "research_report",
            research_data=json.dumps(report_data, ensure_ascii=False, indent=2)
        )
        
        response = await self.call_llm(
            prompt,
            temperature=0.3,
            max_tokens=8000,
            response_format="json"
        )
        
        return json.loads(response)

    async def _convert_to_markdown(self, json_report: Dict) -> str:
        """将JSON报告转换为Markdown格式"""
        prompt = self.format_prompt(
            "markdown_converter",
            json_report=json.dumps(json_report, ensure_ascii=False, indent=2)
        )
        
        markdown_content = await self.call_llm(
            prompt,
            temperature=0.2,
            max_tokens=6000
        )
        
        return markdown_content

    async def _convert_to_html(self, markdown_content: str) -> str:
        """将Markdown转换为HTML格式"""
        # 首先使用markdown库转换基础HTML
        import markdown
        html_body = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'toc', 'tables']
        )
        
        # 然后使用LLM增强HTML样式
        prompt = self.format_prompt(
            "html_converter",
            report_content=html_body
        )
        
        enhanced_html = await self.call_llm(
            prompt,
            temperature=0.2,
            max_tokens=8000
        )
        
        return enhanced_html

    async def _generate_executive_summary(self, json_report: Dict) -> Dict:
        """生成执行摘要"""
        prompt = self.format_prompt(
            "executive_summary_generator",
            full_report=json.dumps(json_report, ensure_ascii=False, indent=2)
        )
        
        response = await self.call_llm(
            prompt,
            temperature=0.3,
            max_tokens=2000,
            response_format="json"
        )
        
        return json.loads(response)

    async def _store_reports(self, report_id: str, reports: Dict[str, Any]):
        """存储不同格式的报告"""
        for format_type, content in reports.items():
            await self.blackboard.store_data(
                f"report_{report_id}_{format_type}",
                {
                    "content": content,
                    "format": format_type,
                    "generated_at": datetime.now().isoformat(),
                    "generator": self.config.name
                }
            )
        
        # 存储报告元数据
        await self.blackboard.store_data(
            f"report_{report_id}_metadata",
            {
                "formats_available": list(reports.keys()),
                "generated_at": datetime.now().isoformat(),
                "report_id": report_id,
                "status": "completed"
            }
        )

    async def _publish_report_generated(self, report_id: str, report_content: str):
        """发布报告生成完成事件"""
        event = BlackboardEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.REPORT_GENERATED,
            source_agent=self.config.name,
            data={
                "report_id": report_id,
                "content": report_content,
                "word_count": len(report_content),
                "generated_at": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        
        await self.blackboard.publish_event(event)
        self.logger.info(f"报告生成完成: {report_id}")
