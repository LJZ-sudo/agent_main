#!/usr/bin/env python3
"""
文献搜索模块 - 支持多个学术数据库的文献检索
"""
import asyncio
import aiohttp
import httpx
import json
import time
import feedparser
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote, urlencode
from loguru import logger
import re
from datetime import datetime, timedelta


@dataclass
class LiteratureSearchResult:
    """文献搜索结果"""
    title: str
    authors: List[str]
    abstract: str
    publication_date: str
    journal: str
    doi: Optional[str] = None
    url: Optional[str] = None
    keywords: List[str] = None
    citation_count: int = 0
    quality_score: float = 0.0
    source_database: str = ""


@dataclass
class SearchQuery:
    """搜索查询"""
    keywords: List[str]
    title_keywords: Optional[List[str]] = None
    author: Optional[str] = None
    journal: Optional[str] = None
    year_range: Optional[tuple] = None
    max_results: int = 50
    language: str = "en"


@dataclass
class APIUsageStats:
    """API使用统计"""
    api_name: str
    requests_count: int = 0
    cost_estimate: float = 0.0
    last_request_time: Optional[datetime] = None
    error_count: int = 0
    daily_limit_reached: bool = False


class LiteratureSearchEngine:
    """增强的文献搜索引擎 - 支持多个API和费用监控"""
    
    def __init__(self, config=None):
        self.config = config
        self.search_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "total_results": 0,
            "average_response_time": 0.0
        }
        self.response_times = []
        
        # API使用统计
        self.api_usage = {
            "serpapi": APIUsageStats("SerpApi"),
            "searchapi": APIUsageStats("SearchApi"),
            "arxiv": APIUsageStats("arXiv"),
            "semantic_scholar": APIUsageStats("Semantic Scholar"),
            "pubmed": APIUsageStats("PubMed"),
            "crossref": APIUsageStats("CrossRef")
        }
        
        # API定价（每1000次请求的估计费用）
        self.api_pricing = {
            "serpapi": 5.0,  # SerpApi大约$5/1000次
            "searchapi": 4.0,  # SearchApi大约$4/1000次
            "arxiv": 0.0,  # 免费
            "semantic_scholar": 0.0,  # 免费
            "pubmed": 0.0,  # 免费
            "crossref": 0.0  # 免费
        }
        
        # 当日使用统计
        self.daily_cost = 0.0
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_stats_if_needed(self):
        """如果是新的一天，重置每日统计"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_cost = 0.0
            self.last_reset_date = today
            for api_stat in self.api_usage.values():
                api_stat.daily_limit_reached = False
            logger.info("每日API使用统计已重置")
    
    def _check_api_cost_limit(self, api_name: str) -> bool:
        """检查API费用是否超限"""
        self._reset_daily_stats_if_needed()
        
        if not self.config or not self.config.api_cost_monitoring:
            return True
        
        estimated_cost = self.api_pricing.get(api_name, 0.0) / 1000
        
        if self.daily_cost + estimated_cost > self.config.daily_cost_limit:
            logger.warning(f"⚠️ API费用即将超过每日限制: {self.daily_cost:.2f}/${self.config.daily_cost_limit}")
            self.api_usage[api_name].daily_limit_reached = True
            return False
        
        if (self.daily_cost + estimated_cost) / self.config.daily_cost_limit > self.config.cost_alert_threshold:
            logger.warning(f"⚠️ API费用已达警戒线: {(self.daily_cost / self.config.daily_cost_limit * 100):.1f}%")
        
        return True
    
    def _record_api_usage(self, api_name: str, success: bool = True):
        """记录API使用情况"""
        if api_name in self.api_usage:
            self.api_usage[api_name].requests_count += 1
            self.api_usage[api_name].last_request_time = datetime.now()
            
            if success:
                cost = self.api_pricing.get(api_name, 0.0) / 1000
                self.api_usage[api_name].cost_estimate += cost
                self.daily_cost += cost
                
                if self.config and self.config.api_usage_log_enabled:
                    logger.info(f"📊 API使用: {api_name}, 今日费用: ${self.daily_cost:.4f}")
            else:
                self.api_usage[api_name].error_count += 1
    
    def _select_optimal_api(self, query: SearchQuery) -> str:
        """智能选择最优API"""
        if not self.config:
            return "arxiv"  # 默认使用免费API
        
        strategy = getattr(self.config, 'search_strategy', 'intelligent')
        
        if strategy == "free_first":
            # 优先使用免费API
            for api in ["arxiv", "semantic_scholar", "pubmed", "crossref"]:
                if not self.api_usage[api].daily_limit_reached:
                    return api
        
        elif strategy == "quality_first":
            # 优先使用高质量付费API
            if self._check_api_cost_limit("searchapi") and not self.api_usage["searchapi"].daily_limit_reached:
                return "searchapi"
            elif self._check_api_cost_limit("serpapi") and not self.api_usage["serpapi"].daily_limit_reached:
                return "serpapi"
        
        elif strategy == "intelligent":
            # 智能选择：根据查询类型和API可用性
            academic_keywords = ["machine learning", "deep learning", "AI", "neural network", "algorithm"]
            is_academic = any(kw.lower() in " ".join(query.keywords).lower() for kw in academic_keywords)
            
            if is_academic:
                # 学术查询优先使用免费的学术数据库
                for api in ["arxiv", "semantic_scholar"]:
                    if not self.api_usage[api].daily_limit_reached:
                        return api
            
            # 其他查询可以使用付费API
            if self._check_api_cost_limit("searchapi"):
                return "searchapi"
        
        # 回退到免费API
        return "arxiv"

    async def search_serpapi_google_scholar(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """使用SerpApi搜索Google Scholar"""
        if not self.config or not getattr(self.config, 'serpapi_key', None):
            logger.warning("SerpApi密钥未配置，跳过搜索")
            return []
        
        if not self._check_api_cost_limit("serpapi"):
            logger.warning("SerpApi已达费用限制，跳过搜索")
            return []
        
        logger.info(f"✨ 使用SerpApi搜索Google Scholar: {query.keywords}")
        start_time = time.time()
        
        try:
            search_terms = " ".join(query.keywords)
            
            params = {
                'engine': 'google_scholar',
                'q': search_terms,
                'api_key': self.config.serpapi_key,
                'num': min(query.max_results, 20),  # SerpApi限制
                'hl': 'en'
            }
            
            if query.year_range:
                start_year, end_year = query.year_range
                params['as_ylo'] = start_year
                params['as_yhi'] = end_year
            
            url = f"https://serpapi.com/search?{urlencode(params)}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_serpapi_response(data)
                    
                    self._record_api_usage("serpapi", True)
                    response_time = time.time() - start_time
                    self._update_stats(len(results), response_time, True)
                    
                    logger.info(f"✅ SerpApi搜索成功: {len(results)}篇文献, 耗时{response_time:.2f}s")
                    return results
                else:
                    logger.error(f"❌ SerpApi搜索失败: HTTP {response.status_code}")
                    if response.status_code == 401:
                        logger.error("SerpApi API密钥无效或余额不足")
                    self._record_api_usage("serpapi", False)
                    return []
        
        except Exception as e:
            logger.error(f"❌ SerpApi搜索异常: {e}")
            self._record_api_usage("serpapi", False)
            return []

    async def search_searchapi_google_scholar(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """使用SearchApi搜索Google Scholar"""
        if not self.config or not getattr(self.config, 'searchapi_key', None):
            logger.warning("SearchApi密钥未配置，跳过搜索")
            return []
        
        if not self._check_api_cost_limit("searchapi"):
            logger.warning("SearchApi已达费用限制，跳过搜索")
            return []
        
        logger.info(f"✨ 使用SearchApi搜索Google Scholar: {query.keywords}")
        start_time = time.time()
        
        try:
            search_terms = " ".join(query.keywords)
            
            params = {
                'engine': 'google_scholar',
                'q': search_terms,
                'api_key': self.config.searchapi_key,
                'num': min(query.max_results, 20),  # SearchApi限制
                'hl': 'en'
            }
            
            if query.year_range:
                start_year, end_year = query.year_range
                params['as_ylo'] = start_year
                params['as_yhi'] = end_year
            
            url = f"https://www.searchapi.io/api/v1/search?{urlencode(params)}"
            
            headers = {
                'Authorization': f'Bearer {self.config.searchapi_key}',
                'Content-Type': 'application/json'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_searchapi_response(data)
                    
                    self._record_api_usage("searchapi", True)
                    response_time = time.time() - start_time
                    self._update_stats(len(results), response_time, True)
                    
                    logger.info(f"✅ SearchApi搜索成功: {len(results)}篇文献, 耗时{response_time:.2f}s")
                    return results
                else:
                    logger.error(f"❌ SearchApi搜索失败: HTTP {response.status_code}")
                    if response.status_code == 401:
                        logger.error("SearchApi API密钥无效或余额不足")
                    elif response.status_code == 429:
                        logger.error("SearchApi请求频率超限")
                    self._record_api_usage("searchapi", False)
                    return []
        
        except Exception as e:
            logger.error(f"❌ SearchApi搜索异常: {e}")
            self._record_api_usage("searchapi", False)
            return []

    def _parse_serpapi_response(self, data: dict) -> List[LiteratureSearchResult]:
        """解析SerpApi响应"""
        results = []
        
        organic_results = data.get('organic_results', [])
        for item in organic_results:
            try:
                result = LiteratureSearchResult(
                    title=item.get('title', ''),
                    authors=self._extract_authors_from_serpapi(item),
                    abstract=item.get('snippet', ''),
                    publication_date=item.get('publication_info', {}).get('summary', ''),
                    journal=self._extract_journal_from_serpapi(item),
                    url=item.get('link', ''),
                    citation_count=self._extract_citations_from_serpapi(item),
                    source_database="Google Scholar (SerpApi)"
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"解析SerpApi结果时出错: {e}")
                continue
        
        return results

    def _parse_searchapi_response(self, data: dict) -> List[LiteratureSearchResult]:
        """解析SearchApi响应"""
        results = []
        
        organic_results = data.get('organic_results', [])
        for item in organic_results:
            try:
                result = LiteratureSearchResult(
                    title=item.get('title', ''),
                    authors=self._extract_authors_from_searchapi(item),
                    abstract=item.get('snippet', ''),
                    publication_date=item.get('publication_info', {}).get('summary', ''),
                    journal=self._extract_journal_from_searchapi(item),
                    url=item.get('link', ''),
                    citation_count=self._extract_citations_from_searchapi(item),
                    source_database="Google Scholar (SearchApi)"
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"解析SearchApi结果时出错: {e}")
                continue
        
        return results

    def _extract_authors_from_serpapi(self, item: dict) -> List[str]:
        """从SerpApi结果中提取作者"""
        publication_info = item.get('publication_info', {})
        authors_str = publication_info.get('authors', '')
        if authors_str:
            return [author.strip() for author in authors_str.split(',')]
        return []

    def _extract_authors_from_searchapi(self, item: dict) -> List[str]:
        """从SearchApi结果中提取作者"""
        publication_info = item.get('publication_info', {})
        authors_str = publication_info.get('authors', '')
        if authors_str:
            return [author.strip() for author in authors_str.split(',')]
        return []

    def _extract_journal_from_serpapi(self, item: dict) -> str:
        """从SerpApi结果中提取期刊"""
        publication_info = item.get('publication_info', {})
        return publication_info.get('summary', '').split(' - ')[0] if publication_info.get('summary') else ''

    def _extract_journal_from_searchapi(self, item: dict) -> str:
        """从SearchApi结果中提取期刊"""
        publication_info = item.get('publication_info', {})
        return publication_info.get('summary', '').split(' - ')[0] if publication_info.get('summary') else ''

    def _extract_citations_from_serpapi(self, item: dict) -> int:
        """从SerpApi结果中提取引用数"""
        inline_links = item.get('inline_links', {})
        cited_by = inline_links.get('cited_by', {})
        total = cited_by.get('total', 0)
        return int(total) if isinstance(total, (str, int)) and str(total).isdigit() else 0

    def _extract_citations_from_searchapi(self, item: dict) -> int:
        """从SearchApi结果中提取引用数"""
        inline_links = item.get('inline_links', {})
        cited_by = inline_links.get('cited_by', {})
        total = cited_by.get('total', 0)
        return int(total) if isinstance(total, (str, int)) and str(total).isdigit() else 0

    async def search_multiple_databases(self, query: SearchQuery) -> Dict[str, List[LiteratureSearchResult]]:
        """智能搜索多个数据库"""
        logger.info(f"🚀 开始智能文献搜索: {query.keywords}")
        start_time = time.time()
        
        # 选择最优API策略
        primary_api = self._select_optimal_api(query)
        logger.info(f"📋 选择的主要搜索API: {primary_api}")
        
        results = {}
        
        try:
            # 主要搜索
            if primary_api == "searchapi":
                results["searchapi"] = await self.search_searchapi_google_scholar(query)
            elif primary_api == "serpapi":
                results["serpapi"] = await self.search_serpapi_google_scholar(query)
            elif primary_api == "arxiv":
                results["arxiv"] = await self.search_arxiv(query)
            elif primary_api == "semantic_scholar":
                results["semantic_scholar"] = await self.search_semantic_scholar(query)
            
            # 如果主要搜索结果不足，尝试补充搜索
            total_results = sum(len(papers) for papers in results.values())
            if total_results < query.max_results // 2:
                logger.info("📈 主要搜索结果不足，启动补充搜索")
                
                # 补充免费API搜索
                if primary_api != "arxiv":
                    results["arxiv"] = await self.search_arxiv(query)
                
                if primary_api != "semantic_scholar":
                    # 适当降低结果数量以避免过多请求
                    backup_query = SearchQuery(
                        keywords=query.keywords,
                        max_results=min(query.max_results // 2, 20),
                        year_range=query.year_range
                    )
                    backup_results = await self.search_semantic_scholar(backup_query)
                    if backup_results:
                        results["semantic_scholar"] = backup_results
            
            # 记录搜索统计
            total_time = time.time() - start_time
            total_papers = sum(len(papers) for papers in results.values())
            
            logger.info(f"🎯 智能文献搜索完成: 共找到{total_papers}篇文献, 耗时{total_time:.2f}s")
            
            return results
        
        except Exception as e:
            logger.error(f"❌ 智能搜索失败: {e}")
            # 回退到基础搜索
            if self.config and getattr(self.config, 'fallback_to_free', True):
                logger.info("🔄 回退到免费API搜索")
                try:
                    results["arxiv"] = await self.search_arxiv(query)
                    return results
                except Exception as fallback_error:
                    logger.error(f"❌ 回退搜索也失败了: {fallback_error}")
            
            return {}

    def get_api_usage_report(self) -> dict:
        """获取API使用报告"""
        self._reset_daily_stats_if_needed()
        
        report = {
            "daily_cost": self.daily_cost,
            "daily_limit": getattr(self.config, 'daily_cost_limit', 10.0) if self.config else 10.0,
            "cost_percentage": (self.daily_cost / getattr(self.config, 'daily_cost_limit', 10.0) * 100) if self.config else 0,
            "apis": {}
        }
        
        for api_name, stats in self.api_usage.items():
            report["apis"][api_name] = {
                "requests": stats.requests_count,
                "cost": stats.cost_estimate,
                "errors": stats.error_count,
                "last_used": stats.last_request_time.isoformat() if stats.last_request_time else None,
                "limit_reached": stats.daily_limit_reached
            }
        
        return report

    def _update_stats(self, result_count: int, response_time: float, success: bool):
        """更新搜索统计"""
        self.search_stats["total_searches"] += 1
        if success:
            self.search_stats["successful_searches"] += 1
            self.search_stats["total_results"] += result_count
        
        self.response_times.append(response_time)
        if len(self.response_times) > 100:  # 保持最近100次的记录
            self.response_times.pop(0)
        
        self.search_stats["average_response_time"] = sum(self.response_times) / len(self.response_times)

    def get_search_stats(self) -> dict:
        """获取搜索统计信息"""
        return {
            **self.search_stats,
            "api_usage": self.get_api_usage_report()
        }

    async def search_arxiv(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """搜索arXiv数据库 - 真实API调用"""
        logger.info(f"✨ 搜索arXiv: {query.keywords}")
        start_time = time.time()
        
        try:
            # 构建arXiv查询语句
            search_terms = " AND ".join([f'all:"{kw}"' for kw in query.keywords])
            
            # 添加时间范围过滤
            if query.year_range:
                start_year, end_year = query.year_range
                search_terms += f" AND submittedDate:[{start_year}0101 TO {end_year}1231]"
            
            # 构建完整URL
            params = {
                'search_query': search_terms,
                'start': 0,
                'max_results': min(query.max_results, 100),  # arXiv限制
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            url = f"https://export.arxiv.org/api/query?{urlencode(params)}"
            logger.info(f"🔍 arXiv查询URL: {url[:100]}...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    content = response.text
                    results = self._parse_arxiv_response(content)
                    
                    # 更新统计
                    response_time = time.time() - start_time
                    self._update_stats(len(results), response_time, True)
                    
                    logger.info(f"✅ arXiv搜索成功: {len(results)}篇文献, 耗时{response_time:.2f}s")
                    return results
                else:
                    logger.error(f"❌ arXiv搜索失败: HTTP {response.status_code}")
                    return []
                        
        except Exception as e:
            logger.error(f"❌ arXiv搜索异常: {e}")
            self._update_stats(0, time.time() - start_time, False)
            return []
    
    async def search_pubmed(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """搜索PubMed数据库（使用NCBI E-utilities API）"""
        logger.info(f"搜索PubMed: {query.keywords}")
        start_time = time.time()
        
        try:
            # 第一步：搜索获取PMIDs
            search_terms = " AND ".join(f'"{keyword}"' for keyword in query.keywords)
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(search_terms)}&retmode=json&retmax={query.max_results}"
            
            async with aiohttp.ClientSession() as session:
                # 搜索阶段
                async with session.get(search_url) as response:
                    if response.status != 200:
                        logger.error(f"PubMed搜索失败: HTTP {response.status}")
                        return []
                    
                    search_data = await response.json()
                    pmids = search_data.get("esearchresult", {}).get("idlist", [])
                    
                    if not pmids:
                        logger.info("PubMed未找到相关文献")
                        return []
                
                # 获取详细信息
                if pmids:
                    pmid_list = ",".join(pmids[:20])  # 限制一次获取20个
                    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid_list}&retmode=xml"
                    
                    async with session.get(fetch_url) as response:
                        if response.status == 200:
                            xml_content = await response.text()
                            results = self._parse_pubmed_response(xml_content)
                            
                            # 更新统计
                            response_time = time.time() - start_time
                            self._update_stats(len(results), response_time, True)
                            
                            return results
                        else:
                            logger.error(f"PubMed详情获取失败: HTTP {response.status}")
                            return []
                            
        except Exception as e:
            logger.error(f"PubMed搜索异常: {e}")
            self._update_stats(0, time.time() - start_time, False)
            return []
    
    async def search_semantic_scholar(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """搜索Semantic Scholar数据库 - 真实API调用"""
        logger.info(f"✨ 搜索Semantic Scholar: {query.keywords}")
        start_time = time.time()
        
        try:
            # 构建搜索语句
            search_terms = " ".join(query.keywords)
            
            # 构建请求参数
            params = {
                'query': search_terms,
                'limit': min(query.max_results, 100),  # Semantic Scholar限制
                'fields': 'title,authors,abstract,year,journal,citationCount,url,doi,fieldsOfStudy,venue,publicationDate'
            }
            
            # 添加时间过滤
            if query.year_range:
                start_year, end_year = query.year_range
                params['year'] = f"{start_year}-{end_year}"
            
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?{urlencode(params)}"
            logger.info(f"🔍 Semantic Scholar查询: {search_terms}")
            
            headers = {
                'User-Agent': 'Research-Multi-Agent-System/1.0',
                'Accept': 'application/json'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_semantic_scholar_response(data)
                    
                    # 更新统计
                    response_time = time.time() - start_time
                    self._update_stats(len(results), response_time, True)
                    
                    logger.info(f"✅ Semantic Scholar搜索成功: {len(results)}篇文献, 耗时{response_time:.2f}s")
                    return results
                elif response.status_code == 429:
                    logger.warning("⚠️ Semantic Scholar API限流，稍后重试")
                    await asyncio.sleep(2)
                    return await self.search_semantic_scholar(query)  # 重试一次
                else:
                    logger.error(f"❌ Semantic Scholar搜索失败: HTTP {response.status_code}")
                    return []
                        
        except Exception as e:
            logger.error(f"❌ Semantic Scholar搜索异常: {e}")
            self._update_stats(0, time.time() - start_time, False)
            return []
    
    async def search_crossref(self, query: SearchQuery) -> List[LiteratureSearchResult]:
        """搜索CrossRef数据库 - 真实API调用"""
        logger.info(f"✨ 搜索CrossRef: {query.keywords}")
        start_time = time.time()
        
        try:
            # 构建搜索语句
            search_terms = " ".join(query.keywords)
            
            # 构建请求参数
            params = {
                'query': search_terms,
                'rows': min(query.max_results, 50),  # CrossRef限制
                'sort': 'relevance',
                'order': 'desc'
            }
            
            # 添加时间过滤
            if query.year_range:
                start_year, end_year = query.year_range
                params['filter'] = f'from-pub-date:{start_year},until-pub-date:{end_year}'
            
            url = f"https://api.crossref.org/works?{urlencode(params)}"
            logger.info(f"🔍 CrossRef查询: {search_terms}")
            
            headers = {
                'User-Agent': 'Research-Multi-Agent-System/1.0 (mailto:research@example.com)',
                'Accept': 'application/json'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_crossref_response(data)
                    
                    # 更新统计
                    response_time = time.time() - start_time
                    self._update_stats(len(results), response_time, True)
                    
                    logger.info(f"✅ CrossRef搜索成功: {len(results)}篇文献, 耗时{response_time:.2f}s")
                    return results
                else:
                    logger.error(f"❌ CrossRef搜索失败: HTTP {response.status_code}")
                    return []
                        
        except Exception as e:
            logger.error(f"❌ CrossRef搜索异常: {e}")
            self._update_stats(0, time.time() - start_time, False)
            return []
    
    def _parse_crossref_response(self, data: Dict[str, Any]) -> List[LiteratureSearchResult]:
        """解析CrossRef响应"""
        results = []
        try:
            items = data.get("message", {}).get("items", [])
            
            for item in items:
                # 提取作者
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                # 提取日期
                pub_date = ""
                if "published-print" in item:
                    date_parts = item["published-print"].get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        pub_date = str(date_parts[0][0])  # 获取年份
                elif "published-online" in item:
                    date_parts = item["published-online"].get("date-parts", [[]])
                    if date_parts and date_parts[0]:
                        pub_date = str(date_parts[0][0])
                
                # 提取期刊
                journal = item.get("container-title", [""])[0] if item.get("container-title") else ""
                
                # 提取DOI
                doi = item.get("DOI", "")
                
                # 提取摘要（CrossRef通常没有摘要）
                abstract = item.get("abstract", "")
                
                # 构建URL
                url = f"https://doi.org/{doi}" if doi else ""
                
                result = LiteratureSearchResult(
                    title=item.get("title", [""])[0] if item.get("title") else "",
                    authors=authors,
                    abstract=abstract,
                    publication_date=pub_date,
                    journal=journal,
                    doi=doi,
                    url=url,
                    keywords=[],
                    citation_count=item.get("is-referenced-by-count", 0),
                    source_database="crossref"
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"解析CrossRef响应失败: {e}")
        
        return results
    
    def _parse_arxiv_response(self, xml_content: str) -> List[LiteratureSearchResult]:
        """解析arXiv响应"""
        results = []
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            # arXiv命名空间
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                published = entry.find('atom:published', ns)
                
                # 作者
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)
                
                # URL
                url = entry.find('atom:id', ns)
                
                if title is not None and summary is not None:
                    result = LiteratureSearchResult(
                        title=title.text.strip(),
                        authors=authors,
                        abstract=summary.text.strip(),
                        publication_date=published.text if published is not None else "",
                        journal="arXiv",
                        url=url.text if url is not None else "",
                        keywords=[],
                        source_database="arxiv"
                    )
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"解析arXiv响应失败: {e}")
        
        return results
    
    def _parse_pubmed_response(self, xml_content: str) -> List[LiteratureSearchResult]:
        """解析PubMed响应"""
        results = []
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            for article in root.findall('.//PubmedArticle'):
                # 标题
                title_elem = article.find('.//ArticleTitle')
                title = title_elem.text if title_elem is not None else ""
                
                # 摘要
                abstract_elem = article.find('.//AbstractText')
                abstract = abstract_elem.text if abstract_elem is not None else ""
                
                # 作者
                authors = []
                for author in article.findall('.//Author'):
                    lastname = author.find('LastName')
                    forename = author.find('ForeName')
                    if lastname is not None and forename is not None:
                        authors.append(f"{forename.text} {lastname.text}")
                
                # 期刊
                journal_elem = article.find('.//Journal/Title')
                journal = journal_elem.text if journal_elem is not None else ""
                
                # 发表日期
                year_elem = article.find('.//PubDate/Year')
                year = year_elem.text if year_elem is not None else ""
                
                # DOI
                doi_elem = article.find('.//ArticleId[@IdType="doi"]')
                doi = doi_elem.text if doi_elem is not None else None
                
                if title and abstract:
                    result = LiteratureSearchResult(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        publication_date=year,
                        journal=journal,
                        doi=doi,
                        keywords=[],
                        source_database="pubmed"
                    )
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"解析PubMed响应失败: {e}")
        
        return results
    
    def _parse_semantic_scholar_response(self, data: Dict[str, Any]) -> List[LiteratureSearchResult]:
        """解析Semantic Scholar响应"""
        results = []
        try:
            for paper in data.get("data", []):
                authors = [author.get("name", "") for author in paper.get("authors", [])]
                
                result = LiteratureSearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=paper.get("abstract", ""),
                    publication_date=str(paper.get("year", "")),
                    journal=paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
                    url=paper.get("url", ""),
                    citation_count=paper.get("citationCount", 0),
                    keywords=[],
                    source_database="semantic_scholar"
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"解析Semantic Scholar响应失败: {e}")
        
        return results


class LiteratureQualityEvaluator:
    """文献质量评估器"""
    
    def __init__(self):
        self.quality_weights = {
            "citation_count": 0.3,
            "journal_impact": 0.25,
            "recency": 0.2,
            "relevance": 0.15,
            "completeness": 0.1
        }
    
    def evaluate_literature(self, literature: LiteratureSearchResult, query: SearchQuery) -> float:
        """评估文献质量"""
        scores = {}
        
        # 引用数量评分
        scores["citation_count"] = min(literature.citation_count / 100, 1.0)
        
        # 期刊影响力评分（简化版）
        scores["journal_impact"] = self._evaluate_journal_impact(literature.journal)
        
        # 时效性评分
        scores["recency"] = self._evaluate_recency(literature.publication_date)
        
        # 相关性评分
        scores["relevance"] = self._evaluate_relevance(literature, query)
        
        # 完整性评分
        scores["completeness"] = self._evaluate_completeness(literature)
        
        # 计算加权总分
        total_score = sum(
            scores[factor] * weight 
            for factor, weight in self.quality_weights.items()
        )
        
        return min(total_score * 10, 10.0)  # 转换为10分制
    
    def _evaluate_journal_impact(self, journal: str) -> float:
        """评估期刊影响力"""
        # 简化的期刊影响力评估
        high_impact_journals = [
            "nature", "science", "cell", "pnas", "jama", "nejm", 
            "lancet", "ieee", "acm", "arxiv"
        ]
        
        journal_lower = journal.lower()
        for high_journal in high_impact_journals:
            if high_journal in journal_lower:
                return 1.0
        
        return 0.6  # 默认中等影响力
    
    def _evaluate_recency(self, publication_date: str) -> float:
        """评估时效性"""
        try:
            if not publication_date:
                return 0.3
                
            year = int(publication_date[:4])
            current_year = 2024
            years_ago = current_year - year
            
            if years_ago <= 1:
                return 1.0
            elif years_ago <= 3:
                return 0.8
            elif years_ago <= 5:
                return 0.6
            elif years_ago <= 10:
                return 0.4
            else:
                return 0.2
                
        except (ValueError, IndexError):
            return 0.3
    
    def _evaluate_relevance(self, literature: LiteratureSearchResult, query: SearchQuery) -> float:
        """评估相关性"""
        # 简化的相关性评估
        text_to_check = f"{literature.title} {literature.abstract}".lower()
        keyword_matches = 0
        
        for keyword in query.keywords:
            if keyword.lower() in text_to_check:
                keyword_matches += 1
        
        if query.keywords:
            return keyword_matches / len(query.keywords)
        return 0.5
    
    def _evaluate_completeness(self, literature: LiteratureSearchResult) -> float:
        """评估完整性"""
        completeness_score = 0.0
        
        if literature.title:
            completeness_score += 0.3
        if literature.abstract:
            completeness_score += 0.4
        if literature.authors:
            completeness_score += 0.15
        if literature.journal:
            completeness_score += 0.1
        if literature.publication_date:
            completeness_score += 0.05
        
        return completeness_score


# 导出主要类
__all__ = [
    "LiteratureSearchEngine",
    "LiteratureQualityEvaluator", 
    "LiteratureSearchResult",
    "SearchQuery"
] 