"""Odaily 快讯爬虫"""
import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class OdailyCrawler:
    """Odaily 快讯爬虫"""

    def __init__(self):
        self.base_url = settings.ODAILY_BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _get(self, url: str, **kwargs) -> requests.Response:
        """带自动重试的 GET 请求（最多 3 次，指数退避）"""
        return requests.get(url, headers=self.headers, timeout=self.timeout, **kwargs)

    def fetch_news_list(self, page: int = 1, limit: int = 20) -> List[Dict]:
        """
        获取快讯列表

        Args:
            page: 页码
            limit: 每页数量

        Returns:
            快讯列表
        """
        # 尝试方法1: 使用 API 接口（如果存在）
        news_items = self._try_fetch_from_api(page, limit)

        # 如果 API 失败，使用方法2: 解析 HTML
        if not news_items:
            news_items = self._fetch_from_html(page)

        print(f"从页面爬取到 {len(news_items)} 条快讯")
        return news_items

    def _try_fetch_from_api(self, page: int, limit: int) -> List[Dict]:
        """尝试从 API 获取数据"""
        api_urls = [
            f"{self.base_url}/api/pp/api/info-flow/newsflash_columns/newsflashes",
            f"{self.base_url}/api/newsflash/list",
            f"{self.base_url}/newsflash/ajax",
        ]

        for api_url in api_urls:
            try:
                params = {'page': page, 'limit': limit, 'b_id': 181}
                response = self._get(api_url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data:
                        items = data['data'].get('items', []) or data['data'].get('list', [])
                        if items:
                            print(f"成功从 API 获取数据: {api_url}")
                            return self._parse_api_response(items)
            except Exception:
                continue

        return []

    def _parse_api_response(self, items: List[Dict]) -> List[Dict]:
        """解析 API 响应"""
        news_items = []

        for item in items:
            try:
                content = item.get('description') or item.get('content') or item.get('title', '')
                if len(content) < 20:
                    continue

                title = self._extract_title_from_content(content)
                published_at = self._parse_timestamp(item)
                odaily_id = self._make_id(content, published_at)

                news_items.append({
                    'odaily_id': odaily_id,
                    'title': title,
                    'content': content,
                    'published_at': published_at,
                    'source_url': item.get('url') or f"{self.base_url}/newsflash",
                })
            except Exception as e:
                print(f"Error parsing API item: {e}")
                continue

        return news_items

    def _fetch_from_html(self, page: int) -> List[Dict]:
        """从 HTML 页面获取数据"""
        url = f"{self.base_url}/newsflash"

        try:
            response = self._get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 方法1: Next.js __NEXT_DATA__
            news_items = self._parse_nextjs_data(soup)

            # 方法2: CSS 选择器匹配常见快讯结构
            if not news_items:
                news_items = self._parse_with_css_selectors(soup)

            # 方法3: 降级 —— 页面文本正则匹配
            if not news_items:
                news_items = self._parse_news_list(soup)

            return news_items
        except Exception as e:
            print(f"Error fetching news from HTML: {e}")
            return []

    def _parse_nextjs_data(self, soup: BeautifulSoup) -> List[Dict]:
        """从 Next.js __NEXT_DATA__ 中提取数据"""
        try:
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            if not script_tag:
                return []

            data = json.loads(script_tag.string)

            paths = [
                ['props', 'pageProps', 'newsflashes'],
                ['props', 'pageProps', 'data', 'items'],
                ['props', 'pageProps', 'initialData', 'items'],
                ['props', 'pageProps', 'list'],
            ]

            items = None
            for path in paths:
                try:
                    current = data
                    for key in path:
                        current = current[key]
                    if current and isinstance(current, list):
                        items = current
                        print(f"从 Next.js 数据中找到 {len(items)} 条快讯")
                        break
                except (KeyError, TypeError):
                    continue

            if not items:
                return []

            news_items = []
            for item in items:
                try:
                    content = item.get('description') or item.get('content') or item.get('title', '')
                    if len(content) < 20:
                        continue

                    title = self._extract_title_from_content(content)
                    published_at = self._parse_timestamp(item)
                    odaily_id = self._make_id(content, published_at)

                    news_items.append({
                        'odaily_id': odaily_id,
                        'title': title,
                        'content': content,
                        'published_at': published_at,
                        'source_url': item.get('url') or f"{self.base_url}/newsflash",
                    })
                except Exception as e:
                    print(f"Error parsing Next.js item: {e}")
                    continue

            return news_items

        except Exception as e:
            print(f"Error parsing Next.js data: {e}")
            return []

    def _parse_with_css_selectors(self, soup: BeautifulSoup) -> List[Dict]:
        """使用 CSS 选择器匹配快讯条目（覆盖常见 Next.js 快讯页面结构）"""
        # 按优先级尝试多种可能的选择器
        candidate_selectors = [
            'li.newsflash-item',
            'div.newsflash-item',
            'article.newsflash',
            'li[data-id]',
            'div[class*="newsflash"]',
            'div[class*="flash-item"]',
            'li[class*="flash"]',
        ]

        for selector in candidate_selectors:
            elements = soup.select(selector)
            if not elements:
                continue

            news_items = []
            for el in elements:
                try:
                    # 尝试提取时间
                    time_el = el.find(['time', 'span'], attrs={'class': re.compile(r'time|date', re.I)})
                    time_text = time_el.get_text(strip=True) if time_el else ''

                    # 提取内容文本
                    content = el.get_text(separator=' ', strip=True)
                    # 去掉时间部分避免污染内容
                    if time_text and content.startswith(time_text):
                        content = content[len(time_text):].strip()

                    content = self._clean_text(content)
                    if len(content) < 20:
                        continue

                    title = self._extract_title_from_content(content)
                    published_at = self._parse_today_time(time_text) if time_text else datetime.now()
                    odaily_id = self._make_id(content, published_at)

                    news_items.append({
                        'odaily_id': odaily_id,
                        'title': title,
                        'content': content,
                        'published_at': published_at,
                        'source_url': f"{self.base_url}/newsflash",
                    })
                except Exception as e:
                    print(f"CSS selector parse error: {e}")
                    continue

            if news_items:
                print(f"通过 CSS 选择器 '{selector}' 找到 {len(news_items)} 条快讯")
                return news_items

        return []

    def _parse_news_list(self, soup: BeautifulSoup) -> List[Dict]:
        """降级方案：从页面文本正则匹配（格式：HH:MM + 内容）"""
        page_text = soup.get_text()

        pattern = r'(\d{2}:\d{2})([^\d\n]+?)(?=\d{2}:\d{2}|$)'
        matches = re.findall(pattern, page_text, re.DOTALL)

        print(f"从页面文本中匹配到 {len(matches)} 条快讯")

        news_items = []
        for idx, (time_str, content_raw) in enumerate(matches):
            try:
                content = self._clean_text(content_raw)
                if len(content) < 20:
                    continue

                title = self._extract_title_from_content(content)
                published_at = self._parse_today_time(time_str)
                odaily_id = self._make_id(content, published_at)

                news_items.append({
                    'odaily_id': odaily_id,
                    'title': title,
                    'content': content,
                    'published_at': published_at,
                    'source_url': f"{self.base_url}/newsflash",
                })
                print(f"  [{idx + 1}] {time_str} - {title[:40]}... (内容长度: {len(content)})")
            except Exception as e:
                print(f"Error parsing news item {idx}: {e}")
                continue

        return news_items

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _make_id(self, content: str, published_at: Optional[datetime]) -> str:
        """根据内容和时间生成确定性唯一 ID"""
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        if published_at:
            date_str = published_at.strftime('%Y%m%d%H%M')
            return f"odaily_{date_str}_{content_hash}"
        return f"odaily_{content_hash}"

    def _parse_timestamp(self, item: Dict) -> Optional[datetime]:
        """从字典中解析时间戳字段"""
        for key in ('published_at', 'created_at', 'time'):
            val = item.get(key)
            if val:
                try:
                    return datetime.fromtimestamp(int(val))
                except (ValueError, OSError):
                    continue
        return None

    def _extract_title_from_content(self, content: str) -> str:
        """从内容中提取标题"""
        content = re.sub(r'^Odaily星球日报讯?\s*', '', content)
        sentences = re.split(r'[。！？\n]', content)
        if sentences and len(sentences[0]) > 10:
            return sentences[0][:80].strip()
        return content[:80].strip()

    def _parse_today_time(self, time_str: str) -> datetime:
        """解析 HH:MM 格式的时间（当天日期）"""
        try:
            today = datetime.now().date()
            parts = time_str.split(':')
            hour, minute = int(parts[0]), int(parts[1])
            return datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
        except Exception:
            return datetime.now()

    def _clean_text(self, text: str) -> str:
        """清洗文本：合并空白"""
        return re.sub(r'\s+', ' ', text).strip()


def clean_news_data(news_data: Dict) -> Optional[Dict]:
    """
    清洗快讯数据

    Args:
        news_data: 原始快讯数据

    Returns:
        清洗后的数据，无效时返回 None
    """
    if not news_data:
        return None

    cleaned = news_data.copy()

    if 'title' in cleaned:
        cleaned['title'] = re.sub(r'<[^>]+>', '', cleaned['title']).strip()

    if 'content' in cleaned:
        cleaned['content'] = re.sub(r'<[^>]+>', '', cleaned['content'])
        cleaned['content'] = re.sub(r'\s+', ' ', cleaned['content']).strip()

    if not cleaned.get('content') or len(cleaned.get('content', '')) < 10:
        return None

    return cleaned
