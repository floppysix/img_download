import asyncio
from typing import List
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class GoogleDownloader(BaseImageDownloader):
    """Google 图片下载器"""

    def __init__(self):
        super().__init__("google")

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Google 图片

        先尝试第三方库，失败则返回空列表（后续实现爬虫）
        """
        # 尝试使用 google_images_download
        try:
            from google_images_download import google_images_download

            response = google_images_download.googleimagesdownload()

            # 配置参数
            arguments = {
                "keywords": keyword,
                "limit": count,
                "print_urls": True,
                "no_download": True,  # 只获取 URL
            }

            paths = response.download(arguments)

            # 解析返回的 URL
            urls = []
            if isinstance(paths, dict) and keyword in paths:
                # 从输出中提取 URL
                # 注意：这个库的输出格式需要实际测试后调整
                pass

            logger.info(f"Google: found {len(urls)} images for '{keyword}'")
            return urls

        except ImportError:
            logger.warning("google_images_download not available")
            return []
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
