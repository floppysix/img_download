import pytest
from pathlib import Path
from img_download.utils import download_image
import aiohttp


@pytest.mark.asyncio
async def test_download_image_success(tmp_path, mocker):
    """测试成功下载图片"""
    # Mock aiohttp response
    mock_response = mocker.Mock()
    mock_response.status = 200
    mock_response.read = mocker.AsyncMock(return_value=b"fake_image_data")

    # Create a proper async context manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_response

    mock_session = mocker.Mock()
    mock_session.get = mock_get

    save_path = tmp_path / "test.jpg"
    result = await download_image("http://example.com/img.jpg", save_path, mock_session)

    assert result is True
    assert save_path.exists()
    assert save_path.read_bytes() == b"fake_image_data"


@pytest.mark.asyncio
async def test_download_image_failure(tmp_path, mocker):
    """测试下载失败"""
    mock_response = mocker.Mock()
    mock_response.status = 404

    # Create a proper async context manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_response

    mock_session = mocker.Mock()
    mock_session.get = mock_get

    save_path = tmp_path / "test.jpg"
    result = await download_image("http://example.com/img.jpg", save_path, mock_session)

    assert result is False
    assert not save_path.exists()
