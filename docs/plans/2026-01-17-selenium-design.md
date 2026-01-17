# Selenium 增强的百度/谷歌图片搜索设计文档

**日期**: 2026-01-17
**状态**: 设计已确认

## 1. 概述

为解决百度和谷歌图片搜索的反爬虫问题，使用 Selenium 模拟真实浏览器作为备用方案。

**当前问题**：
- 百度 API 返回 HTML 错误页面
- 谷歌无法连接（防火墙/地区限制）

**解决方案**：混合模式 - aiohttp 优先，失败后自动切换到 Selenium

---

## 2. 架构设计

### 新增组件

1. **`img_download/drivers/selenium_driver.py`** - Selenium 浏览器管理器
   - `BrowserManager` 类：单例模式管理浏览器实例
   - 懒加载：首次使用时启动浏览器
   - 空闲超时：5 分钟无操作自动关闭
   - 自动重启：浏览器崩溃时自动恢复

2. **`img_download/downloaders/selenium_mixin.py`** - Selenium 功能混入类
   - 提供 `_fetch_with_selenium()` 方法
   - 实现混合策略：滚动 + 按钮点击
   - 智能重试机制
   - 可配置的 headless 模式

### 修改组件

- `BaiduDownloader` 和 `GoogleDownloader` 继承 `SeleniumMixin`
- 在 `_fetch_page()` 中实现降级策略：先尝试 aiohttp，失败后调用 Selenium

### 数据流

```
用户请求 → Bing(aiohttp) → 成功返回
         → Baidu/Google → aiohttp失败 → Selenium备用 → 成功返回
```

---

## 3. 核心实现

### 3.1 BrowserManager

```python
class BrowserManager:
    """单例模式管理 Chrome 浏览器实例"""

    def __init__(self):
        self._driver: Optional[webdriver.Chrome] = None
        self._last_used: float = 0
        self._idle_timeout = 300  # 5 分钟
        self._headless = True
        self._init_lock = threading.Lock()

    def get_driver(self) -> webdriver.Chrome:
        """获取浏览器实例（懒加载 + 复用）"""
        # 检查浏览器是否崩溃，需要重新创建
        if self._driver is not None:
            try:
                self._driver.current_url  # 测试连接
            except:
                self._driver = None

        # 创建新实例
        if self._driver is None:
            options = self._create_options()
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.set_page_load_timeout(30)

        self._last_used = asyncio.get_event_loop().time()
        return self._driver
```

### 3.2 Chrome 选项配置

```python
def _create_options(self) -> Options:
    """创建 Chrome 选项（推荐配置）"""
    options = Options()

    # 无头模式
    if self._headless:
        options.add_argument('--headless')

    # 性能优化
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--blink-settings=imagesEnabled=false')

    # 窗口大小
    options.add_argument('--window-size=1920,1080')

    return options
```

### 3.3 SeleniumMixin 混入类

```python
class SeleniumMixin:
    """Selenium 功能混入类"""

    selenium_enabled = True
    page_load_timeout = 30
    scroll_pause_time = 2
    max_scroll_attempts = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._browser_manager = BrowserManager()

    async def _fetch_with_selenium(self, keyword: str, page: int = 0) -> List[str]:
        """使用 Selenium 获取图片 URL（备用方案）"""
        driver = self._browser_manager.get_driver()
        url = self._build_selenium_url(keyword, page)
        driver.get(url)

        # 混合加载策略
        self._load_more_content(driver)

        # 提取 URL
        return self._extract_image_urls(driver)
```

### 3.4 混合加载策略

```python
def _load_more_content(self, driver) -> None:
    """混合加载策略：滚动 + 按钮"""
    urls_count = 0

    for attempt in range(self.max_scroll_attempts):
        # 1. 滚动页面
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(self.scroll_pause_time)

        # 2. 检查新内容
        current_urls = len(driver.find_elements(By.TAG_NAME, "img"))
        if current_urls == urls_count:
            # 没有新内容，尝试找按钮
            if not self._try_click_load_more(driver):
                break
        urls_count = current_urls
```

### 3.5 降级策略

```python
async def _fetch_page(self, keyword: str, offset: int, count: int) -> List[str]:
    """获取单页（优先 aiohttp，失败后 Selenium）"""

    # 策略 1: 先尝试 aiohttp
    urls = await self._fetch_with_aiohttp(keyword, offset, count)
    if urls:
        return urls

    # 策略 2: aiohttp 失败，使用 Selenium
    logger.info("aiohttp failed, trying Selenium...")
    page_num = offset // self.page_size
    return await self._fetch_with_selenium(keyword, page_num)
```

---

## 4. 配置

### ImageDownloader 新增参数

```python
class ImageDownloader:
    def __init__(
        self,
        output_dir: str = "output",
        max_concurrent: int = 10,
        # Selenium 配置
        selenium_enabled: bool = True,
        headless: bool = False,
    ):
        ...
```

### 使用示例

```python
# 默认配置（无头模式）
downloader = ImageDownloader()

# 调试时使用有头模式
downloader = ImageDownloader(headless=False)

# 禁用 Selenium（只用 aiohttp）
downloader = ImageDownloader(selenium_enabled=False)
```

---

## 5. 错误处理

### 智能重试策略

| 错误类型 | 重试策略 | 说明 |
|---------|---------|------|
| TimeoutException | 重试 3 次，间隔递增 | 网络问题，可能恢复 |
| NoSuchElementException | 不重试 | 页面结构改变，重试无效 |
| WebDriverException | 重试 5 次 | 浏览器问题，可能恢复 |
| 其他异常 | 重试 3 次 | 未知问题 |

```python
for attempt in range(max_retries):
    try:
        # Selenium 操作
        ...
        return urls
    except TimeoutException:
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
        else:
            logger.error("Max retries exceeded")
    except NoSuchElementException:
        break  # 不重试
```

---

## 6. 测试策略

### 单元测试

- `test_selenium_driver.py` - BrowserManager 单例和配置测试
- `test_baidu.py` - 添加 Selenium mock 测试
- `test_google.py` - 添加 Selenium mock 测试

### 集成测试

- `test_selenium_integration.py` - 真实浏览器测试
- 默认跳过（设置 `SKIP_SELENIUM_TESTS=1` 才运行）

---

## 7. 文件结构

```
img_download/
├── drivers/
│   └── selenium_driver.py          # 新增
├── downloaders/
│   ├── base.py                     # 不变
│   ├── bing.py                     # 不变
│   ├── baidu.py                    # 修改
│   ├── google.py                   # 修改
│   └── selenium_mixin.py           # 新增
└── core.py                         # 修改

tests/
├── test_selenium_driver.py         # 新增
├── test_baidu.py                   # 修改
├── test_google.py                  # 修改
└── test_selenium_integration.py    # 新增
```

---

## 8. 依赖

```toml
[project.dependencies]
selenium = "^4.15.0"
webdriver-manager = "^4.0.0"
```

---

## 9. 预期效果

- **百度**：绕过反爬虫检测，成功获取图片
- **谷歌**：绕过网络限制，成功获取图片
- **Bing**：保持原有快速方式（aiohttp）
- **性能**：aiohttp 成功时无额外开销
- **可靠性**：Selenium 作为备用方案

---

## 10. 实现任务

1. 创建 `selenium_driver.py` - BrowserManager 实现
2. 创建 `selenium_mixin.py` - SeleniumMixin 实现
3. 修改 `baidu.py` - 继承 SeleniumMixin，实现降级策略
4. 修改 `google.py` - 继承 SeleniumMixin，实现降级策略
5. 修改 `core.py` - 添加 Selenium 配置
6. 添加单元测试和集成测试
7. 更新依赖
8. 真实测试验证
