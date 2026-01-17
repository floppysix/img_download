import pytest
from unittest.mock import MagicMock, AsyncMock
from img_download.downloaders import BaiduDownloader


@pytest.mark.asyncio
async def test_baidu_downloader_creation():
    downloader = BaiduDownloader()
    assert downloader.name == "baidu"
    assert downloader.page_size == 20
    assert downloader.max_pages == 20
    assert downloader.max_empty_pages == 2


@pytest.mark.asyncio
async def test_baidu_search_with_mock_html(mocker):
    """测试 HTML 解析功能"""
    downloader = BaiduDownloader()

    # Mock HTML 响应（模拟 Baidu 返回的 HTML）
    mock_html = '''
    <div>
        <img data-imgurl="https://example.com/image1.jpg">
        <img data-imgurl="https://example.com/image2.png">
        <img data-imgurl="https://example.com/image3.gif">
    </div>
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
async def test_baidu_search_empty_result(mocker):
    """测试空结果"""
    downloader = BaiduDownloader()

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
async def test_baidu_search_non_200_status(mocker):
    """测试非200状态码"""
    downloader = BaiduDownloader()

    mock_response = mocker.Mock()
    mock_response.status = 404

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mock_response
    )
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("cat", 10)
    assert result == []


@pytest.mark.asyncio
async def test_search_with_pagination_mock(mocker):
    """测试分页搜索功能（使用 mock）"""
    downloader = BaiduDownloader()
    # 测试时只获取 2 页，加快测试速度
    original_max_pages = downloader.max_pages
    downloader.max_pages = 2

    # Mock JSON 响应 - 每页返回不同的 URL
    page_0_data = [
        {"objURL": f"https://example.com/img{i}.jpg"}
        for i in range(10)
    ]
    page_1_data = [
        {"objURL": f"https://example.com/img{i}.jpg"}
        for i in range(10, 18)
    ]

    # Mock HTTP 响应
    def mock_get(url, params, headers, timeout):
        mock_resp = AsyncMock()
        mock_resp.status = 200

        pn = params.get('pn', 0)

        if pn == 0:
            mock_resp.json = AsyncMock(return_value={"data": page_0_data})
        elif pn == 20:
            mock_resp.json = AsyncMock(return_value={"data": page_1_data})
        else:
            # 后续页面返回空
            mock_resp.json = AsyncMock(return_value={"data": []})

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

    # 应该获取到 18 个唯一 URL（10 + 8）
    # 第三页返回空，连续2个空页后停止
    assert len(result) == 18
    assert "https://example.com/img0.jpg" in result
    assert "https://example.com/img17.jpg" in result
    assert isinstance(result, set)


@pytest.mark.asyncio
async def test_search_with_pagination_stop_conditions(mocker):
    """测试停止条件"""
    downloader = BaiduDownloader()
    # 测试时只获取 2 页
    downloader.max_pages = 2

    # Mock validation - 模拟第一页有结果，第二页为空
    async def mock_validate(urls):
        return urls[:8] if len(urls) > 8 else []

    call_count = [0]

    async def mock_fetch_page(keyword, pn, count):
        call_count[0] += 1
        # 第1页返回 20 个 URL，第2页返回 0 个
        if call_count[0] == 1:
            return [f"https://example.com/img{i}.jpg" for i in range(20)]
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
    assert len(result) == 8  # 只有第1页的8个有效URL
    assert call_count[0] <= 3  # 不应该超过 max_empty_pages + 1


@pytest.mark.asyncio
async def test_search_with_pagination_soft_stop(mocker):
    """测试软性停止条件（结果数 < 30%）"""
    downloader = BaiduDownloader()
    downloader.max_pages = 2

    # Mock validation - 返回少于 30% 的结果
    async def mock_validate(urls):
        # 只返回 3 个 URL（< 20 * 0.3 = 6）
        return urls[:3]

    call_count = [0]

    async def mock_fetch_page(keyword, pn, count):
        call_count[0] += 1
        return [f"https://example.com/img{i}.jpg" for i in range(20)]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该在第1页后因结果数过少而停止
    # 注意：软停止时，结果会被添加后再停止
    assert len(result) == 3  # 添加了3个结果后停止
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_fetch_page_helper(mocker):
    """测试 _fetch_page 辅助方法"""
    downloader = BaiduDownloader()

    mock_json = {
        "data": [
            {"objURL": "https://example.com/test.jpg"},
            {"middleURL": "https://example.com/test2.jpg"},
            {"thumbURL": "https://example.com/test3.jpg"},
        ]
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_json)

    response_cm = AsyncMock()
    response_cm.__aenter__.return_value = mock_response
    response_cm.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response_cm)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader._fetch_page("cat", pn=0, count=20)

    assert len(result) == 3
    assert "https://example.com/test.jpg" in result
    assert "https://example.com/test2.jpg" in result
    assert "https://example.com/test3.jpg" in result


@pytest.mark.asyncio
async def test_search_with_pagination_deduplication(mocker):
    """测试 URL 自动去重"""
    downloader = BaiduDownloader()

    # 两页返回重复的 URL
    mock_json = {
        "data": [
            {"objURL": "https://example.com/duplicate.jpg"},
            {"objURL": "https://example.com/unique1.jpg"},
            {"objURL": "https://example.com/unique2.jpg"},
            {"objURL": "https://example.com/unique3.jpg"},
            {"objURL": "https://example.com/unique4.jpg"},
            {"objURL": "https://example.com/unique5.jpg"},
            {"objURL": "https://example.com/unique6.jpg"},
            {"objURL": "https://example.com/unique7.jpg"},
            {"objURL": "https://example.com/unique8.jpg"},
        ]
    }

    def mock_get(url, params, headers, timeout):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_json)

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
    # 所有页面返回相同内容，应该只有 9 个唯一 URL
    assert len(result) == 9
    assert "https://example.com/duplicate.jpg" in result
    assert "https://example.com/unique1.jpg" in result


@pytest.mark.asyncio
async def test_search_with_pagination_max_pages_limit(mocker):
    """测试最大页数限制"""
    downloader = BaiduDownloader()
    downloader.max_pages = 3  # 设置较小的最大页数用于测试

    page_call_count = [0]

    async def mock_fetch_page(keyword, pn, count):
        # 每页返回不同的 URL
        page_call_count[0] += 1
        start_idx = (page_call_count[0] - 1) * 20
        url_list = [
            f"https://example.com/img{i}.jpg"
            for i in range(start_idx, start_idx + 20)
        ]
        return url_list

    async def mock_validate(urls):
        # 返回 15 个有效 URL (> 30%)
        return urls[:15]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    result = await downloader.search_with_pagination("cat")

    # 应该在达到 max_pages 后停止
    # 3 页，每页 15 个唯一 URL = 45
    assert len(result) == 45
    assert page_call_count[0] == 3  # 应该调用 3 次


@pytest.mark.asyncio
async def test_search_with_pagination_exception_handling(mocker):
    """测试异常处理"""
    downloader = BaiduDownloader()

    call_count = [0]

    async def mock_fetch_page(keyword, pn, count):
        call_count[0] += 1
        if call_count[0] == 1:
            return [f"https://example.com/img{i}.jpg" for i in range(20)]
        else:
            raise Exception("Network error")

    async def mock_validate(urls):
        return urls[:15]

    mocker.patch.object(
        downloader, "_fetch_page", side_effect=mock_fetch_page
    )
    mocker.patch.object(
        downloader, "_validate_urls", side_effect=mock_validate
    )

    # 应该捕获异常并继续
    result = await downloader.search_with_pagination("cat")

    # 第1页应该成功，第2页异常但不会中断整个流程
    assert len(result) >= 15
    assert call_count[0] >= 2


@pytest.mark.asyncio
async def test_parse_image_urls_from_json():
    """测试 JSON 解析功能"""
    downloader = BaiduDownloader()

    # 测试完整的 JSON 数据
    mock_json = {
        "data": [
            {"objURL": "https://example.com/obj1.jpg"},
            {"middleURL": "https://example.com/mid1.jpg"},
            {"thumbURL": "https://example.com/thumb1.jpg"},
            {
                "objURL": "https://example.com/obj2.jpg",
                "middleURL": "https://example.com/mid2.jpg"
            },
            # 没有 URL 的项应该被跳过
            {"objURL": ""},
            {"middleURL": None},
            # 非 http URL 应该被跳过
            {"objURL": "ftp://example.com/file.jpg"},
        ]
    }

    result = downloader._parse_image_urls_from_json(mock_json)

    # 应该返回 4 个有效 URL（优先 objURL，最后一个是无效的 ftp URL）
    assert len(result) == 4
    assert "https://example.com/obj1.jpg" in result
    assert "https://example.com/mid1.jpg" in result
    assert "https://example.com/thumb1.jpg" in result
    assert "https://example.com/obj2.jpg" in result  # objURL 优先于 middleURL


@pytest.mark.asyncio
async def test_fetch_page_with_various_url_types(mocker):
    """测试 _fetch_page 处理不同类型的 URL"""
    downloader = BaiduDownloader()

    # 测试只有 thumbURL 的情况
    mock_json = {
        "data": [
            {"thumbURL": "https://example.com/thumb1.jpg"},
            {"thumbURL": "https://example.com/thumb2.jpg"},
            # objURL 和 middleURL 都不存在的情况
            {"thumbURL": "https://example.com/thumb3.jpg"},
        ]
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_json)

    response_cm = AsyncMock()
    response_cm.__aenter__.return_value = mock_response
    response_cm.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=response_cm)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader._fetch_page("cat", pn=0, count=20)

    # 当只有 thumbURL 时，也应该能提取 URL
    assert len(result) == 3
    assert all(url.startswith("https://example.com/thumb") for url in result)
