import pytest
from img_download.downloaders import GoogleDownloader


@pytest.mark.asyncio
async def test_google_downloader_creation():
    downloader = GoogleDownloader()
    assert downloader.name == "google"


@pytest.mark.asyncio
async def test_google_search_without_library():
    """测试没有第三方库时的行为"""
    downloader = GoogleDownloader()
    result = await downloader.search("cat", 10)
    # 应该返回空列表（库未安装）
    assert isinstance(result, list)
