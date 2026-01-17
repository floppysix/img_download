import pytest
from img_download import ImageDownloader


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


@pytest.mark.asyncio
async def test_concurrent_download_with_mock(tmp_path, mocker):
    """测试并发下载功能"""
    # Mock download_image 函数
    async def mock_download(url, path, session):
        # 模拟创建文件
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search("cat", count=5)

    assert result["total"] == 5
    assert result["success"] >= 0
    assert result["failed"] >= 0
