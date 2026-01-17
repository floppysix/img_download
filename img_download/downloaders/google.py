from typing import List, Set
import aiohttp
import re
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class GoogleDownloader(BaseImageDownloader):
    """Google 图片下载器 - 纯爬虫实现"""

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
        super().__init__("google")
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
        获取单页图片 URL

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
                            f"Google page start={start}: "
                            f"failed with status {response.status}"
                        )

        except Exception as e:
            logger.error(f"Error fetching Google page (start={start}): {e}")

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
