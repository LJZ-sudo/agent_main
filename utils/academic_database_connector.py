"""
学术数据库连接器
连接真实的学术数据库API，获取最新的研究文献
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import xml.etree.ElementTree as ET
import urllib.parse

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """数据库类型枚举"""
    PUBMED = "pubmed"
    ARXIV = "arxiv"
    IEEE_XPLORE = "ieee_xplore"
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"
    GOOGLE_SCHOLAR = "google_scholar"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    CROSSREF = "crossref"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = 10  # 每秒请求数限制
    timeout: int = 30
    max_retries: int = 3
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class SearchQuery:
    """搜索查询"""
    keywords: List[str]
    title_keywords: Optional[List[str]] = None
    author: Optional[str] = None
    journal: Optional[str] = None
    year_range: Optional[Tuple[int, int]] = None
    max_results: int = 100
    sort_by: str = "relevance"  # relevance, date, citations
    field_filter: Optional[str] = None


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
    doi: str = ""
    url: str = ""
    citation_count: int = 0
    journal_impact_factor: float = 0.0
    publication_date: Optional[datetime] = None
    source_database: str = ""
    full_text_url: str = ""
    pdf_url: str = ""
    affiliation: str = ""
    funding_info: str = ""
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AcademicDatabaseConnector:
    """
    学术数据库连接器
    
    支持的数据库：
    - PubMed (生物医学文献)
    - arXiv (预印本)
    - IEEE Xplore (工程技术)
    - Semantic Scholar (跨学科)
    - CrossRef (DOI数据库)
    """

    def __init__(self):
        self.databases = self._initialize_databases()
        self.session = None
        self.rate_limiters = {}

    def _initialize_databases(self) -> Dict[DatabaseType, DatabaseConfig]:
        """初始化数据库配置"""
        return {
            DatabaseType.PUBMED: DatabaseConfig(
                name="PubMed",
                base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                rate_limit=3,  # PubMed API限制
                headers={"User-Agent": "ResearchAgent/1.0"}
            ),
            DatabaseType.ARXIV: DatabaseConfig(
                name="arXiv",
                base_url="http://export.arxiv.org/api/",
                rate_limit=1,  # arXiv API限制较严
                headers={"User-Agent": "ResearchAgent/1.0"}
            ),
            DatabaseType.SEMANTIC_SCHOLAR: DatabaseConfig(
                name="Semantic Scholar",
                base_url="https://api.semanticscholar.org/graph/v1/",
                rate_limit=100,  # 较宽松的限制
                headers={
                    "User-Agent": "ResearchAgent/1.0",
                    "x-api-key": ""  # 需要申请API密钥
                }
            ),
            DatabaseType.CROSSREF: DatabaseConfig(
                name="CrossRef",
                base_url="https://api.crossref.org/",
                rate_limit=50,
                headers={"User-Agent": "ResearchAgent/1.0 (mailto:your-email@example.com)"}
            ),
            DatabaseType.IEEE_XPLORE: DatabaseConfig(
                name="IEEE Xplore",
                base_url="https://ieeexploreapi.ieee.org/api/v1/",
                rate_limit=10,
                headers={"User-Agent": "ResearchAgent/1.0"}
                # 需要API密钥
            )
        }

    async def initialize(self):
        """初始化连接器"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        
        # 初始化速率限制器
        for db_type in self.databases:
            self.rate_limiters[db_type] = []
        
        logger.info("学术数据库连接器初始化完成")

    async def search_literature(
        self,
        query: SearchQuery,
        databases: List[DatabaseType] = None,
        parallel_search: bool = True
    ) -> Dict[DatabaseType, List[LiteratureDocument]]:
        """
        搜索文献
        
        Args:
            query: 搜索查询
            databases: 要搜索的数据库列表
            parallel_search: 是否并行搜索
            
        Returns:
            Dict[DatabaseType, List[LiteratureDocument]]: 各数据库的搜索结果
        """
        if not self.session:
            await self.initialize()
        
        if databases is None:
            databases = [DatabaseType.PUBMED, DatabaseType.ARXIV, DatabaseType.SEMANTIC_SCHOLAR]
        
        logger.info(f"开始搜索文献: {query.keywords} (数据库: {[db.value for db in databases]})")
        
        results = {}
        
        if parallel_search:
            # 并行搜索
            tasks = []
            for db_type in databases:
                task = asyncio.create_task(
                    self._search_single_database(db_type, query),
                    name=f"search_{db_type.value}"
                )
                tasks.append((db_type, task))
            
            # 等待所有搜索完成
            for db_type, task in tasks:
                try:
                    documents = await task
                    results[db_type] = documents
                    logger.info(f"{db_type.value} 搜索完成: {len(documents)} 篇文献")
                except Exception as e:
                    logger.error(f"{db_type.value} 搜索失败: {e}")
                    results[db_type] = []
        else:
            # 串行搜索
            for db_type in databases:
                try:
                    documents = await self._search_single_database(db_type, query)
                    results[db_type] = documents
                    logger.info(f"{db_type.value} 搜索完成: {len(documents)} 篇文献")
                except Exception as e:
                    logger.error(f"{db_type.value} 搜索失败: {e}")
                    results[db_type] = []
        
        total_documents = sum(len(docs) for docs in results.values())
        logger.info(f"文献搜索完成，共找到 {total_documents} 篇文献")
        
        return results

    async def _search_single_database(
        self,
        db_type: DatabaseType,
        query: SearchQuery
    ) -> List[LiteratureDocument]:
        """搜索单个数据库"""
        try:
            # 检查速率限制
            await self._check_rate_limit(db_type)
            
            # 根据数据库类型调用相应的搜索方法
            if db_type == DatabaseType.PUBMED:
                return await self._search_pubmed(query)
            elif db_type == DatabaseType.ARXIV:
                return await self._search_arxiv(query)
            elif db_type == DatabaseType.SEMANTIC_SCHOLAR:
                return await self._search_semantic_scholar(query)
            elif db_type == DatabaseType.CROSSREF:
                return await self._search_crossref(query)
            elif db_type == DatabaseType.IEEE_XPLORE:
                return await self._search_ieee_xplore(query)
            else:
                logger.warning(f"不支持的数据库类型: {db_type}")
                return []
                
        except Exception as e:
            logger.error(f"搜索 {db_type.value} 时出错: {e}")
            return []

    async def _search_pubmed(self, query: SearchQuery) -> List[LiteratureDocument]:
        """搜索PubMed数据库"""
        config = self.databases[DatabaseType.PUBMED]
        
        # 构建搜索查询
        search_terms = []
        for keyword in query.keywords:
            search_terms.append(f'"{keyword}"[Title/Abstract]')
        
        if query.author:
            search_terms.append(f'"{query.author}"[Author]')
        
        if query.year_range:
            start_year, end_year = query.year_range
            search_terms.append(f"{start_year}:{end_year}[Publication Date]")
        
        search_query = " AND ".join(search_terms)
        
        # 第一步：搜索获取ID列表
        search_url = f"{config.base_url}esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": search_query,
            "retmax": min(query.max_results, 1000),
            "retmode": "json",
            "sort": "relevance" if query.sort_by == "relevance" else "pub_date"
        }
        
        async with self.session.get(search_url, params=search_params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"PubMed搜索请求失败: {response.status}")
            
            search_data = await response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            return []
        
        # 第二步：获取详细信息
        fetch_url = f"{config.base_url}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list[:query.max_results]),
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        await self._check_rate_limit(DatabaseType.PUBMED)  # 再次检查速率限制
        
        async with self.session.get(fetch_url, params=fetch_params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"PubMed获取详情失败: {response.status}")
            
            xml_content = await response.text()
            return self._parse_pubmed_xml(xml_content)

    async def _search_arxiv(self, query: SearchQuery) -> List[LiteratureDocument]:
        """搜索arXiv数据库"""
        config = self.databases[DatabaseType.ARXIV]
        
        # 构建搜索查询
        search_terms = []
        for keyword in query.keywords:
            search_terms.append(f'all:"{keyword}"')
        
        if query.title_keywords:
            for title_keyword in query.title_keywords:
                search_terms.append(f'ti:"{title_keyword}"')
        
        if query.author:
            search_terms.append(f'au:"{query.author}"')
        
        search_query = " AND ".join(search_terms)
        
        # arXiv API参数
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(query.max_results, 1000),
            "sortBy": "relevance" if query.sort_by == "relevance" else "submittedDate",
            "sortOrder": "descending"
        }
        
        search_url = f"{config.base_url}query"
        
        async with self.session.get(search_url, params=params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"arXiv搜索请求失败: {response.status}")
            
            xml_content = await response.text()
            return self._parse_arxiv_xml(xml_content)

    async def _search_semantic_scholar(self, query: SearchQuery) -> List[LiteratureDocument]:
        """搜索Semantic Scholar数据库"""
        config = self.databases[DatabaseType.SEMANTIC_SCHOLAR]
        
        # 构建搜索查询
        search_query = " ".join(query.keywords)
        
        # Semantic Scholar API参数
        params = {
            "query": search_query,
            "limit": min(query.max_results, 100),
            "fields": "paperId,title,authors,journal,year,abstract,citationCount,url,venue,publicationDate"
        }
        
        if query.year_range:
            params["year"] = f"{query.year_range[0]}-{query.year_range[1]}"
        
        search_url = f"{config.base_url}paper/search"
        
        async with self.session.get(search_url, params=params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"Semantic Scholar搜索请求失败: {response.status}")
            
            data = await response.json()
            return self._parse_semantic_scholar_json(data)

    async def _search_crossref(self, query: SearchQuery) -> List[LiteratureDocument]:
        """搜索CrossRef数据库"""
        config = self.databases[DatabaseType.CROSSREF]
        
        # 构建搜索查询
        search_query = " ".join(query.keywords)
        
        params = {
            "query": search_query,
            "rows": min(query.max_results, 1000),
            "sort": "relevance" if query.sort_by == "relevance" else "published"
        }
        
        if query.year_range:
            params["filter"] = f"from-pub-date:{query.year_range[0]},until-pub-date:{query.year_range[1]}"
        
        search_url = f"{config.base_url}works"
        
        async with self.session.get(search_url, params=params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"CrossRef搜索请求失败: {response.status}")
            
            data = await response.json()
            return self._parse_crossref_json(data)

    async def _search_ieee_xplore(self, query: SearchQuery) -> List[LiteratureDocument]:
        """搜索IEEE Xplore数据库（需要API密钥）"""
        config = self.databases[DatabaseType.IEEE_XPLORE]
        
        # 注意：这需要有效的IEEE API密钥
        if not config.api_key:
            logger.warning("IEEE Xplore需要API密钥，跳过搜索")
            return []
        
        # 构建搜索查询
        search_query = " AND ".join(f'"{keyword}"' for keyword in query.keywords)
        
        params = {
            "querytext": search_query,
            "max_records": min(query.max_results, 200),
            "start_record": 1,
            "sort_field": "relevance" if query.sort_by == "relevance" else "publication_year",
            "sort_order": "desc",
            "apikey": config.api_key
        }
        
        search_url = f"{config.base_url}search"
        
        async with self.session.get(search_url, params=params, headers=config.headers) as response:
            if response.status != 200:
                raise Exception(f"IEEE Xplore搜索请求失败: {response.status}")
            
            data = await response.json()
            return self._parse_ieee_json(data)

    def _parse_pubmed_xml(self, xml_content: str) -> List[LiteratureDocument]:
        """解析PubMed XML响应"""
        documents = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    # 提取基本信息
                    medline_citation = article.find("MedlineCitation")
                    pmid = medline_citation.find("PMID").text if medline_citation.find("PMID") is not None else ""
                    
                    article_elem = medline_citation.find("Article")
                    if article_elem is None:
                        continue
                    
                    # 标题
                    title_elem = article_elem.find("ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    # 作者
                    authors = []
                    author_list = article_elem.find("AuthorList")
                    if author_list is not None:
                        for author in author_list.findall("Author"):
                            last_name = author.find("LastName")
                            first_name = author.find("ForeName")
                            if last_name is not None and first_name is not None:
                                authors.append(f"{last_name.text}, {first_name.text}")
                    
                    # 期刊
                    journal_elem = article_elem.find("Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""
                    
                    # 年份
                    year_elem = article_elem.find("Journal/JournalIssue/PubDate/Year")
                    year = int(year_elem.text) if year_elem is not None else datetime.now().year
                    
                    # 摘要
                    abstract_elem = article_elem.find("Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None else ""
                    
                    # 关键词
                    keywords = []
                    keyword_list = medline_citation.find("KeywordList")
                    if keyword_list is not None:
                        for keyword in keyword_list.findall("Keyword"):
                            if keyword.text:
                                keywords.append(keyword.text)
                    
                    # DOI
                    doi = ""
                    for article_id in article_elem.findall("ELocationID"):
                        if article_id.get("EIdType") == "doi":
                            doi = article_id.text
                            break
                    
                    document = LiteratureDocument(
                        doc_id=f"pubmed_{pmid}",
                        title=title,
                        authors=authors,
                        journal=journal,
                        year=year,
                        abstract=abstract,
                        keywords=keywords,
                        doi=doi,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source_database="PubMed"
                    )
                    
                    documents.append(document)
                    
                except Exception as e:
                    logger.warning(f"解析PubMed文章时出错: {e}")
                    continue
        
        except ET.ParseError as e:
            logger.error(f"解析PubMed XML时出错: {e}")
        
        return documents

    def _parse_arxiv_xml(self, xml_content: str) -> List[LiteratureDocument]:
        """解析arXiv XML响应"""
        documents = []
        
        try:
            # 移除命名空间前缀以简化解析
            xml_content = xml_content.replace('xmlns="http://www.w3.org/2005/Atom"', '')
            xml_content = xml_content.replace('xmlns:arxiv="http://arxiv.org/schemas/atom"', '')
            
            root = ET.fromstring(xml_content)
            
            for entry in root.findall("entry"):
                try:
                    # ID
                    id_elem = entry.find("id")
                    arxiv_id = id_elem.text.split("/")[-1] if id_elem is not None else ""
                    
                    # 标题
                    title_elem = entry.find("title")
                    title = title_elem.text.strip() if title_elem is not None else ""
                    
                    # 作者
                    authors = []
                    for author in entry.findall("author"):
                        name_elem = author.find("name")
                        if name_elem is not None:
                            authors.append(name_elem.text)
                    
                    # 摘要
                    summary_elem = entry.find("summary")
                    abstract = summary_elem.text.strip() if summary_elem is not None else ""
                    
                    # 发表日期
                    published_elem = entry.find("published")
                    year = datetime.now().year
                    if published_elem is not None:
                        try:
                            pub_date = datetime.fromisoformat(published_elem.text.replace('Z', '+00:00'))
                            year = pub_date.year
                        except:
                            pass
                    
                    # 分类作为关键词
                    keywords = []
                    for category in entry.findall("category"):
                        term = category.get("term")
                        if term:
                            keywords.append(term)
                    
                    # URL
                    url = id_elem.text if id_elem is not None else ""
                    pdf_url = url.replace("/abs/", "/pdf/") + ".pdf" if url else ""
                    
                    document = LiteratureDocument(
                        doc_id=f"arxiv_{arxiv_id}",
                        title=title,
                        authors=authors,
                        journal="arXiv preprint",
                        year=year,
                        abstract=abstract,
                        keywords=keywords,
                        url=url,
                        pdf_url=pdf_url,
                        source_database="arXiv"
                    )
                    
                    documents.append(document)
                    
                except Exception as e:
                    logger.warning(f"解析arXiv条目时出错: {e}")
                    continue
        
        except ET.ParseError as e:
            logger.error(f"解析arXiv XML时出错: {e}")
        
        return documents

    def _parse_semantic_scholar_json(self, data: Dict[str, Any]) -> List[LiteratureDocument]:
        """解析Semantic Scholar JSON响应"""
        documents = []
        
        papers = data.get("data", [])
        
        for paper in papers:
            try:
                # 基本信息
                paper_id = paper.get("paperId", "")
                title = paper.get("title", "")
                year = paper.get("year", datetime.now().year)
                abstract = paper.get("abstract", "")
                citation_count = paper.get("citationCount", 0)
                url = paper.get("url", "")
                
                # 作者
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name", "")
                    if name:
                        authors.append(name)
                
                # 期刊/会议
                journal = paper.get("journal", {}).get("name", "") or paper.get("venue", "")
                
                # 发表日期
                pub_date = paper.get("publicationDate")
                if pub_date and year is None:
                    try:
                        year = datetime.fromisoformat(pub_date).year
                    except:
                        year = datetime.now().year
                
                document = LiteratureDocument(
                    doc_id=f"s2_{paper_id}",
                    title=title,
                    authors=authors,
                    journal=journal,
                    year=year or datetime.now().year,
                    abstract=abstract,
                    keywords=[],  # Semantic Scholar不直接提供关键词
                    url=url,
                    citation_count=citation_count,
                    source_database="Semantic Scholar"
                )
                
                documents.append(document)
                
            except Exception as e:
                logger.warning(f"解析Semantic Scholar条目时出错: {e}")
                continue
        
        return documents

    def _parse_crossref_json(self, data: Dict[str, Any]) -> List[LiteratureDocument]:
        """解析CrossRef JSON响应"""
        documents = []
        
        items = data.get("message", {}).get("items", [])
        
        for item in items:
            try:
                # DOI
                doi = item.get("DOI", "")
                
                # 标题
                titles = item.get("title", [])
                title = titles[0] if titles else ""
                
                # 作者
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if family:
                        full_name = f"{family}, {given}" if given else family
                        authors.append(full_name)
                
                # 期刊
                container_title = item.get("container-title", [])
                journal = container_title[0] if container_title else ""
                
                # 年份
                published = item.get("published-print") or item.get("published-online")
                year = datetime.now().year
                if published and "date-parts" in published:
                    date_parts = published["date-parts"][0]
                    if date_parts:
                        year = date_parts[0]
                
                # 摘要（CrossRef通常不提供）
                abstract = item.get("abstract", "")
                
                # URL
                url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
                
                document = LiteratureDocument(
                    doc_id=f"crossref_{doi.replace('/', '_')}",
                    title=title,
                    authors=authors,
                    journal=journal,
                    year=year,
                    abstract=abstract,
                    keywords=[],
                    doi=doi,
                    url=url,
                    source_database="CrossRef"
                )
                
                documents.append(document)
                
            except Exception as e:
                logger.warning(f"解析CrossRef条目时出错: {e}")
                continue
        
        return documents

    def _parse_ieee_json(self, data: Dict[str, Any]) -> List[LiteratureDocument]:
        """解析IEEE Xplore JSON响应"""
        documents = []
        
        articles = data.get("articles", [])
        
        for article in articles:
            try:
                # 基本信息
                doc_id = str(article.get("article_number", ""))
                title = article.get("title", "")
                abstract = article.get("abstract", "")
                year = article.get("publication_year", datetime.now().year)
                
                # 作者
                authors = []
                for author in article.get("authors", {}).get("authors", []):
                    full_name = author.get("full_name", "")
                    if full_name:
                        authors.append(full_name)
                
                # 期刊/会议
                journal = article.get("publication_title", "")
                
                # DOI
                doi = article.get("doi", "")
                
                # URL
                url = f"https://ieeexplore.ieee.org/document/{doc_id}" if doc_id else ""
                
                # 关键词
                keywords = []
                index_terms = article.get("index_terms", {})
                for term_type in ["ieee_terms", "author_terms"]:
                    terms = index_terms.get(term_type, {}).get("terms", [])
                    keywords.extend(terms)
                
                document = LiteratureDocument(
                    doc_id=f"ieee_{doc_id}",
                    title=title,
                    authors=authors,
                    journal=journal,
                    year=year,
                    abstract=abstract,
                    keywords=keywords,
                    doi=doi,
                    url=url,
                    source_database="IEEE Xplore"
                )
                
                documents.append(document)
                
            except Exception as e:
                logger.warning(f"解析IEEE条目时出错: {e}")
                continue
        
        return documents

    async def _check_rate_limit(self, db_type: DatabaseType):
        """检查并执行速率限制"""
        config = self.databases[db_type]
        now = time.time()
        
        # 清理过期的请求记录
        self.rate_limiters[db_type] = [
            req_time for req_time in self.rate_limiters[db_type]
            if now - req_time < 1.0  # 保留1秒内的请求
        ]
        
        # 检查是否超过速率限制
        if len(self.rate_limiters[db_type]) >= config.rate_limit:
            sleep_time = 1.0 - (now - self.rate_limiters[db_type][0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 记录当前请求
        self.rate_limiters[db_type].append(now)

    async def get_paper_details(self, doi: str, database: DatabaseType = None) -> Optional[LiteratureDocument]:
        """根据DOI获取论文详细信息"""
        if not doi:
            return None
        
        # 优先使用CrossRef获取详细信息
        if database is None or database == DatabaseType.CROSSREF:
            try:
                config = self.databases[DatabaseType.CROSSREF]
                url = f"{config.base_url}works/{doi}"
                
                await self._check_rate_limit(DatabaseType.CROSSREF)
                
                async with self.session.get(url, headers=config.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        documents = self._parse_crossref_json({"message": {"items": [data["message"]]}})
                        return documents[0] if documents else None
            except Exception as e:
                logger.error(f"获取DOI {doi} 详细信息失败: {e}")
        
        return None

    async def get_citation_network(self, paper_id: str, depth: int = 1) -> Dict[str, Any]:
        """获取论文引用网络"""
        # 这是一个高级功能，需要更复杂的API调用
        # 目前返回简化的结构
        return {
            "center_paper": paper_id,
            "citations": [],
            "references": [],
            "network_depth": depth
        }

    def merge_search_results(
        self,
        results: Dict[DatabaseType, List[LiteratureDocument]]
    ) -> List[LiteratureDocument]:
        """合并多个数据库的搜索结果，去除重复"""
        all_documents = []
        seen_titles = set()
        seen_dois = set()
        
        # 按数据库优先级排序
        priority_order = [
            DatabaseType.PUBMED,
            DatabaseType.SEMANTIC_SCHOLAR,
            DatabaseType.IEEE_XPLORE,
            DatabaseType.CROSSREF,
            DatabaseType.ARXIV
        ]
        
        for db_type in priority_order:
            if db_type in results:
                for doc in results[db_type]:
                    # 去重逻辑
                    is_duplicate = False
                    
                    # 基于DOI去重
                    if doc.doi and doc.doi in seen_dois:
                        is_duplicate = True
                    
                    # 基于标题去重
                    if not is_duplicate and doc.title:
                        title_normalized = doc.title.lower().strip()
                        if title_normalized in seen_titles:
                            is_duplicate = True
                    
                    if not is_duplicate:
                        all_documents.append(doc)
                        if doc.doi:
                            seen_dois.add(doc.doi)
                        if doc.title:
                            seen_titles.add(doc.title.lower().strip())
        
        logger.info(f"合并结果：共 {len(all_documents)} 篇去重后的文献")
        return all_documents

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
        logger.info("学术数据库连接器已关闭")


# 使用示例
async def main():
    """示例用法"""
    connector = AcademicDatabaseConnector()
    
    try:
        # 创建搜索查询
        query = SearchQuery(
            keywords=["machine learning", "materials science"],
            year_range=(2020, 2024),
            max_results=50,
            sort_by="relevance"
        )
        
        # 搜索多个数据库
        results = await connector.search_literature(
            query,
            databases=[DatabaseType.PUBMED, DatabaseType.ARXIV, DatabaseType.SEMANTIC_SCHOLAR]
        )
        
        # 合并结果
        merged_documents = connector.merge_search_results(results)
        
        print(f"搜索完成，共找到 {len(merged_documents)} 篇文献")
        
        # 显示前几篇文献
        for i, doc in enumerate(merged_documents[:5]):
            print(f"\n{i+1}. {doc.title}")
            print(f"   作者: {', '.join(doc.authors[:3])}{'...' if len(doc.authors) > 3 else ''}")
            print(f"   期刊: {doc.journal} ({doc.year})")
            print(f"   来源: {doc.source_database}")
            if doc.citation_count > 0:
                print(f"   引用数: {doc.citation_count}")
    
    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main()) 