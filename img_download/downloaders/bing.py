from typing import List, Set
import asyncio
import aiohttp
import re
import html
import json
import random
import time
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器 - 支持 aiohttp 和 Selenium 两种方式"""

    # 分页配置参数
    page_size = 35
    max_pages = 50  # 增加最大页数：20 → 50
    max_empty_pages = 2
    max_total_images = 2000  # 添加此属性以支持上限检查
    request_delay_base = 2.5  # 基础请求间隔（秒）
    request_delay_random = 1.0  # 随机延迟范围（秒）
    stall_threshold = 3  # 连续几页新增少于阈值时触发暂停
    stall_new_threshold = 5  # 新增URL少于此数视为停滞
    stall_pause_time = 10  # 检测到停滞时暂停时间（秒）

    # Selenium 配置
    selenium_scroll_pause = 2  # 滚动后等待时间（秒）
    selenium_max_scrolls = 20  # 最大滚动次数

    def __init__(self, use_selenium: bool = False):
        """
        初始化 Bing 下载器

        Args:
            use_selenium: 是否使用 Selenium 方式（默认 False 使用 aiohttp）
        """
        super().__init__("bing")
        self.use_selenium = use_selenium
        self.base_url = "https://www.bing.com/images/async"
        self.request_timeout = 60  # 增加超时时间：30 → 60 秒
        self.max_retries = 3  # 最大重试次数

        # Selenium 相关
        self._driver = None
        self._browser_manager = None
        self._collected_urls: Set[str] = set()  # Selenium 用：已收集的 URL

        if use_selenium:
            logger.info("Bing: 使用 Selenium 模式")
        else:
            logger.info("Bing: 使用 aiohttp 模式")

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

        根据 use_selenium 参数选择使用 aiohttp 或 Selenium 方式

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        if self.use_selenium:
            return await self._search_with_selenium(keyword)
        else:
            return await self._search_with_aiohttp(keyword)

    async def _search_with_aiohttp(self, keyword: str) -> Set[str]:
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

        # 构建完整的请求头（模拟真实浏览器行为）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.bing.com/images/search?q={keyword}",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
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
            stall_count = 0  # 连续停滞计数器
            pause_count = 0  # 暂停次数计数器
            max_pauses = 2  # 最多暂停2次

            for page in range(self.max_pages):
                # 检查是否已达到上限（提前退出）
                if len(all_urls) >= self.max_total_images:
                    logger.info(
                        f"Reached max_total_images limit ({self.max_total_images}), stopping pagination"
                    )
                    break

                first = page * self.page_size
                prev_count = len(all_urls)  # 记录处理前的数量

                try:
                    # 获取单页数据（使用共享 Session 和 headers）
                    urls = await self._fetch_page(keyword, first, self.page_size, session, headers, page)

                    # 添加随机化的请求间隔（从第二页开始）
                    if page > 0:
                        delay = self.request_delay_base + random.uniform(0, self.request_delay_random)
                        await asyncio.sleep(delay)

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

                    # 先添加结果
                    all_urls.update(valid_urls)
                    new_count = len(all_urls) - prev_count  # 本页新增数量

                    logger.info(
                        f"Bing page {page + 1}: found {len(valid_urls)} valid URLs, "
                        f"{new_count} new (total: {len(all_urls)})"
                    )

                    # 智能停滞检测：连续几页新增很少
                    if new_count < self.stall_new_threshold:
                        stall_count += 1
                        logger.info(f"Stall detected: {new_count} new URLs (stall_count: {stall_count}/{self.stall_threshold}, pause_count: {pause_count}/{max_pauses})")

                        if stall_count >= self.stall_threshold and pause_count < max_pauses:
                            # 检测到持续停滞，暂停一段时间后继续
                            pause_count += 1
                            logger.info(
                                f"Persistent stall detected, pausing for {self.stall_pause_time}s "
                                f"(pause {pause_count}/{max_pauses})..."
                            )
                            await asyncio.sleep(self.stall_pause_time)
                            stall_count = 0  # 重置停滞计数
                            continue  # 继续下一页
                    else:
                        stall_count = 0  # 有新增，重置停滞计数

                    # 软性停止：结果数 < 30% 且非停滞状态
                    if new_count == 0 and len(valid_urls) < self.page_size * 0.3:
                        logger.info("Page return rate < 30% with no new URLs, stopping pagination")
                        break

                except Exception as e:
                    logger.error(f"Error fetching Bing page {page + 1}: {e}")
                    # 继续尝试下一页，不中断整个流程

        logger.info(f"Bing pagination complete: {len(all_urls)} total unique URLs")
        return all_urls

    async def _fetch_page(self, keyword: str, first: int, count: int, session: aiohttp.ClientSession, headers: dict, page: int = 0) -> List[str]:
        """
        获取单页图片 URL（带重试机制）

        Args:
            keyword: 搜索关键词
            first: 起始位置偏移量
            count: 请求的数量
            session: 共享的 aiohttp ClientSession（保持 Cookie）
            headers: 请求头（包含必需的 Referer）
            page: 当前页码（用于生成动态参数）

        Returns:
            图片 URL 列表
        """
        urls = []

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                # 构建请求参数（模拟真实搜索行为，添加动态参数）
                params = {
                    "q": keyword,
                    "first": first,
                    "count": count,
                    "mmasync": "1",  # 启用异步加载
                    "scenario": "ImageBasicHover",  # 基本悬停场景
                    "lostate": "r",  # 结果状态
                    "layout": "row",  # 行布局
                    "SFX": str(random.randint(1, 5)),  # 随机搜索效果参数
                    "iid": f"images.{page + 1}.{random.randint(1000, 9999)}",  # 动态接口标识
                    "tsc": "ImageBasicHover",  # 添加更多真实参数
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

    async def _search_with_selenium(self, keyword: str) -> Set[str]:
        """
        使用 Selenium 分页搜索 Bing 图片

        通过模拟浏览器滚动来加载更多图片

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        all_urls: Set[str] = set()
        self._collected_urls = set()  # 重置已收集的 URL

        try:
            # 获取浏览器实例
            driver = self._get_driver()

            # 访问 Bing 图片搜索页面
            search_url = f"https://www.bing.com/images/search?q={keyword}"
            logger.info(f"Bing Selenium: 访问 {search_url}")
            driver.get(search_url)

            # 等待页面加载
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "iusc"))
            )

            # 滚动加载更多图片
            last_height = driver.execute_script("return document.body.scrollHeight")

            for scroll_count in range(self.selenium_max_scrolls):
                # 检查是否已达到上限
                if len(all_urls) >= self.max_total_images:
                    logger.info(f"Reached max_total_images limit ({self.max_total_images}), stopping")
                    break

                # 解析当前页面的图片
                new_urls = self._parse_image_urls_from_driver(driver)
                before_count = len(all_urls)
                all_urls.update(new_urls)
                new_count = len(all_urls) - before_count

                logger.info(
                    f"Bing Selenium: 滚动 {scroll_count + 1}, "
                    f"当前: {len(all_urls)}, 新增: {new_count}"
                )

                # 滚动到底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(self.selenium_scroll_pause)

                # 检查是否到达底部
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # 尝试点击"加载更多"按钮
                    try:
                        load_more = driver.find_element(By.CLASS_NAME, "btn_seemore")
                        load_more.click()
                        time.sleep(self.selenium_scroll_pause)
                    except:
                        # 没有更多按钮，可能到底了
                        logger.info("Bing Selenium: 到达页面底部")
                        break

                last_height = new_height

                # 如果连续几次没有新增，停止
                if new_count == 0 and len(all_urls) > 0:
                    logger.info("Bing Selenium: 没有新内容，停止加载")
                    break

        except Exception as e:
            logger.error(f"Bing Selenium 搜索错误: {e}")

        logger.info(f"Bing Selenium: 完成，共 {len(all_urls)} 个唯一 URL")
        return all_urls

    def _get_driver(self):
        """获取或创建浏览器实例"""
        if self._driver is None:
            from ..drivers.selenium_driver import BrowserManager
            self._browser_manager = BrowserManager()
            self._driver = self._browser_manager.get_driver()
        return self._driver

    def _parse_image_urls_from_driver(self, driver) -> Set[str]:
        """
        从 Selenium 页面提取图片 URL

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            图片 URL 集合
        """
        from selenium.webdriver.common.by import By

        urls = set()

        try:
            # Bing 的图片 URL 在 div.iusc 的 m 属性中（JSON 格式）
            elements = driver.find_elements(By.CLASS_NAME, "iusc")

            for elem in elements:
                try:
                    m_attr = elem.get_attribute("m")
                    if m_attr:
                        # 解码 HTML 实体
                        decoded = html.unescape(m_attr)
                        # 解析 JSON
                        data = json.loads(decoded)
                        # 提取 murl 字段
                        if 'murl' in data:
                            urls.add(data['murl'])
                except (json.JSONDecodeError, KeyError):
                    continue

        except Exception as e:
            logger.warning(f"从页面提取 URL 错误: {e}")

        return urls

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
