import pytest
from img_download.downloaders import BaseImageDownloader


def test_base_is_abstract():
    """基类不能直接实例化"""
    with pytest.raises(TypeError):
        BaseImageDownloader()


def test_concrete_downloader():
    """子类必须实现 search 方法"""

    class TestDownloader(BaseImageDownloader):
        async def search(self, keyword: str, count: int) -> list:
            return []

    downloader = TestDownloader("test")
    assert downloader.name == "test"
