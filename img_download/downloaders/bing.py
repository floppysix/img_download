from typing import List
import aiohttp
from selectolax.lexbor import LexborHTMLParser
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

    def _parse_image_urls(self, html: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            parser = LexborHTMLParser(html)

            # Bing 的图片 URL 通常在 murl 属性中
            for node in parser.css("div[murl]"):
                url = node.attributes.get("murl")
                if url:
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls
