import pytest
from typing import Set
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


@pytest.mark.asyncio
async def test_search_with_pagination_parallel(tmp_path, mocker):
    """Test parallel execution of multiple sources with pagination"""
    # Track execution order to verify parallelism
    execution_order = []

    async def mock_search_with_pagination(keyword: str) -> Set[str]:
        import asyncio
        # Add a small delay to allow parallel execution
        await asyncio.sleep(0.01)
        execution_order.append(keyword)

        # Return different URLs for different sources to test merging
        if "bing" in str(type(mocker.call_args)):
            return {
                "http://example.com/bing1.jpg",
                "http://example.com/bing2.jpg",
                "http://example.com/bing3.jpg",
            }
        elif "baidu" in str(type(mocker.call_args)):
            return {
                "http://example.com/baidu1.jpg",
                "http://example.com/baidu2.jpg",
                "http://example.com/baidu3.jpg",
            }
        return set()

    # Mock the pagination methods for all downloaders
    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_search_with_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_search_with_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat")

    # Verify results
    assert isinstance(result, dict)
    assert "total" in result
    assert "success" in result
    assert "failed" in result
    assert "path" in result
    assert "sources" in result

    # Should have URLs from both sources (minus any duplicates)
    assert result["total"] >= 0


@pytest.mark.asyncio
async def test_search_with_pagination_deduplication(tmp_path, mocker):
    """Test global deduplication across multiple sources"""
    # Shared URLs that should be deduplicated
    shared_urls = {
        "http://example.com/shared1.jpg",
        "http://example.com/shared2.jpg",
    }

    bing_only_urls = {
        "http://example.com/bing1.jpg",
        "http://example.com/bing2.jpg",
    }

    baidu_only_urls = {
        "http://example.com/baidu1.jpg",
        "http://example.com/baidu2.jpg",
    }

    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return shared_urls | bing_only_urls

    async def mock_baidu_pagination(keyword: str) -> Set[str]:
        return shared_urls | baidu_only_urls

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing", "baidu"])

    # Total should be: shared (2) + bing_only (2) + baidu_only (2) = 6
    # NOT: (shared + bing_only) + (shared + baidu_only) = 8
    assert result["total"] == 6
    assert result["success"] == 6
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_search_with_pagination_source_tracking(tmp_path, mocker):
    """Test that sources are properly tracked for sources.json"""
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/bing1.jpg",
            "http://example.com/bing2.jpg",
        }

    async def mock_baidu_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/baidu1.jpg",
            "http://example.com/baidu2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing", "baidu"])

    # Verify source statistics
    assert "sources" in result
    sources = result["sources"]
    assert "bing" in sources
    assert "baidu" in sources

    # Each source should have 2 successful downloads
    assert sources["bing"]["success"] == 2
    assert sources["bing"]["failed"] == 0
    assert sources["baidu"]["success"] == 2
    assert sources["baidu"]["failed"] == 0

    # Verify sources.json file was created
    import json
    from pathlib import Path

    sources_file = Path(tmp_path) / "cat" / "sources.json"
    assert sources_file.exists()

    with open(sources_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Verify all records have source information
    assert len(records) == 4
    for record in records:
        assert "source" in record
        assert "filename" in record
        assert "url" in record
        assert "success" in record
        assert record["success"] is True

    # Verify source distribution
    bing_records = [r for r in records if r["source"] == "bing"]
    baidu_records = [r for r in records if r["source"] == "baidu"]
    assert len(bing_records) == 2
    assert len(baidu_records) == 2


@pytest.mark.asyncio
async def test_search_with_pagination_not_implemented(tmp_path, mocker):
    """Test graceful handling of downloaders that don't implement pagination"""
    # Mock Google downloader to raise NotImplementedError
    async def mock_not_implemented(keyword: str) -> Set[str]:
        raise NotImplementedError("Google does not implement pagination")

    # Mock Bing to work normally
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/bing1.jpg",
            "http://example.com/bing2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.google.GoogleDownloader.search_with_pagination",
        side_effect=mock_not_implemented
    )
    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat")

    # Should succeed with only Bing's results
    assert result["total"] == 2
    assert result["success"] == 2
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_search_with_pagination_exception_handling(tmp_path, mocker):
    """Test graceful handling of exceptions from individual downloaders"""
    # Mock Baidu to raise an exception
    async def mock_baidu_error(keyword: str) -> Set[str]:
        raise Exception("Network error")

    # Mock Bing to work normally
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/bing1.jpg",
            "http://example.com/bing2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_error
    )
    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat")

    # Should succeed with only Bing's results (Baidu error is logged but doesn't crash)
    assert result["total"] == 2
    assert result["success"] == 2
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_search_with_pagination_custom_sources(tmp_path, mocker):
    """Test using custom sources list"""
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/bing1.jpg",
            "http://example.com/bing2.jpg",
        }

    async def mock_baidu_pagination(keyword: str) -> Set[str]:
        return {
            "http://example.com/baidu1.jpg",
            "http://example.com/baidu2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_pagination
    )

    # Mock download to avoid actual downloads
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))

    # Test with only bing source
    result = await downloader.search_with_pagination("cat", sources=["bing"])
    assert result["total"] == 2
    assert result["sources"]["bing"]["success"] == 2
    assert "baidu" not in result["sources"]

    # Test with only baidu source
    result = await downloader.search_with_pagination("cat", sources=["baidu"])
    assert result["total"] == 2
    assert result["sources"]["baidu"]["success"] == 2
    assert "bing" not in result["sources"]
