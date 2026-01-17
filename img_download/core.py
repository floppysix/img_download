import asyncio
import json
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

        # 收集所有来源的 URL（带来源标记）
        url_sources = []
        for source in sources:
            if source in self.downloaders:
                urls = await self.downloaders[source].search(keyword, count)
                for url in urls:
                    url_sources.append((url, source))

        # 限制数量
        url_sources = url_sources[:count]

        # 并发下载
        stats = await self._download_concurrent(keyword, keyword_dir, url_sources)

        return {
            "total": count,
            "success": stats["success"],
            "failed": stats["failed"],
            "sources": stats.get("sources", {}),
            "path": str(keyword_dir)
        }

    async def _download_concurrent(
        self,
        keyword: str,
        save_dir: Path,
        url_sources: List[tuple]
    ) -> Dict[str, Any]:
        """并发下载图片"""
        success_count = 0
        failed_count = 0
        source_stats = {}
        download_records = []

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession() as session:
            # 绑定 session 到 download_image
            tasks = []
            for idx, (url, source) in enumerate(url_sources):
                # 创建闭包捕获正确的 url 和 session
                async def bound_download(u=url, s=source, i=idx):
                    async with semaphore:
                        # 文件命名格式: 关键词_序号.扩展名
                        ext = self._get_extension(u)
                        filename = f"{keyword}_{i + 1}{ext}"
                        save_path = save_dir / filename

                        # 下载
                        result = await download_image(u, save_path, session)

                        # 记录下载信息
                        record = {
                            "filename": filename,
                            "source": s,
                            "url": u,
                            "success": result
                        }
                        download_records.append(record)

                        # 更新来源统计
                        if s not in source_stats:
                            source_stats[s] = {"success": 0, "failed": 0}
                        if result:
                            source_stats[s]["success"] += 1
                        else:
                            source_stats[s]["failed"] += 1

                        return result

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

        # 保存来源记录到 JSON 文件
        self._save_source_records(save_dir, download_records)

        return {
            "success": success_count,
            "failed": failed_count,
            "sources": source_stats
        }

    def _save_source_records(self, save_dir: Path, records: List[Dict]):
        """保存图片来源记录到 JSON 文件"""
        records_file = save_dir / "sources.json"
        try:
            with open(records_file, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            logger.info(f"Source records saved to: {records_file}")
        except Exception as e:
            logger.error(f"Failed to save source records: {e}")

    def _get_extension(self, url: str) -> str:
        """从 URL 获取文件扩展名"""
        url_lower = url.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            if ext in url_lower:
                return ext
        return ".jpg"
