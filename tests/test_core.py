import pytest
from img_download import ImageDownloader
from pathlib import Path


@pytest.mark.asyncio
async def test_image_downloader_creation(tmp_path):
    downloader = ImageDownloader(output_dir=str(tmp_path))
    assert downloader.output_dir == tmp_path
    assert "bing" in downloader.downloaders


@pytest.mark.asyncio
async def test_search_basic(tmp_path):
    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search("cat", count=10)

    assert result["total"] == 10
    assert isinstance(result, dict)
    assert "success" in result
    assert "failed" in result
    assert "path" in result
