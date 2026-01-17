from typing import List, Set
import asyncio
import aiohttp
import re
import html
import json
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器 - 纯 aiohttp 实现"""

    # 分页配置参数
    page_size = 35
    max_pages = 20
    max_empty_pages = 2
    max_total_images = 2000  # 添加此属性以支持上限检查

    def __init__(self):
        super().__init__("bing")
        self.base_url = "https://www.bing.com/images/async"
        self.request_timeout = 60  # 增加超时时间：30 → 60 秒
        self.max_retries = 3  # 最大重试次数

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Bing 图片并返回 URL 列表

        使用爬虫方式获取图片 URL
        """
        urls = []

        try:
            # 构建搜索 URL
            params = {
                "q": keyword,
                "count": count * 2,  # 多请求一些，因为有些可能无效
                "first": 0,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        urls = self._parse_image_urls(html)

                        # 过滤并限制数量
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(f"Bing: found {len(urls)} images for '{keyword}'")
                    else:
                        logger.warning(f"Bing: failed with status {response.status}")

        except Exception as e:
            logger.error(f"Bing search error: {e}")

        return urls

    async def search_with_pagination(self, keyword: str) -> Set[str]:
        """
        分页搜索 Bing 图片，返回去重后的 URL 集合

        重要：Bing 要求先访问主搜索页面建立 Session，然后才能请求 /images/async
        关键：必须添加 Referer 头，否则分页会被限制

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        all_urls: Set[str] = set()
        empty_count = 0

        # 构建完整的请求头（重要：Referer 是必需的）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.bing.com/images/search?q={keyword}",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 创建共享 Session（关键：保持 Cookie）
        async with aiohttp.ClientSession() as session:
            # 第一步：访问主搜索页面建立 Session
            try:
                logger.info(f"Bing: initializing session for '{keyword}'...")
                async with session.get(
                    f"https://www.bing.com/images/search",
                    params={"q": keyword},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        cookies = session.cookie_jar.filter_cookies('https://www.bing.com')
                        logger.info(f"Bing: session initialized with {len(cookies)} cookies")
                    else:
                        logger.warning(f"Bing: session init returned status {resp.status}")
            except Exception as e:
                logger.warning(f"Bing: session init failed: {e}, continuing anyway...")

            # 第二步：使用已建立的 Session 进行分页请求
            for page in range(self.max_pages):
                # 检查是否已达到上限（提前退出）
                if len(all_urls) >= self.max_total_images:
                    logger.info(
                        f"Reached max_total_images limit ({self.max_total_images}), stopping pagination"
                    )
                    break

                first = page * self.page_size

                try:
                    # 获取单页数据（使用共享 Session 和 headers）
                    urls = await self._fetch_page(keyword, first, self.page_size, session, headers)

                    # 验证 URL
                    valid_urls = await self._validate_urls(urls)

                    # 停止检查
                    if len(valid_urls) == 0:
                        empty_count += 1
                        if empty_count >= self.max_empty_pages:
                            break
                        # 空页直接跳过，不添加也不继续
                        continue
                    else:
                        empty_count = 0

                    # 软性停止：结果数 < 30%
                    # 先添加结果，再判断是否停止
                    all_urls.update(valid_urls)
                    logger.info(
                        f"Bing page {page + 1}: found {len(valid_urls)} valid URLs "
                        f"(total: {len(all_urls)})"
                    )

                    if len(valid_urls) < self.page_size * 0.3:
                        break

                except Exception as e:
                    logger.error(f"Error fetching Bing page {page + 1}: {e}")
                    # 继续尝试下一页，不中断整个流程

        logger.info(f"Bing pagination complete: {len(all_urls)} total unique URLs")
        return all_urls

    async def _fetch_page(self, keyword: str, first: int, count: int, session: aiohttp.ClientSession, headers: dict) -> List[str]:
        """
        获取单页图片 URL（带重试机制）

        Args:
            keyword: 搜索关键词
            first: 起始位置偏移量
            count: 请求的数量
            session: 共享的 aiohttp ClientSession（保持 Cookie）
            headers: 请求头（包含必需的 Referer）

        Returns:
            图片 URL 列表
        """
        urls = []

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 构建请求参数
                params = {
                    "q": keyword,
                    "first": first,
                    "count": count,
                }

                # 使用传入的共享 Session 和 headers（关键：保持 Cookie 和 Referer）
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        urls = self._parse_image_urls(html_content)
                        if urls:  # 如果成功获取到 URL，直接返回
                            return urls
                        else:  # 状态码 200 但没有 URL，可能是空页
                            logger.info(f"Bing page {first}: no URLs found (empty page)")
                            return []
                    else:
                        logger.warning(
                            f"Bing page {first}: failed with status {response.status}"
                        )
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))  # 指数退避

            except asyncio.TimeoutError:
                logger.warning(
                    f"Bing page {first}: timeout (attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(3 * (attempt + 1))  # 增加退避时间：2 → 3 秒
            except Exception as e:
                error_msg = str(e) if str(e) else type(e).__name__
                logger.error(
                    f"Bing page {first}: error (attempt {attempt + 1}/{self.max_retries}): {error_msg}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # 指数退避

        return urls

    def _parse_image_urls(self, html_content: str) -> List[str]:
        """从 HTML 中解析图片 URL

        Bing 返回格式: <div class="iusc" m="{&quot;murl&quot;:&quot;URL&quot;,...}">
        需要提取 m 属性，解码 HTML 实体，解析 JSON，提取 murl 字段
        """
        urls = []

        try:
            # 匹配 m="..." 属性（内容可能包含 HTML 转义）
            pattern = r'm="([^"]{20,})"'
            matches = re.findall(pattern, html_content)

            for match in matches:
                try:
                    # 解码 HTML 实体（&quot; -> ", &amp; -> &）
                    decoded = html.unescape(match)
                    # 解析 JSON
                    data = json.loads(decoded)
                    # 提取 murl 字段
                    if 'murl' in data:
                        urls.append(data['murl'])
                except (json.JSONDecodeError, KeyError) as e:
                    # 静默跳过无法解析的条目
                    continue

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls

    # ========== Selenium 相关方法 ==========

    def _build_selenium_url(self, keyword: str, page: int) -> str:
        """
        构建 Bing 搜索 URL（Selenium 用）

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            Bing 图片搜索 URL
        """
        return (
            f"https://www.bing.com/images/async"
            f"?q={keyword}&async=content&first=1"
        )

    def _extract_image_urls(self, driver) -> List[str]:
        """
        从页面提取图片 URL（Selenium 用）

        不限制返回数量，由 max_total_images 控制上限

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            图片 URL 列表
        """
        from selenium.webdriver.common.by import By

        urls = set()

        try:
            # Bing 的图片 URL 通常在 img 标签的 src 属性中
            img_elements = driver.find_elements(By.TAG_NAME, "img")

            for img in img_elements:
                try:
                    src = img.get_attribute("src")
                    # 过滤掉 Bing 的 logo 和小图标
                    if (src and src.startswith("http") and
                        "bing.com" not in src and  # 排除 Bing 自身资源
                        "data:image" not in src):
                        # 检查是否已达到上限
                        if len(self._collected_urls) >= self.max_total_images:
                            break
                        urls.add(src)
                        self._collected_urls.add(src)
                except:
                    pass

        except Exception as e:
            logger.warning(f"Error extracting URLs with Selenium: {e}")

        result = list(urls)
        logger.info(
            f"Bing Selenium: extracted {len(result)} URLs "
            f"(total collected: {len(self._collected_urls)}/{self.max_total_images})"
        )
        return result
