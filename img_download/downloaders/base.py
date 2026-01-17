from abc import ABC, abstractmethod
from typing import List, Set
import aiohttp


class BaseImageDownloader(ABC):
    """图片下载器抽象基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索图片并返回 URL 列表（单页，保持向后兼容）

        Args:
            keyword: 搜索关键词
            count: 需要的图片数量

        Returns:
            图片 URL 列表
        """
        pass

    async def search_with_pagination(self, keyword: str) -> Set[str]:
        """
        分页搜索，返回去重后的 URL 集合（新接口）

        Default implementation raises NotImplementedError.
        Concrete classes should override this method.

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement search_with_pagination()")

    async def _validate_urls(self, urls: List[str]) -> List[str]:
        """
        验证 URL 有效性（HEAD 请求）

        Args:
            urls: 待验证的 URL 列表

        Returns:
            有效的 URL 列表
        """
        import asyncio
        from ..logger import setup_logger

        logger = setup_logger()
        valid_urls = []
        semaphore = asyncio.Semaphore(10)  # 10 并发验证

        async def check(url: str) -> bool:
            try:
                async with semaphore:
                    async with aiohttp.ClientSession() as session:
                        async with session.head(url, timeout=10) as resp:
                            return resp.status == 200 and self._is_image(resp)
            except Exception:
                return False

        results = await asyncio.gather(*[check(u) for u in urls])

        for url, is_valid in zip(urls, results):
            if is_valid:
                valid_urls.append(url)
            else:
                logger.warning(f"Validation failed: {url[:60]}...")

        # 失败率监控
        if len(valid_urls) < len(urls) * 0.5:
            logger.warning(f"High failure rate: {len(valid_urls)}/{len(urls)}")

        return valid_urls

    def _is_image(self, response) -> bool:
        """检查响应是否为图片"""
        ct = response.headers.get('Content-Type', '')
        return ct.startswith('image/')

    def _should_stop(self, valid_urls: List[str], page_size: int, empty_count: int, current_page: int = 0, max_pages: int = 20, max_empty_pages: int = 2) -> bool:
        """
        判断是否应该停止分页

        Args:
            valid_urls: 当前页有效 URL 列表
            page_size: 每页请求的数量
            empty_count: 当前连续空页数
            current_page: 当前页码（从 0 开始）
            max_pages: 最大请求页数（硬性上限）
            max_empty_pages: 连续空页停止阈值

        Returns:
            是否应该停止
        """
        # 硬性上限：最大页数
        if current_page >= max_pages:
            return True

        # 连续空页停止
        if len(valid_urls) == 0:
            return empty_count >= max_empty_pages

        # 末页检测：返回数量 < 30%
        if len(valid_urls) < page_size * 0.3:
            return True

        return False
