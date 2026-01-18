# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行示例
python example.py

# 运行测试
pytest

# 运行特定测试
pytest tests/test_bing.py

# 运行集成测试
pytest tests/integration/

# 运行测试并生成覆盖率报告
pytest --cov=img_download

# 运行诊断工具
python examples/diagnose_bing.py
python examples/verify_webdriver_flag.py
```

## 架构设计

### 核心架构

这是一个异步 Python 图片下载器，支持从多个搜索引擎（百度、Bing、Google）获取图片。采用插件模式架构，每个搜索引擎作为独立的下载器类实现。

```
ImageDownloader (core.py)
    ├── 并行调度多个下载器
    ├── 跨来源全局去重
    └── 信号量控制并发下载

BaseImageDownloader (base.py)
    ├── 所有下载器的抽象基类
    ├── 提供 URL 验证 (_validate_urls)
    └── 定义分页停止条件 (_should_stop)

具体下载器 (downloaders/*.py)
    ├── BaiduDownloader - 使用 JSON API (/search/acjson)
    ├── BingDownloader - HTML 解析 + 会话管理
    ├── GoogleDownloader - 混合 aiohttp + Selenium（受 reCAPTCHA 限制）
    └── SeleniumMixin - 提供 Selenium 回退支持
```

### 关键架构要点

**1. 双模式运行**

- `search()` - 简单模式：获取指定数量的图片，适合快速下载
- `search_with_pagination()` - 高级模式：跨多页获取最大图片数，推荐用于批量下载

**2. 并行源执行**

`core.py:search_with_pagination()` 使用 `asyncio.gather()` 并行运行所有启用的下载器，然后合并结果并进行全局去重。错误处理是隔离的——一个源失败不影响其他源（见 lines 176-178）。

**3. 混合获取策略**

每个下载器实现混合方法：
- 主要方式：`aiohttp` 快速 HTTP 请求
- 回退方式：当 aiohttp 失败时使用 Selenium（适用于有强反爬保护的站点）

参考 `baidu.py:_fetch_page()` 或 `google.py:_fetch_page()` 了解该模式。

**4. 来源可靠性对比**

| 来源 | 可靠性 | 原因 |
|------|--------|------|
| 百度 | 高 | 使用 JSON API，反爬虫弱 |
| Bing | 高 | 反爬虫弱，分页支持好 |
| Google | 有限 | reCAPTCHA 阻止自动化访问 |

**5. BrowserManager 单例**

`drivers/selenium_driver.py:BrowserManager` 是单例，跨所有 Selenium 操作管理单个 Chrome 实例。应用反检测技术：
- 通过 CDP 命令隐藏 `navigator.webdriver` 标志
- 禁用自动化功能 (`--disable-blink-features=AutomationControlled`)
- 设置真实的 User-Agent

### 添加新的图片来源

1. 创建新的下载器类，继承 `BaseImageDownloader`
2. 实现 `search()` 方法（抽象基类要求）
3. 实现 `search_with_pagination()` 方法（推荐）
4. 在 `core.py:ImageDownloader.__init__()` 的 downloaders 字典中注册
5. 添加导入到 `downloaders/__init__.py`

可使用 `SeleniumMixin` 提供 Selenium 回退支持——使用多重继承同时继承 `BaseImageDownloader` 和 `SeleniumMixin`。

### 下载流程

1. 调用 `ImageDownloader.search_with_pagination(keyword)`
2. 并行执行：每个下载器的 `search_with_pagination()` 并发运行
3. 每个下载器：
   - 通过 aiohttp 或 Selenium 获取页面
   - 通过 `_validate_urls()` 验证 URL
   - 返回唯一 URL 的 Set[str]
4. 核心合并结果，全局去重
5. `_download_concurrent()` 通过信号量控制的并发下载所有 URL
6. 来源记录保存到 `{output_dir}/{keyword}/sources.json`

### 重要配置常量

- `max_total_images`（默认 2000）- 每个来源的上限，可通过 ImageDownloader 初始化配置
- `page_size` - 每个下载器的设置（百度：20，Bing：35）
- `max_pages` - 每个下载器的设置（百度：20，Bing：20）
- `max_concurrent`（默认 25）- 同时下载数限制

### 文件命名规范

下载的图片：`{keyword}_{index}{extension}`，索引从 1 开始。

示例：`猫_1.jpg`、`猫_2.png` 等。

### URL 验证机制

`BaseImageDownloader._validate_urls()` 执行并发 GET 请求，使用 Range 头（bytes=0-1023）验证 URL 而不下载完整图片。接受 200 和 206 状态码，对带有图片扩展名的 URL 进行宽松验证。
