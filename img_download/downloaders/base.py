from abc import ABC, abstractmethod
import asyncio
from typing import List, Set
import aiohttp
from ..logger import setup_logger


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
        class_name = self.__class__.__name__
        msg = f"{class_name} must implement search_with_pagination()"
        raise NotImplementedError(msg)

    async def _validate_urls(self, urls: List[str]) -> List[str]:
        """
        验证 URL 有效性（GET 请求 + 宽松验证）

        Args:
            urls: 待验证的 URL 列表

        Returns:
            有效的 URL 列表
        """
        logger = setup_logger()
        valid_urls = []
        semaphore = asyncio.Semaphore(50)  # 提高并发到 50（性能优化）

        # 复用 ClientSession（关键优化）
        async with aiohttp.ClientSession() as session:
            async def check(url: str) -> bool:
                try:
                    async with semaphore:
                        # 使用 GET 请求而不是 HEAD（HEAD 经常被拒绝）
                        # 只请求前 1KB 数据来验证
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=5),
                            headers={"Range": "bytes=0-1023"}  # 只请求前 1KB
                        ) as resp:
                            # 接受 200 (OK) 和 206 (Partial Content，由于 Range 请求)
                            if resp.status in (200, 206):
                                # 宽松验证：有 Content-Type 或者 URL 看起来像图片
                                ct = resp.headers.get('Content-Type', '')
                                if ct.startswith('image/'):
                                    return True
                                # 如果没有 Content-Type，检查 URL 扩展名
                                url_lower = url.lower()
                                if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                                    return True
                            return False
                except Exception as e:
                    # 静默失败，不打印每个错误
                    return False

            results = await asyncio.gather(*[check(u) for u in urls])

        for url, is_valid in zip(urls, results):
            if is_valid:
                valid_urls.append(url)

        # 只打印汇总信息
        logger.info(f"Validation: {len(valid_urls)}/{len(urls)} URLs passed")

        return valid_urls

    def _is_image(self, response: aiohttp.ClientResponse) -> bool:
        """检查响应是否为图片"""
        ct = response.headers.get('Content-Type', '')
        return ct.startswith('image/')

    def _should_stop(
        self,
        valid_urls: List[str],
        page_size: int,
        empty_count: int,
        current_page: int = 0,
        max_pages: int = 20,
        max_empty_pages: int = 2,
    ) -> bool:
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
