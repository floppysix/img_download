from typing import List
import aiohttp
import re
import html
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器"""

    def __init__(self):
        super().__init__("bing")
        self.base_url = "https://www.bing.com/images/async"

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
                    timeout=30
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

    def _parse_image_urls(self, html_content: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            # Bing 返回的数据格式: murl&quot;:&quot;URL&quot;
            # 使用正则表达式提取并解码 HTML 实体
            pattern = r'murl&quot;:&quot;([^&]+)&quot;'
            matches = re.findall(pattern, html_content)

            for match in matches:
                # 解码 HTML 实体（&quot; -> "）
                decoded_url = html.unescape(match)
                urls.append(decoded_url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls
