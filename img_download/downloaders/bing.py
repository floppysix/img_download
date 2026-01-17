import asyncio
from typing import List
from .base import BaseImageDownloader


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器 - 先尝试第三方库，失败则用爬虫"""

    def __init__(self):
        super().__init__("bing")

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Bing 图片

        先尝试第三方库，失败则返回空列表（爬虫后续实现）
        """
        # 第一步：先返回空列表，后续再实现第三方库和爬虫
        await asyncio.sleep(0)  # 保持 async 特性
        return []
