import pytest
from unittest.mock import MagicMock, AsyncMock
from img_download.downloaders import BingDownloader


@pytest.mark.asyncio
async def test_bing_downloader_creation():
    downloader = BingDownloader()
    assert downloader.name == "bing"


@pytest.mark.asyncio
async def test_bing_search_with_mock_html(mocker):
    """测试 HTML 解析功能"""
    downloader = BingDownloader()

    # Mock HTML 响应（模拟 Bing 返回的实际格式，包含 HTML 实体编码）
    mock_html = '''
    <div class="imgpt" murl&quot;:&quot;https://example.com/image1.jpg&quot;</div>
    <div class="imgpt" murl&quot;:&quot;https://example.com/image2.png&quot;</div>
    <div class="imgpt" murl&quot;:&quot;https://example.com/image3.gif&quot;</div>
    '''

    # Create response mock
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=mock_html)

    # Create response context manager
    response_cm = AsyncMock()
    response_cm.__aenter__.return_value = mock_response
    response_cm.__aexit__.return_value = None

    # Create session mock
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response_cm)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Patch ClientSession
    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("cat", 10)

    assert len(result) == 3
    assert "https://example.com/image1.jpg" in result
    assert "https://example.com/image2.png" in result


@pytest.mark.asyncio
async def test_bing_search_empty_result(mocker):
    """测试空结果"""
    downloader = BingDownloader()

    # Create response mock
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html></html>")

    # Create response context manager
    response_cm = AsyncMock()
    response_cm.__aenter__.return_value = mock_response
    response_cm.__aexit__.return_value = None

    # Create session mock
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response_cm)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Patch ClientSession
    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("nonexistent", 10)

    assert result == []


@pytest.mark.asyncio
async def test_bing_search_non_200_status(mocker):
    """测试非200状态码"""
    downloader = BingDownloader()

    mock_response = mocker.Mock()
    mock_response.status = 404

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("cat", 10)
    assert result == []
