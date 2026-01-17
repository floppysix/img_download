import asyncio
from typing import List
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BaiduDownloader(BaseImageDownloader):
    """百度图片下载器 - 纯爬虫实现"""

    def __init__(self):
        super().__init__("baidu")
        self.base_url = "https://image.baidu.com/search/index"

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索百度图片

        使用爬虫方式
        """
        urls = []

        try:
            params = {
                "tn": "baiduimage",
                "word": keyword,
                "pn": 0,
                "rn": count * 2,
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
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(f"Baidu: found {len(urls)} images for '{keyword}'")
                    else:
                        logger.warning(f"Baidu: failed with status {response.status}")

        except Exception as e:
            logger.error(f"Baidu search error: {e}")

        return urls

    def _parse_image_urls(self, html: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            parser = LexborHTMLParser(html)

            # 百度的图片 URL 通常在 data-imgurl 属性中
            for node in parser.css("img[data-imgurl]"):
                url = node.attributes.get("data-imgurl")
                if url:
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls
