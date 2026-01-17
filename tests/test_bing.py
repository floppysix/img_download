import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from img_download.downloaders import BingDownloader


@pytest.mark.asyncio
async def test_bing_downloader_creation():
    downloader = BingDownloader()
    assert downloader.name == "bing"
    assert downloader.page_size == 35
    assert downloader.max_pages == 20
    assert downloader.max_empty_pages == 2


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


@pytest.mark.asyncio
async def test_search_with_pagination_mock(mocker):
    """测试分页搜索功能（使用 mock）"""
    downloader = BingDownloader()

    # Mock HTML 响应 - 每页返回不同的 URL
    # 第一页：15 个 URL（> 30% 的 35，即 > 10.5）
    page_0_urls = [f'<div murl&quot;:&quot;https://example.com/img{i}.jpg&quot;</div>' for i in range(15)]
    page_0_html = '\n'.join(page_0_urls)

    # 第二页：12 个 URL（> 30%，但少于第一页）
    page_1_urls = [f'<div murl&quot;:&quot;https://example.com/img{i}.jpg&quot;</div>' for i in range(15, 27)]
    page_1_html = '\n'.join(page_1_urls)

    # Mock HTTP 响应
    def mock_get(url, params, headers, timeout):
        mock_resp = AsyncMock()
        mock_resp.status = 200

        first = params.get('first', 0)

        if first == 0:
            mock_resp.text = AsyncMock(return_value=page_0_html)
        elif first == 35:
            mock_resp.text = AsyncMock(return_value=page_1_html)
        else:
            # 后续页面返回空
            mock_resp.text = AsyncMock(return_value="")

        # Create a proper async context manager mock
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        return mock_cm

    mock_session = MagicMock()
    mock_session.get = mock_get
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Mock validation - all URLs valid
    async def mock_validate(urls):
        return urls

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该获取到 27 个唯一 URL（15 + 12）
    # 第三页返回空，连续2个空页后停止
    assert len(result) == 27
    assert "https://example.com/img0.jpg" in result
    assert "https://example.com/img26.jpg" in result
    assert isinstance(result, set)


@pytest.mark.asyncio
async def test_search_with_pagination_stop_conditions(mocker):
    """测试停止条件"""
    downloader = BingDownloader()

    # Mock validation - 模拟第一页有结果，第二页为空
    async def mock_validate(urls):
        return urls[:10] if len(urls) > 10 else []

    call_count = [0]

    async def mock_fetch_page(keyword, first, count):
        call_count[0] += 1
        # 第1页返回 35 个 URL，第2页返回 0 个
        if call_count[0] == 1:
            return [f"https://example.com/img{i}.jpg" for i in range(35)]
        else:
            return []

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该在连续空页后停止
    assert len(result) == 10  # 只有第1页的10个有效URL
    assert call_count[0] <= 3  # 不应该超过 max_empty_pages + 1


@pytest.mark.asyncio
async def test_search_with_pagination_soft_stop(mocker):
    """测试软性停止条件（结果数 < 30%）"""
    downloader = BingDownloader()

    # Mock validation - 返回少于 30% 的结果
    async def mock_validate(urls):
        # 只返回 5 个 URL（< 35 * 0.3 = 10.5）
        return urls[:5]

    call_count = [0]

    async def mock_fetch_page(keyword, first, count):
        call_count[0] += 1
        if call_count[0] == 1:
            return [f"https://example.com/img{i}.jpg" for i in range(35)]
        else:
            return [f"https://example.com/img{i}.jpg" for i in range(35)]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该在第1页后因结果数过少而停止
    # 注意：软停止时，结果会被添加后再停止
    assert len(result) == 5  # 添加了5个结果后停止
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_fetch_page_helper(mocker):
    """测试 _fetch_page 辅助方法"""
    downloader = BingDownloader()

    mock_html = '<div murl&quot;:&quot;https://example.com/test.jpg&quot;</div>'

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=mock_html)

    response_cm = AsyncMock()
    response_cm.__aenter__.return_value = mock_response
    response_cm.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response_cm)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader._fetch_page("cat", first=0, count=35)

    assert len(result) == 1
    assert result[0] == "https://example.com/test.jpg"


@pytest.mark.asyncio
async def test_search_with_pagination_deduplication(mocker):
    """测试 URL 自动去重"""
    downloader = BingDownloader()

    # 两页返回重复的 URL
    mock_html = '''
        <div murl&quot;:&quot;https://example.com/duplicate.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique1.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique2.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique3.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique4.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique5.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique6.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique7.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique8.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique9.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique10.jpg&quot;</div>
        <div murl&quot;:&quot;https://example.com/unique11.jpg&quot;</div>
    '''

    def mock_get(url, params, headers, timeout):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value=mock_html)

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        return mock_cm

    mock_session = MagicMock()
    mock_session.get = mock_get
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    async def mock_validate(urls):
        return urls

    mocker.patch.object(downloader, "_validate_urls", side_effect=mock_validate)

    result = await downloader.search_with_pagination("cat")

    # 即使多页返回相同 URL，结果集应该去重
    assert isinstance(result, set)
    # 所有页面返回相同内容，应该只有 12 个唯一 URL
    assert len(result) == 12
    assert "https://example.com/duplicate.jpg" in result
    assert "https://example.com/unique1.jpg" in result


@pytest.mark.asyncio
async def test_search_with_pagination_max_pages_limit(mocker):
    """测试最大页数限制"""
    downloader = BingDownloader()
    downloader.max_pages = 3  # 设置较小的最大页数用于测试

    page_call_count = [0]

    async def mock_fetch_page(keyword, first, count):
        # 每页返回不同的 URL
        page_call_count[0] += 1
        start_idx = (page_call_count[0] - 1) * 35
        return [f"https://example.com/img{i}.jpg" for i in range(start_idx, start_idx + 35)]

    async def mock_validate(urls):
        # 返回 30 个有效 URL (> 30%)
        return urls[:30]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该在达到 max_pages 后停止
    # 3 页，每页 30 个唯一 URL = 90
    assert len(result) == 90
    assert page_call_count[0] == 3  # 应该调用 3 次


@pytest.mark.asyncio
async def test_search_with_pagination_exception_handling(mocker):
    """测试异常处理"""
    downloader = BingDownloader()

    call_count = [0]

    async def mock_fetch_page(keyword, first, count):
        call_count[0] += 1
        if call_count[0] == 1:
            return [f"https://example.com/img{i}.jpg" for i in range(35)]
        else:
            raise Exception("Network error")

    async def mock_validate(urls):
        return urls[:30]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    # 应该捕获异常并继续
    result = await downloader.search_with_pagination("cat")

    # 第1页应该成功，第2页异常但不会中断整个流程
    assert len(result) >= 30
    assert call_count[0] >= 2
