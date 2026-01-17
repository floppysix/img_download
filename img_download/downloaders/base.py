from abc import ABC, abstractmethod
from typing import List


class BaseImageDownloader(ABC):
    """图片下载器抽象基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索图片并返回 URL 列表

        Args:
            keyword: 搜索关键词
            count: 需要的图片数量

        Returns:
            图片 URL 列表
        """
        pass
