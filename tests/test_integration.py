import pytest
from img_download import ImageDownloader


@pytest.mark.asyncio
async def test_module_import():
    """测试模块可以正确导入"""
    from img_download import ImageDownloader
    assert ImageDownloader is not None


@pytest.mark.asyncio
async def test_module_version():
    """测试模块有版本号"""
    import img_download
    assert hasattr(img_download, "__version__")
    assert isinstance(img_download.__version__, str)
    assert len(img_download.__version__) > 0


@pytest.mark.asyncio
async def test_basic_usage(tmp_path):
    """测试基本使用流程"""
    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search("test", count=5)

    assert isinstance(result, dict)
    assert result["total"] == 5
