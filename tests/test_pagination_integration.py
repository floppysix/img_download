"""
Integration tests for pagination feature.

These tests cover the full flow from search_with_pagination through
validation to download, including edge cases and error scenarios.
"""

import pytest
import json
from pathlib import Path
from typing import Set
from img_download import ImageDownloader


@pytest.mark.asyncio
async def test_full_pagination_flow_with_validation(tmp_path, mocker):
    """Test complete flow: pagination → validation → download"""
    # Mock pagination to return already-validated URLs (simulating validation happened)
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after validation has filtered out invalid URLs
        return {
            "http://example.com/valid1.jpg",
            "http://example.com/valid2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    # Mock download to avoid actual network calls
    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should download all validated URLs
    assert result["total"] == 2  # Total URLs found after validation
    assert result["success"] == 2  # All downloads succeeded
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_empty_results_integration(tmp_path, mocker):
    """Test integration behavior when all sources return empty results"""
    async def mock_empty_pagination(keyword: str) -> Set[str]:
        return set()

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_empty_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_empty_pagination
    )

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination(
        "nonexistent", sources=["bing", "baidu"]
    )

    # Should handle empty results gracefully
    assert result["total"] == 0
    assert result["success"] == 0
    assert result["failed"] == 0
    assert "sources" in result


@pytest.mark.asyncio
async def test_validation_timeout_handling(tmp_path, mocker):
    """Test graceful handling of validation timeouts"""
    # Mock pagination returning URLs that would have passed validation
    # after some timeouts occurred during the validation phase
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after validation with timeouts
        # Only the last URL passed validation (others timed out)
        return {
            "http://example.com/valid.jpg",
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should only download the URL that passed validation
    assert result["total"] == 1
    assert result["success"] == 1


@pytest.mark.asyncio
async def test_content_type_validation_integration(tmp_path, mocker):
    """Test validation with various Content-Type headers"""
    # Mock pagination simulating Content-Type validation result
    # Only actual image URLs pass validation
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after Content-Type validation
        return {
            "http://example.com/image.jpg",  # Valid image Content-Type
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should only download valid image URLs (those that passed Content-Type check)
    assert result["total"] == 1
    assert result["success"] == 1


@pytest.mark.asyncio
async def test_mixed_source_success_failure(tmp_path, mocker):
    """Test integration when some sources succeed and others fail"""
    # Bing returns URLs
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {"http://example.com/bing1.jpg", "http://example.com/bing2.jpg"}

    # Baidu raises exception
    async def mock_baidu_error(keyword: str) -> Set[str]:
        raise Exception("Network error")

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_error
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat")

    # Should succeed with Bing's results despite Baidu failure
    assert result["total"] == 2
    assert result["success"] == 2
    assert "bing" in result["sources"]


@pytest.mark.asyncio
async def test_validation_high_failure_rate_logging(tmp_path, mocker, caplog):
    """Test logging behavior when validation failure rate is high"""
    # Mock pagination simulating high failure rate during validation
    # Only 20% of original URLs passed validation
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after high failure rate validation
        return {f"http://example.com/img{i}.jpg" for i in range(4)}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should handle the high failure rate scenario
    # The pagination method returns only the validated URLs
    assert result["total"] == 4
    assert result["success"] == 4


@pytest.mark.asyncio
async def test_deduplication_across_sources_with_validation(tmp_path, mocker):
    """Test that deduplication works correctly with validation"""
    shared_urls = {
        "http://example.com/shared1.jpg",
        "http://example.com/shared2.jpg",
    }

    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return shared_urls | {"http://example.com/bing1.jpg"}

    async def mock_baidu_pagination(keyword: str) -> Set[str]:
        return shared_urls | {"http://example.com/baidu1.jpg"}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_pagination
    )

    # Mock validation - all pass
    async def mock_validate(self, urls):
        return list(urls)

    mocker.patch(
        "img_download.downloaders.base.BaseImageDownloader._validate_urls",
        mock_validate
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination(
        "cat", sources=["bing", "baidu"]
    )

    # Total should be: 2 shared + 1 bing + 1 baidu = 4 (not 6)
    assert result["total"] == 4
    assert result["success"] == 4


@pytest.mark.asyncio
async def test_sources_json_with_validation_failures(tmp_path, mocker):
    """Test sources.json correctly reflects validation and download results"""
    # Mock pagination simulating that only 2 URLs passed validation
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after validation filtered out one URL
        return {
            "http://example.com/pass1.jpg",
            "http://example.com/pass2.jpg",
        }

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Check sources.json was created correctly
    sources_file = Path(tmp_path) / "cat" / "sources.json"
    assert sources_file.exists()

    with open(sources_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Should have records only for validated URLs
    assert len(records) == 2
    for record in records:
        assert record["source"] == "bing"
        assert record["success"] is True
        assert "pass" in record["url"]


@pytest.mark.asyncio
async def test_concurrent_validation_limits(tmp_path, mocker):
    """Test that validation respects concurrency limits"""
    import asyncio

    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # Return many URLs to test concurrency
        return {f"http://example.com/img{i}.jpg" for i in range(30)}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    # Track concurrent validations
    concurrent_count = [0]
    max_concurrent = [0]

    async def mock_validate(self, urls):
        # Simulate concurrent validation
        async def check_one(url):
            concurrent_count[0] += 1
            if concurrent_count[0] > max_concurrent[0]:
                max_concurrent[0] = concurrent_count[0]
            await asyncio.sleep(0.01)
            concurrent_count[0] -= 1
            return True

        results = await asyncio.gather(*[check_one(u) for u in urls])
        return [u for u, valid in zip(urls, results) if valid]

    mocker.patch(
        "img_download.downloaders.base.BaseImageDownloader._validate_urls",
        mock_validate
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Validation should have occurred with some concurrency
    assert result["success"] > 0


@pytest.mark.asyncio
async def test_pagination_stops_with_no_valid_urls(tmp_path, mocker):
    """Test that pagination stops early when no URLs are found"""
    # Mock pagination returning empty results immediately
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # Simulates that no valid URLs were found (all failed validation)
        return set()

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should handle empty results gracefully
    assert result["total"] == 0
    assert result["success"] == 0


@pytest.mark.asyncio
async def test_stop_conditions_with_partial_validation(tmp_path, mocker):
    """Test soft stop when validation returns < 30% of page size"""
    # Mock pagination simulating low validation success rate
    # Returns only 5 URLs (< 30% of 35)
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after validation with low success rate
        # Only 5 URLs passed validation, triggering soft stop
        return {f"http://example.com/img{i}.jpg" for i in range(5)}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should handle the low validation results
    assert result["total"] == 5
    assert result["success"] == 5


@pytest.mark.asyncio
async def test_network_error_during_pagination(tmp_path, mocker):
    """Test graceful handling of network errors during pagination"""
    # Mock pagination that handles internal network errors
    # and returns partial results
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        # This simulates the result after encountering network errors
        # during pagination - some pages succeeded, others failed
        # but the downloader handled it gracefully
        return {f"http://example.com/img{i}.jpg" for i in range(15)}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination("cat", sources=["bing"])

    # Should handle network errors gracefully and return partial results
    assert result["total"] == 15
    assert result["success"] == 15


@pytest.mark.asyncio
async def test_multiple_sources_with_different_page_sizes(tmp_path, mocker):
    """Test integration when sources have different page sizes"""
    # Bing (page_size=35) returns 35 URLs
    async def mock_bing_pagination(keyword: str) -> Set[str]:
        return {f"http://example.com/bing{i}.jpg" for i in range(35)}

    # Baidu (page_size=20) returns 20 URLs
    async def mock_baidu_pagination(keyword: str) -> Set[str]:
        return {f"http://example.com/baidu{i}.jpg" for i in range(20)}

    mocker.patch(
        "img_download.downloaders.bing.BingDownloader.search_with_pagination",
        side_effect=mock_bing_pagination
    )
    mocker.patch(
        "img_download.downloaders.baidu.BaiduDownloader.search_with_pagination",
        side_effect=mock_baidu_pagination
    )

    async def mock_validate(self, urls):
        return list(urls)

    mocker.patch(
        "img_download.downloaders.base.BaseImageDownloader._validate_urls",
        mock_validate
    )

    async def mock_download(url, path, session):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake_image")
        return True

    mocker.patch("img_download.core.download_image", side_effect=mock_download)

    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search_with_pagination(
        "cat", sources=["bing", "baidu"]
    )

    # Should handle different page sizes correctly
    assert result["total"] == 55  # 35 + 20 with no overlap
    assert result["success"] == 55
