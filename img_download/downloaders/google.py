from typing import List, Set
import aiohttp
import re
import time
from .base import BaseImageDownloader
from .selenium_mixin import SeleniumMixin
from ..logger import setup_logger

logger = setup_logger()


class GoogleDownloader(BaseImageDownloader, SeleniumMixin):
    """Google 图片下载器 - aiohttp + Selenium 混合模式"""

    # 分页配置参数
    page_size = 20
    max_pages = 20
    max_empty_pages = 2

    # HTTP 请求配置
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    REQUEST_TIMEOUT = 30

    def __init__(self):
        BaseImageDownloader.__init__(self, "google")
        SeleniumMixin.__init__(self)
        self.base_url = "https://www.google.com/search"

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Google 图片

        使用爬虫方式获取图片 URL
        """
        urls = []

        try:
            # 构建搜索 URL
            params = {
                "tbm": "isch",
                "q": keyword,
                "start": 0,
            }

            headers = {"User-Agent": self.USER_AGENT}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        urls = self._parse_image_urls(html)

                        # 过滤并限制数量
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(f"Google: found {len(urls)} images for '{keyword}'")
                    else:
                        logger.warning(f"Google: failed with status {response.status}")

        except Exception as e:
            logger.error(f"Google search error: {e}")

        return urls

    async def search_with_pagination(self, keyword: str) -> Set[str]:
        """
        分页搜索 Google 图片，返回去重后的 URL 集合

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        all_urls: Set[str] = set()
        empty_count = 0

        for page in range(self.max_pages):
            start = page * self.page_size

            try:
                # 获取单页数据
                urls = await self._fetch_page(keyword, start, self.page_size)

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
                    f"Google page {page + 1}: "
                    f"found {len(valid_urls)} valid URLs "
                    f"(total: {len(all_urls)})"
                )

                if len(valid_urls) < self.page_size * 0.3:
                    break

            except Exception as e:
                logger.error(f"Error fetching Google page {page + 1}: {e}")
                # 继续尝试下一页，不中断整个流程

        logger.info(
            f"Google pagination complete: "
            f"{len(all_urls)} total unique URLs"
        )
        return all_urls

    async def _fetch_page(self, keyword: str, start: int, count: int) -> List[str]:
        """
        获取单页图片 URL（混合模式：aiohttp 优先，Selenium 备用）

        Args:
            keyword: 搜索关键词
            start: 起始位置偏移量（0, 20, 40, ...）
            count: 请求的数量

        Returns:
            图片 URL 列表
        """
        # 策略 1: 先尝试 aiohttp
        urls = await self._fetch_with_aiohttp(keyword, start, count)
        if urls:
            return urls

        # 策略 2: aiohttp 失败，使用 Selenium
        logger.info("Google aiohttp failed, trying Selenium...")
        page_num = start // self.page_size
        return await self._fetch_with_selenium(keyword, page_num)

    async def _fetch_with_aiohttp(
        self,
        keyword: str,
        start: int,
        count: int
    ) -> List[str]:
        """
        使用 aiohttp 获取单页图片 URL

        Args:
            keyword: 搜索关键词
            start: 起始位置偏移量（0, 20, 40, ...）
            count: 请求的数量

        Returns:
            图片 URL 列表
        """
        urls = []

        try:
            # 构建请求参数
            params = {
                "tbm": "isch",
                "q": keyword,
                "start": start,
            }

            headers = {"User-Agent": self.USER_AGENT}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        urls = self._parse_image_urls(html_content)
                    else:
                        logger.warning(
                            f"Google aiohttp failed (start={start}): "
                            f"status {response.status}"
                        )

        except Exception as e:
            logger.warning(f"Google aiohttp error: {e}")

        return urls

    def _parse_image_urls(self, html_content: str) -> List[str]:
        """
        从 HTML 中解析图片 URL

        Google Images 返回的 HTML 中包含图片 URL，
        通常在 data-src 或 src 属性中
        """
        urls = []

        try:
            # 方法1: 提取 data-url 属性中的 URL（HTML 属性格式）
            data_url_pattern = r'data-url="([^"]+)"'
            matches = re.findall(data_url_pattern, html_content)
            urls.extend(matches)

            # 方法2: 提取 src 或 data-src 属性中的图片 URL
            # 排除明显的小图标和 logo
            src_pattern = r'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*>'
            src_matches = re.findall(src_pattern, html_content)

            for url in src_matches:
                # 过滤掉明显的小图标和静态资源
                if (url.startswith("http") and
                    not any(x in url.lower() for x in [
                        "logo", "icon", "favicon", "gstatic", "svg"
                    ])):
                    urls.append(url)

            # 方法3: 提取 ou= 参数中的 URL (Google 特有格式)
            ou_pattern = r'"ou":"([^"]+)"'
            ou_matches = re.findall(ou_pattern, html_content)
            urls.extend(ou_matches)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls

    # ========== Selenium 相关方法 ==========

    def _build_selenium_url(self, keyword: str, page: int) -> str:
        """
        构建谷歌搜索 URL（Selenium 用）

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            谷歌图片搜索 URL
        """
        return f"https://www.google.com/search?tbm=isch&q={keyword}"

    def _extract_image_urls(self, driver) -> List[str]:
        """
        从页面提取图片 URL（Selenium 用）

        Google Images 使用多种提取策略：
        1. 点击图片获取页面中的直接 URL（最优先）
        2. data-url 属性（直接图片 URL）
        3. JSON 格式中的 URL
        4. src/data-src（代理 URL，最后备用）

        不限制返回数量，由 max_total_images 控制上限

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            图片 URL 列表
        """
        from selenium.webdriver.common.by import By

        direct_urls = set()  # 直接图片 URL
        proxy_urls = set()   # 代理 URL

        def can_add_more() -> bool:
            """检查是否还可以添加更多 URL"""
            return len(self._collected_urls) < self.max_total_images

        # 策略 1: 点击第一张图片来触发加载原始 URL
        try:
            if can_add_more():
                first_img = driver.find_element(
                    By.CSS_SELECTOR,
                    "img[src^='https://encrypted-tbn0.gstatic.com']"
                )
                driver.execute_script("arguments[0].scrollIntoView();", first_img)
                driver.execute_script("arguments[0].click();", first_img)
                time.sleep(2)

                # 从更新后的页面源码中提取直接 URL
                page_source = driver.page_source

                # 查找所有 http/https URL，过滤出图片 URL
                all_urls = re.findall(r'https?://[^\s"<>{}|\\^`\[\]]+', page_source)
                for url in all_urls:
                    if not can_add_more():
                        break
                    # 过滤出真正的图片 URL
                    if (url.startswith("http") and
                        'encrypted-tbn0' not in url and
                        'gstatic.com' not in url and
                        'google.com' not in url and
                        'googleapis.com' not in url and
                        'favicon' not in url.lower() and
                        len(url) > 30):
                        # 检查是否包含图片文件扩展名或常见图片域名
                        if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']):
                            direct_urls.add(url)
                            self._collected_urls.add(url)
                        elif any(domain in url for domain in [
                            'wikimedia', 'shutterstock', 'istockphoto', 'getty',
                            'images.', 'img.', 'photos.', 'media.',
                            'upload.', 'cdn.', 'static.'
                        ]):
                            direct_urls.add(url)
                            self._collected_urls.add(url)

        except Exception as e:
            pass  # 点击失败，继续使用其他策略

        # 策略 2: Google 的 data-url 属性
        if can_add_more():
            try:
                img_elements = driver.find_elements(
                    By.CSS_SELECTOR,
                    "img[data-url]"
                )
                for img in img_elements:
                    if not can_add_more():
                        break
                    url = img.get_attribute("data-url")
                    if url and url.startswith("http"):
                        direct_urls.add(url)
                        self._collected_urls.add(url)
            except Exception:
                pass

        # 策略 3: 页面中的 JSON 格式
        if can_add_more():
            try:
                page_source = driver.page_source
                patterns = [
                    r'"ou":"([^"]+)"',
                    r"'ou':\s*'([^']+)'",
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, page_source)
                    for match in matches:
                        if not can_add_more():
                            break
                        if match.startswith("http") and 'google' not in match:
                            direct_urls.add(match)
                            self._collected_urls.add(match)
            except Exception:
                pass

        # 策略 4: 常规 src/data-src（代理 URL，备用）
        if not direct_urls and can_add_more():
            try:
                all_images = driver.find_elements(By.TAG_NAME, "img")
                for img in all_images:
                    if not can_add_more():
                        break
                    for attr in ["src", "data-src"]:
                        url = img.get_attribute(attr)
                        # 只收集 Google 代理 URL（缩略图）
                        if (url and url.startswith("http") and
                            "encrypted-tbn0.gstatic.com" in url):
                            proxy_urls.add(url)
                            self._collected_urls.add(url)
            except Exception:
                pass

        # 优先返回直接 URL，如果没有则使用代理 URL
        result = list(direct_urls) if direct_urls else list(proxy_urls)
        logger.info(
            f"Google Selenium: extracted {len(result)} URLs "
            f"({len(direct_urls)} direct, {len(proxy_urls)} proxy) "
            f"[total collected: {len(self._collected_urls)}/{self.max_total_images}]"
        )
        return result
