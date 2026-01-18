# img_download

图片搜索与下载模块 - 支持多搜索引擎

## 功能特性

- ✅ **百度图片** - 使用 JSON API，稳定可靠（推荐）
- ✅ **Bing 图片** - 反爬虫较弱，分页支持好（推荐）
- ⚠️ **Google 图片** - 受 reCAPTCHA 限制，可能无法正常工作
- ✅ 异步并发下载，速度快
- ✅ 自动分页，获取大量图片
- ✅ Selenium 备用方案，绕过反爬限制
- ✅ URL 验证，过滤无效链接
- ✅ 来源追踪，记录每张图片的来源
- ✅ 自动去重

## 安装

```bash
pip install -r requirements.txt
```

或：

```bash
pip install aiohttp selectolax selenium webdriver-manager
```

## 快速开始

### 基础用法

```python
import asyncio
from img_download import ImageDownloader

async def main():
    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=10,
        verbose=True  # 显示每张图片的下载进度
    )

    # 下载 50 张猫咪图片（使用百度 + Bing）
    result = await downloader.search(
        keyword="猫咪",
        count=50,
        sources=["baidu", "bing"]  # 推荐配置
    )
    print(f"下载完成：{result['success']}/{result['total']}")

asyncio.run(main())
```

### 分页搜索（获取更多图片）

```python
downloader = ImageDownloader(
    output_dir="downloads",
    max_concurrent=20,
    selenium_enabled=True,     # 启用 Selenium 备用方案
    headless=True,             # 无头模式
    verbose=False,             # 简化日志输出
    max_total_images=500       # 每个来源最多 500 张
)

# 自动分页搜索，可获取数百张图片
result = await downloader.search_with_pagination(
    keyword="熊猫",
    sources=["baidu", "bing"]  # 推荐配置
)
print(f"总数: {result['total']}, 成功: {result['success']}")
```

## 参数说明

### ImageDownloader

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_dir` | str | "output" | 输出目录 |
| `max_concurrent` | int | 25 | 最大并发下载数 |
| `selenium_enabled` | bool | True | 是否启用 Selenium 备用 |
| `headless` | bool | True | 是否使用无头浏览器 |
| `verbose` | bool | True | 是否显示详细日志 |
| `max_total_images` | int | 2000 | 每个来源最多收集的图片数 |

### search()

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | str | 必填 | 搜索关键词 |
| `count` | int | 必填 | 下载数量 |
| `sources` | list | 全部 | 搜索引擎（推荐: ["baidu", "bing"]）|

### search_with_pagination()

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | str | 必填 | 搜索关键词 |
| `sources` | list | 全部 | 搜索引擎（推荐: ["baidu", "bing"]）|

## 搜索引擎配置

每源可配置分页参数：

```python
# 百度配置
downloader.downloaders["baidu"].page_size = 20   # 每页 20 张
downloader.downloaders["baidu"].max_pages = 50   # 最多 50 页

# Bing 配置
downloader.downloaders["bing"].page_size = 35    # 每页 35 张
downloader.downloaders["bing"].max_pages = 30    # 最多 30 页
```

## 输出结构

```
output_dir/
├── 关键词/
│   ├── 关键词_1.jpg
│   ├── 关键词_2.jpg
│   ├── ...
│   └── sources.json          # 来源记录（JSON 格式）
```

`sources.json` 格式示例：

```json
[
  {
    "filename": "关键词_1.jpg",
    "source": "baidu",
    "url": "https://example.com/image.jpg",
    "success": true
  }
]
```

## Selenium 使用

当遇到反爬限制时，Selenium 会自动启用：

```python
downloader = ImageDownloader(
    selenium_enabled=True,
    headless=True,   # 设为 False 可看到浏览器窗口（用于调试）
    verbose=True
)
```

Selenium 已配置反检测技术：
- 隐藏 `navigator.webdriver` 标志
- 禁用自动化检测特征
- 模拟真实浏览器指纹

## 诊断工具

项目包含一些诊断工具帮助排查问题：

| 工具 | 用途 |
|------|------|
| `examples/diagnose_bing.py` | 诊断 Bing 连接问题 |
| `examples/verify_webdriver_flag.py` | 验证 Selenium 反检测配置 |

## 运行示例

```bash
# 基础示例
python example.py

# 诊断 Bing 连接
python examples/diagnose_bing.py

# 验证 WebDriver 配置
python examples/verify_webdriver_flag.py
```

## 注意事项

1. **Google 图片限制**
   - Google 图片搜索会触发 reCAPTCHA 验证
   - 建议优先使用 `baidu` + `bing` 来源
   - 如需使用 Google，可能需要代理或其他绕过方式

2. **网络环境**
   - 建议稳定的网络连接
   - 并发过高可能触发限制

3. **合法使用**
   - 请遵守目标网站的 robots.txt 和使用条款
   - 仅供学习和个人使用

## 项目结构

```
img_download/
├── example.py                 # 使用示例
├── proxy_example.py           # 代理实现示例
├── examples/                  # 诊断和示例工具
│   ├── diagnose_bing.py       # Bing 诊断工具
│   ├── diagnose.py            # Selenium 环境诊断
│   └── verify_webdriver_flag.py  # WebDriver 验证
├── img_download/              # 核心代码
│   ├── __init__.py
│   ├── core.py                # 核心调度器
│   ├── logger.py              # 日志模块
│   ├── utils.py               # 工具函数
│   ├── drivers/               # 驱动管理
│   │   └── selenium_driver.py # Selenium 驱动
│   └── downloaders/           # 下载器实现
│       ├── base.py            # 基类
│       ├── baidu.py           # 百度下载器
│       ├── bing.py            # Bing 下载器
│       ├── google.py          # Google 下载器
│       └── selenium_mixin.py  # Selenium 混入类
└── tests/                     # 测试文件
    ├── integration/           # 集成测试
    └── [单元测试]
```

## 许可

MIT License
