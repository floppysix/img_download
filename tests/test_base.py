import pytest
from img_download.downloaders import BaseImageDownloader
from unittest.mock import MagicMock, patch


def test_base_is_abstract():
    """基类不能直接实例化"""
    with pytest.raises(TypeError):
        BaseImageDownloader()


# Concrete downloader for testing pagination and abstract methods
class ConcreteDownloader(BaseImageDownloader):
    """Concrete implementation for testing purposes"""

    async def search(self, keyword: str, count: int) -> list:
        return []

    # Not implementing search_with_pagination to test
    # NotImplementedError


def test_concrete_downloader():
    """子类必须实现 search 方法"""

    class TestDownloader(BaseImageDownloader):
        async def search(self, keyword: str, count: int) -> list:
            return []

        async def search_with_pagination(self, keyword: str) -> set:
            return set()

    downloader = TestDownloader("test")
    assert downloader.name == "test"


@pytest.mark.asyncio
async def test_should_stop_hard_limit():
    """Test stopping at max_pages limit"""
    downloader = ConcreteDownloader("test")
    result = downloader._should_stop(
        [], 35, 0, current_page=20, max_pages=20
    )
    assert result is True
    result = downloader._should_stop(
        [], 35, 0, current_page=19, max_pages=20
    )
    assert result is False


@pytest.mark.asyncio
async def test_should_stop_empty_pages():
    """Test stopping after consecutive empty pages"""
    downloader = ConcreteDownloader("test")
    assert downloader._should_stop([], 35, 2, current_page=0) is True
    assert downloader._should_stop([], 35, 1, current_page=0) is False


@pytest.mark.asyncio
async def test_should_stop_low_results():
    """Test stopping when results < 30% of page size"""
    downloader = ConcreteDownloader("test")
    # 9 results < 35 * 0.3 = 10.5
    result = downloader._should_stop(
        ['url'] * 9, 35, 0, current_page=0
    )
    assert result is True
    result = downloader._should_stop(
        ['url'] * 11, 35, 0, current_page=0
    )
    assert result is False


@pytest.mark.asyncio
async def test_should_stop_continue():
    """Test pagination should continue"""
    downloader = ConcreteDownloader("test")
    result = downloader._should_stop(
        ['url'] * 30, 35, 0, current_page=0
    )
    assert result is False


@pytest.mark.asyncio
async def test_search_with_pagination_not_implemented():
    """Test NotImplementedError when calling unimplemented pagination"""
    downloader = ConcreteDownloader("test")
    with pytest.raises(
        NotImplementedError, match="must implement search_with_pagination"
    ):
        await downloader.search_with_pagination("test")


@pytest.mark.asyncio
async def test_validate_urls_with_mock(mocker):
    """测试 URL 验证功能"""

    class TestDownloader(BaseImageDownloader):
        async def search(self, keyword: str, count: int) -> list:
            return []

        async def search_with_pagination(self, keyword: str) -> set:
            return set()

    downloader = TestDownloader("test")

    # Create a custom MockHead class to handle async context properly
    class MockHead:
        def __init__(self, status, headers):
            self.status = status
            self.headers = headers

        async def __aenter__(self):
            resp = MagicMock()
            resp.status = self.status
            resp.headers = self.headers
            return resp

        async def __aexit__(self, *args):
            pass

    # Mock responses for each URL
    mock_heads = [
        MockHead(200, {'Content-Type': 'image/jpeg'}),  # Valid image
        MockHead(404, {}),                               # Not found
        MockHead(200, {'Content-Type': 'text/html'}),    # Wrong content type
    ]

    call_count = [0]

    # Create the head method mock
    def mock_head(url, timeout=10):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(mock_heads):
            return mock_heads[idx]
        return MockHead(404, {})

    # Create mock session
    mock_session = MagicMock()
    mock_session.head = mock_head

    # Create ClientSession mock that returns our session
    class MockSession:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            pass

    # Patch aiohttp.ClientSession
    patch_target = 'img_download.downloaders.base.aiohttp.ClientSession'
    with patch(patch_target, return_value=MockSession()):
        urls = [
            "http://example.com/1.jpg",
            "http://example.com/2.jpg",
            "http://example.com/3.jpg"
        ]
        result = await downloader._validate_urls(urls)

    assert len(result) == 1  # 只有第一个是有效图片
    assert "http://example.com/1.jpg" in result
