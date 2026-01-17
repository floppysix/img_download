import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
from .downloaders import BingDownloader, GoogleDownloader, BaiduDownloader
from .utils import download_image
from .logger import setup_logger

logger = setup_logger()


class ImageDownloader:
    """图片搜索与下载调度器"""

    def __init__(self, output_dir: str = "output", max_concurrent: int = 10):
        self.output_dir = Path(output_dir)
        self.max_concurrent = max_concurrent
        self.downloaders = {
            "bing": BingDownloader(),
            "baidu": BaiduDownloader(),
            "google": GoogleDownloader(),
        }

    async def search(
        self,
        keyword: str,
        count: int = 50,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        搜索并下载图片

        Args:
            keyword: 搜索关键词
            count: 下载数量
            sources: 图片来源列表，None 则使用全部

        Returns:
            统计结果字典
        """
        if sources is None:
            sources = list(self.downloaders.keys())

        # 创建关键词文件夹
        keyword_dir = self.output_dir / keyword
        keyword_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting search for '{keyword}', count: {count}, sources: {sources}")

        # 获取图片 URL
        all_urls = []
        for source in sources:
            if source in self.downloaders:
                urls = await self.downloaders[source].search(keyword, count)
                all_urls.extend(urls)

        # 限制数量
        all_urls = all_urls[:count]

        # 并发下载
        stats = await self._download_concurrent(keyword, keyword_dir, all_urls)

        return {
            "total": count,
            "success": stats["success"],
            "failed": stats["failed"],
            "path": str(keyword_dir)
        }

    async def _download_concurrent(
        self,
        keyword: str,
        save_dir: Path,
        urls: List[str]
    ) -> Dict[str, Any]:
        """并发下载图片"""
        success_count = 0
        failed_count = 0

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession() as session:
            # 绑定 session 到 download_image
            tasks = []
            for i, url in enumerate(urls):
                # 创建闭包捕获正确的 url 和 session
                async def bound_download(u=url, idx=i):
                    async with semaphore:
                        # 使用实际文件扩展名
                        ext = self._get_extension(u)
                        filename = f"img_{idx:03d}{ext}"
                        save_path = save_dir / filename
                        return await download_image(u, save_path, session)

                tasks.append(bound_download())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, bool):
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1

        return {
            "success": success_count,
            "failed": failed_count
        }

    def _get_extension(self, url: str) -> str:
        """从 URL 获取文件扩展名"""
        url_lower = url.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            if ext in url_lower:
                return ext
        return ".jpg"
