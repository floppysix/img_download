import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from .downloaders import BingDownloader
from .logger import setup_logger

logger = setup_logger()


class ImageDownloader:
    """图片搜索与下载调度器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.downloaders = {
            "bing": BingDownloader(),
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

        # 简化版：先只获取 URL，不实际下载
        all_urls = []
        for source in sources:
            if source in self.downloaders:
                urls = await self.downloaders[source].search(keyword, count)
                all_urls.extend(urls)

        return {
            "total": count,
            "success": len(all_urls),
            "failed": count - len(all_urls),
            "sources": {},
            "path": str(keyword_dir)
        }
