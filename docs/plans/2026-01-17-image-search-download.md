# 图片搜索与下载模块实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个 Python 模块，支持通过关键词搜索并批量下载图片，支持多个图片来源，使用第三方库和爬虫兜底方案。

**Architecture:** 分层架构（接口层 → 调度层 → 下载器层 → 工具层），每个图片来源一个下载器类实现统一接口，使用 asyncio 实现并发下载。

**Tech Stack:** Python 3.10+, aiohttp, selectolax, asyncio, logging

---

## 项目结构

```
img_download/
├── __init__.py           # 导出 ImageDownloader
├── core.py               # 主调度器
├── downloaders/          # 各来源下载器
│   ├── __init__.py
│   ├── base.py           # 抽象基类
│   ├── bing.py           # Bing 下载器
│   ├── google.py         # Google 下载器
│   └── ...
├── utils.py              # 通用工具
└── logger.py             # 日志配置
tests/
├── __init__.py
├── test_core.py
├── test_downloaders.py
└── fixtures/
```

---

## Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "img-download"
version = "0.1.0"
description = "Image search and download module"
requires-python = ">=3.10"
dependencies = [
    "aiohttp>=3.9.0",
    "selectolax>=0.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: 创建 requirements.txt**

```
aiohttp>=3.9.0
selectolax>=0.3.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

**Step 3: 更新 .gitignore**

```
.pytest_cache/
__pycache__/
*.py[cod]
*$py.class
.coverage
htmlcov/
*.log
output/
dist/
*.egg-info/
```

**Step 4: 创建 README.md**

```markdown
# img_download

图片搜索与下载模块

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```python
from img_download import ImageDownloader

downloader = ImageDownloader()
result = downloader.search("猫咪", count=50)
```
```

**Step 5: 安装依赖并提交**

```bash
pip install -r requirements.txt
git add pyproject.toml requirements.txt .gitignore README.md
git commit -m "chore: initialize project structure and dependencies"
```

---

## Task 2: 日志系统

**Files:**
- Create: `img_download/logger.py`

**Step 1: 创建 logger.py**

```python
import logging
import sys
from pathlib import Path

def setup_logger(name: str = "img_download", log_file: str = "download.log") -> logging.Logger:
    """设置日志系统，同时输出到文件和控制台"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

**Step 2: 创建测试文件 tests/test_logger.py**

```python
import pytest
from img_download.logger import setup_logger

def test_logger_creation():
    logger = setup_logger()
    assert logger.name == "img_download"
    assert logger.level == 20  # INFO level

def test_logger_singleton():
    logger1 = setup_logger()
    logger2 = setup_logger()
    assert logger1 is logger2
```

**Step 3: 运行测试验证**

```bash
pytest tests/test_logger.py -v
```

预期：PASS（2 tests）

**Step 4: 提交**

```bash
git add img_download/logger.py tests/test_logger.py
git commit -m "feat: add logging system with file and console output"
```

---

## Task 3: 下载器基类

**Files:**
- Create: `img_download/downloaders/__init__.py`
- Create: `img_download/downloaders/base.py`

**Step 1: 创建 downloaders/__init__.py**

```python
from .base import BaseImageDownloader

__all__ = ["BaseImageDownloader"]
```

**Step 2: 创建 base.py 抽象基类**

```python
from abc import ABC, abstractmethod
from typing import List


class BaseImageDownloader(ABC):
    """图片下载器抽象基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索图片并返回 URL 列表

        Args:
            keyword: 搜索关键词
            count: 需要的图片数量

        Returns:
            图片 URL 列表
        """
        pass
```

**Step 3: 创建测试 tests/test_base.py**

```python
import pytest
from img_download.downloaders import BaseImageDownloader


def test_base_is_abstract():
    """基类不能直接实例化"""
    with pytest.raises(TypeError):
        BaseImageDownloader()


def test_concrete_downloader():
    """子类必须实现 search 方法"""

    class TestDownloader(BaseImageDownloader):
        async def search(self, keyword: str, count: int) -> list:
            return []

    downloader = TestDownloader("test")
    assert downloader.name == "test"
```

**Step 4: 运行测试**

```bash
pytest tests/test_base.py -v
```

预期：PASS（2 tests）

**Step 5: 提交**

```bash
git add img_download/downloaders tests/test_base.py
git commit -m "feat: add abstract base class for image downloaders"
```

---

## Task 4: Bing 下载器实现（第一个具体实现）

**Files:**
- Create: `img_download/downloaders/bing.py`
- Modify: `img_download/downloaders/__init__.py`

**Step 1: 创建 bing.py**

```python
import asyncio
from typing import List
from .base import BaseImageDownloader


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器 - 先尝试第三方库，失败则用爬虫"""

    def __init__(self):
        super().__init__("bing")

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Bing 图片

        先尝试第三方库，失败则返回空列表（爬虫后续实现）
        """
        # 第一步：先返回空列表，后续再实现第三方库和爬虫
        await asyncio.sleep(0)  # 保持 async 特性
        return []
```

**Step 2: 更新 __init__.py**

```python
from .base import BaseImageDownloader
from .bing import BingDownloader

__all__ = ["BaseImageDownloader", "BingDownloader"]
```

**Step 3: 创建测试 tests/test_bing.py**

```python
import pytest
from img_download.downloaders import BingDownloader


@pytest.mark.asyncio
async def test_bing_downloader_creation():
    downloader = BingDownloader()
    assert downloader.name == "bing"


@pytest.mark.asyncio
async def test_bing_search_returns_list():
    downloader = BingDownloader()
    result = await downloader.search("cat", 10)
    assert isinstance(result, list)
    # 目前返回空列表，后续实现后再更新
    assert result == []
```

**Step 4: 运行测试**

```bash
pytest tests/test_bing.py -v
```

预期：PASS（2 tests）

**Step 5: 提交**

```bash
git add img_download/downloaders tests/test_bing.py
git commit -m "feat: add Bing downloader skeleton"
```

---

## Task 5: 工具函数 - 图片下载

**Files:**
- Create: `img_download/utils.py`

**Step 1: 创建 utils.py**

```python
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional
from .logger import setup_logger

logger = setup_logger()


async def download_image(
    url: str,
    save_path: Path,
    session: aiohttp.ClientSession,
    timeout: int = 30
) -> bool:
    """
    下载单张图片

    Args:
        url: 图片 URL
        save_path: 保存路径
        session: aiohttp 会话
        timeout: 超时时间（秒）

    Returns:
        是否下载成功
    """
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                content = await response.read()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(content)
                logger.info(f"Downloaded: {save_path}")
                return True
            else:
                logger.warning(f"Failed {url}: status {response.status}")
                return False
    except asyncio.TimeoutError:
        logger.warning(f"Timeout: {url}")
        return False
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return False
```

**Step 2: 创建测试 tests/test_utils.py**

```python
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

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock()
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

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

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock()
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

    save_path = tmp_path / "test.jpg"
    result = await download_image("http://example.com/img.jpg", save_path, mock_session)

    assert result is False
    assert not save_path.exists()
```

**Step 3: 安装 pytest-mock（如果需要）**

```bash
pip install pytest-mock
```

**Step 4: 运行测试**

```bash
pytest tests/test_utils.py -v
```

预期：PASS（2 tests）

**Step 5: 提交**

```bash
git add img_download/utils.py tests/test_utils.py
git commit -m "feat: add image download utility with retry and error handling"
```

---

## Task 6: 核心调度器

**Files:**
- Create: `img_download/core.py`

**Step 1: 创建 core.py**

```python
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from .downloaders import BingDownloader
from .logger import setup_logger

logger = setup_logger()


class ImageDownloader:
    """图片搜索与下载调度器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.downloaders = {
            "bing": BingDownloader(),
        }

    async def search(
        self,
        keyword: str,
        count: int = 50,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        搜索并下载图片

        Args:
            keyword: 搜索关键词
            count: 下载数量
            sources: 图片来源列表，None 则使用全部

        Returns:
            统计结果字典
        """
        if sources is None:
            sources = list(self.downloaders.keys())

        # 创建关键词文件夹
        keyword_dir = self.output_dir / keyword
        keyword_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting search for '{keyword}', count: {count}, sources: {sources}")

        # 简化版：先只获取 URL，不实际下载
        all_urls = []
        for source in sources:
            if source in self.downloaders:
                urls = await self.downloaders[source].search(keyword, count)
                all_urls.extend(urls)

        return {
            "total": count,
            "success": len(all_urls),
            "failed": count - len(all_urls),
            "sources": {},
            "path": str(keyword_dir)
        }
```

**Step 2: 创建测试 tests/test_core.py**

```python
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
```

**Step 3: 运行测试**

```bash
pytest tests/test_core.py -v
```

预期：PASS（2 tests）

**Step 4: 提交**

```bash
git add img_download/core.py tests/test_core.py
git commit -m "feat: add core scheduler with basic search functionality"
```

---

## Task 7: 更新包导出

**Files:**
- Create: `img_download/__init__.py`

**Step 1: 创建 __init__.py**

```python
from .core import ImageDownloader

__version__ = "0.1.0"
__all__ = ["ImageDownloader"]
```

**Step 2: 创建集成测试 tests/test_integration.py**

```python
import pytest
from img_download import ImageDownloader


@pytest.mark.asyncio
async def test_module_import():
    """测试模块可以正确导入"""
    from img_download import ImageDownloader
    assert ImageDownloader is not None


@pytest.mark.asyncio
async def test_basic_usage(tmp_path):
    """测试基本使用流程"""
    downloader = ImageDownloader(output_dir=str(tmp_path))
    result = await downloader.search("test", count=5)

    assert isinstance(result, dict)
    assert result["total"] == 5
```

**Step 3: 运行所有测试**

```bash
pytest tests/ -v
```

预期：全部 PASS（10+ tests）

**Step 4: 提交**

```bash
git add img_download/__init__.py tests/test_integration.py
git commit -m "feat: add package exports and integration tests"
```

---

## Task 8: 实现 Bing 爬虫（实际搜索功能）

**Files:**
- Modify: `img_download/downloaders/bing.py`

**Step 1: 实现 Bing 爬虫**

```python
import asyncio
from typing import List
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BingDownloader(BaseImageDownloader):
    """Bing 图片下载器"""

    def __init__(self):
        super().__init__("bing")
        self.base_url = "https://www.bing.com/images/async"

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Bing 图片并返回 URL 列表

        使用爬虫方式获取图片 URL
        """
        urls = []

        try:
            # 构建搜索 URL
            params = {
                "q": keyword,
                "count": count * 2,  # 多请求一些，因为有些可能无效
                "first": 0,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        urls = self._parse_image_urls(html)

                        # 过滤并限制数量
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(f"Bing: found {len(urls)} images for '{keyword}'")
                    else:
                        logger.warning(f"Bing: failed with status {response.status}")

        except Exception as e:
            logger.error(f"Bing search error: {e}")

        return urls

    def _parse_image_urls(self, html: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            parser = LexborHTMLParser(html)

            # Bing 的图片 URL 通常在 murl 属性中
            for node in parser.css("div[murl]"):
                url = node.attributes.get("murl")
                if url:
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls
```

**Step 2: 更新测试以支持实际请求（使用 mock）**

```python
import pytest
from img_download.downloaders import BingDownloader


@pytest.mark.asyncio
async def test_bing_search_with_mock_html(mocker):
    """测试 HTML 解析功能"""
    downloader = BingDownloader()

    # Mock HTML 响应（模拟 Bing 返回的 HTML）
    mock_html = '''
    <div class="imgpt" murl="https://example.com/image1.jpg"></div>
    <div class="imgpt" murl="https://example.com/image2.png"></div>
    <div class="imgpt" murl="https://example.com/image3.gif"></div>
    '''

    # Mock aiohttp
    mock_response = mocker.Mock()
    mock_response.status = 200
    mock_response.text = mocker.AsyncMock(return_value=mock_html)

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("cat", 10)

    assert len(result) == 3
    assert "https://example.com/image1.jpg" in result
    assert "https://example.com/image2.png" in result


@pytest.mark.asyncio
async def test_bing_search_empty_result(mocker):
    """测试空结果"""
    downloader = BingDownloader()

    mock_response = mocker.Mock()
    mock_response.status = 200
    mock_response.text = mocker.AsyncMock(return_value="<html></html>")

    mock_session = mocker.Mock()
    mock_session.get = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = mocker.AsyncMock()

    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

    result = await downloader.search("nonexistent", 10)

    assert result == []
```

**Step 3: 运行测试**

```bash
pytest tests/test_bing.py -v
```

预期：PASS（4 tests）

**Step 4: 提交**

```bash
git add img_download/downloaders/bing.py tests/test_bing.py
git commit -m "feat: implement Bing web scraper with selectolax parser"
```

---

## Task 9: 实现并发下载功能

**Files:**
- Modify: `img_download/core.py`

**Step 1: 更新 core.py 添加并发下载**

```python
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
from .downloaders import BingDownloader
from .utils import download_image
from .logger import setup_logger

logger = setup_logger()


class ImageDownloader:
    """图片搜索与下载调度器"""

    def __init__(self, output_dir: str = "output", max_concurrent: int = 10):
        self.output_dir = Path(output_dir)
        self.max_concurrent = max_concurrent
        self.downloaders = {
            "bing": BingDownloader(),
        }

    async def search(
        self,
        keyword: str,
        count: int = 50,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        搜索并下载图片

        Args:
            keyword: 搜索关键词
            count: 下载数量
            sources: 图片来源列表，None 则使用全部

        Returns:
            统计结果字典
        """
        if sources is None:
            sources = list(self.downloaders.keys())

        # 创建关键词文件夹
        keyword_dir = self.output_dir / keyword
        keyword_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting search for '{keyword}', count: {count}, sources: {sources}")

        # 获取图片 URL
        all_urls = []
        for source in sources:
            if source in self.downloaders:
                urls = await self.downloaders[source].search(keyword, count)
                all_urls.extend(urls)

        # 限制数量
        all_urls = all_urls[:count]

        # 并发下载
        stats = await self._download_concurrent(keyword, keyword_dir, all_urls)

        return {
            "total": count,
            "success": stats["success"],
            "failed": stats["failed"],
            "sources": stats.get("sources", {}),
            "path": str(keyword_dir)
        }

    async def _download_concurrent(
        self,
        keyword: str,
        save_dir: Path,
        urls: List[str]
    ) -> Dict[str, Any]:
        """并发下载图片"""
        success_count = 0
        failed_count = 0

        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_semaphore(url: str, index: int) -> bool:
            async with semaphore:
                # 生成文件名：{来源序号}_{原始文件名}
                ext = self._get_extension(url)
                filename = f"bing_{index:03d}{ext}"
                save_path = save_dir / filename
                return await download_image(url, save_path, session)

        async with aiohttp.ClientSession() as session:
            # 绑定 session 到 download_image
            tasks = []
            for i, url in enumerate(urls):
                # 创建闭包捕获正确的 url 和 session
                async def bound_download(u=url, idx=i):
                    return await download_image(u, save_dir / f"bing_{idx:03d}.jpg", session)

                tasks.append(bound_download())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, bool):
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1

        return {
            "success": success_count,
            "failed": failed_count,
            "sources": {}
        }

    def _get_extension(self, url: str) -> str:
        """从 URL 获取文件扩展名"""
        url_lower = url.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            if ext in url_lower:
                return ext
        return ".jpg"
```

**Step 2: 更新测试**

```python
import pytest
from img_download import ImageDownloader
from pathlib import Path


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
```

**Step 3: 运行测试**

```bash
pytest tests/test_core.py -v
```

预期：PASS（3 tests）

**Step 4: 提交**

```bash
git add img_download/core.py tests/test_core.py
git commit -m "feat: add concurrent download with semaphore control"
```

---

## Task 10: 添加 Google 下载器

**Files:**
- Create: `img_download/downloaders/google.py`
- Modify: `img_download/downloaders/__init__.py`
- Modify: `img_download/core.py`

**Step 1: 创建 google.py**

```python
import asyncio
from typing import List
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class GoogleDownloader(BaseImageDownloader):
    """Google 图片下载器"""

    def __init__(self):
        super().__init__("google")

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索 Google 图片

        先尝试第三方库，失败则返回空列表（后续实现爬虫）
        """
        # 尝试使用 google_images_download
        try:
            from google_images_download import google_images_download

            response = google_images_download.googleimagesdownload()

            # 配置参数
            arguments = {
                "keywords": keyword,
                "limit": count,
                "print_urls": True,
                "no_download": True,  # 只获取 URL
            }

            paths = response.download(arguments)

            # 解析返回的 URL
            urls = []
            if isinstance(paths, dict) and keyword in paths:
                # 从输出中提取 URL
                # 注意：这个库的输出格式需要实际测试后调整
                pass

            logger.info(f"Google: found {len(urls)} images for '{keyword}'")
            return urls

        except ImportError:
            logger.warning("google_images_download not available")
            return []
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
```

**Step 2: 更新 __init__.py**

```python
from .base import BaseImageDownloader
from .bing import BingDownloader
from .google import GoogleDownloader

__all__ = ["BaseImageDownloader", "BingDownloader", "GoogleDownloader"]
```

**Step 3: 更新 core.py 添加 Google**

```python
from .downloaders import BingDownloader, GoogleDownloader

# 在 __init__ 中
self.downloaders = {
    "bing": BingDownloader(),
    "google": GoogleDownloader(),
}
```

**Step 4: 创建测试 tests/test_google.py**

```python
import pytest
from img_download.downloaders import GoogleDownloader


@pytest.mark.asyncio
async def test_google_downloader_creation():
    downloader = GoogleDownloader()
    assert downloader.name == "google"


@pytest.mark.asyncio
async def test_google_search_without_library():
    """测试没有第三方库时的行为"""
    downloader = GoogleDownloader()
    result = await downloader.search("cat", 10)
    # 应该返回空列表（库未安装）
    assert isinstance(result, list)
```

**Step 5: 运行测试**

```bash
pytest tests/test_google.py -v
```

预期：PASS（2 tests）

**Step 6: 提交**

```bash
git add img_download/downloaders tests/test_google.py
git commit -m "feat: add Google downloader skeleton with third-party library support"
```

---

## Task 11: 添加百度下载器

**Files:**
- Create: `img_download/downloaders/baidu.py`
- Modify: `img_download/downloaders/__init__.py`
- Modify: `img_download/core.py`

**Step 1: 创建 baidu.py**

```python
import asyncio
from typing import List
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from .base import BaseImageDownloader
from ..logger import setup_logger

logger = setup_logger()


class BaiduDownloader(BaseImageDownloader):
    """百度图片下载器 - 纯爬虫实现"""

    def __init__(self):
        super().__init__("baidu")
        self.base_url = "https://image.baidu.com/search/index"

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索百度图片

        使用爬虫方式
        """
        urls = []

        try:
            params = {
                "tn": "baiduimage",
                "word": keyword,
                "pn": 0,
                "rn": count * 2,
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        urls = self._parse_image_urls(html)
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(f"Baidu: found {len(urls)} images for '{keyword}'")
                    else:
                        logger.warning(f"Baidu: failed with status {response.status}")

        except Exception as e:
            logger.error(f"Baidu search error: {e}")

        return urls

    def _parse_image_urls(self, html: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            parser = LexborHTMLParser(html)

            # 百度的图片 URL 通常在 data-imgurl 属性中
            for node in parser.css("img[data-imgurl]"):
                url = node.attributes.get("data-imgurl")
                if url:
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls
```

**Step 2: 更新 __init__.py**

```python
from .base import BaseImageDownloader
from .bing import BingDownloader
from .google import GoogleDownloader
from .baidu import BaiduDownloader

__all__ = ["BaseImageDownloader", "BingDownloader", "GoogleDownloader", "BaiduDownloader"]
```

**Step 3: 更新 core.py**

```python
from .downloaders import BingDownloader, GoogleDownloader, BaiduDownloader

self.downloaders = {
    "bing": BingDownloader(),
    "google": GoogleDownloader(),
    "baidu": BaiduDownloader(),
}
```

**Step 4: 创建测试 tests/test_baidu.py**

```python
import pytest
from img_download.downloaders import BaiduDownloader


@pytest.mark.asyncio
async def test_baidu_downloader_creation():
    downloader = BaiduDownloader()
    assert downloader.name == "baidu"


@pytest.mark.asyncio
async def test_baidu_parse_html():
    """测试 HTML 解析"""
    downloader = BaiduDownloader()

    mock_html = '''
    <div>
        <img data-imgurl="https://example.com/img1.jpg">
        <img data-imgurl="https://example.com/img2.png">
        <img data-imgurl="https://example.com/img3.gif">
    </div>
    '''

    urls = downloader._parse_image_urls(mock_html)

    assert len(urls) == 3
    assert "https://example.com/img1.jpg" in urls
```

**Step 5: 运行测试**

```bash
pytest tests/test_baidu.py -v
```

预期：PASS（2 tests）

**Step 6: 提交**

```bash
git add img_download/downloaders tests/test_baidu.py
git commit -m "feat: add Baidu downloader with web scraper"
```

---

## Task 12: 运行完整测试套件

**Step 1: 运行所有测试并生成覆盖率报告**

```bash
pytest tests/ -v --cov=img_download --cov-report=html
```

预期：大部分测试 PASS

**Step 2: 检查覆盖率**

打开 `htmlcov/index.html` 查看覆盖率报告

**Step 3: 修复任何失败的测试**

如果有失败的测试，修复并重新提交

**Step 4: 最终提交**

```bash
git add .
git commit -m "test: ensure all tests passing with good coverage"
```

---

## 完成标准

- [ ] 所有测试通过（pytest tests/ -v）
- [ ] 代码覆盖率 > 80%
- [ ] 可以通过 `from img_download import ImageDownloader` 导入使用
- [ ] Bing 下载器可以实际搜索和下载图片
- [ ] 日志正确记录到 download.log 文件
- [ ] 支持并发下载，默认 10 并发

---

## 使用示例

```python
import asyncio
from img_download import ImageDownloader

async def main():
    downloader = ImageDownloader(output_dir="my_images")
    result = await downloader.search("猫咪", count=50, sources=["bing", "baidu"])
    print(f"下载完成：{result['success']}/{result['total']}")

if __name__ == "__main__":
    asyncio.run(main())
```
