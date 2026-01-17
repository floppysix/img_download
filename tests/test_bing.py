import pytest
from img_download.downloaders import BingDownloader


@pytest.mark.asyncio
async def test_bing_downloader_creation():
    downloader = BingDownloader()
    assert downloader.name == "bing"


@pytest.mark.asyncio
async def test_bing_search_returns_list():
    downloader = BingDownloader()
    result = await downloader.search("cat", 10)
    assert isinstance(result, list)
    # 目前返回空列表,后续实现后再更新
    assert result == []
