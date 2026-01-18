# img_download

图片搜索与下载模块 - 支持多搜索引擎

## 功能特性

- ✅ **百度图片** - 使用 JSON API，稳定可靠（推荐）
- ✅ **Bing 图片** - 支持 aiohttp/Selenium 双模式（推荐）
- ⚠️ **Google 图片** - 受 reCAPTCHA 限制，可能无法正常工作
- ✅ 异步并发下载，速度快
- ✅ 自动分页，获取大量图片（最多 2000 张/来源）
- ✅ 智能回退机制（百度 aiohttp 失败时自动切换 Selenium）
- ✅ URL 验证，过滤无效链接
- ✅ 来源追踪，记录每张图片的来源
- ✅ 自动去重

## Bing 双模式支持

Bing 下载器支持两种抓取模式，可通过参数选择：

| 模式 | 抓取数量 | 速度 | 适用场景 |
|-----|---------|-----|---------|
| **aiohttp**（默认） | ~100-200 张 | 快速 | 快速少量抓取 |
| **Selenium**（推荐） | ~300-500 张 | 相当 | 大量抓取 |

**实测对比**（关键词：阿里伯克级驱逐舰，目标 1000 张）：

| 项目 | aiohttp | Selenium | 提升 |
|-----|---------|----------|-----|
| Bing 抓取 | 148 张 | 349 张 | **+136%** |
| 总耗时 | 295 秒 | 296 秒 | 相同 |
| 平均速度 | 3.9 张/秒 | 4.6 张/秒 | **+17%** |

## 安装

```bash
pip install -r requirements.txt
```

**依赖版本**（已验证稳定版本）：
- aiohttp==3.10.5
- yarl==1.11.0
- multidict==6.0.4
- brotli
- selenium>=4.0.0

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

### 使用 Selenium 模式抓取 Bing（推荐）

```python
downloader = ImageDownloader(
    output_dir="downloads",
    max_concurrent=20,
    selenium_enabled=True,        # 启用 Selenium
    headless=True,                # 无头模式
    verbose=False,
    max_total_images=1000,        # 每个来源最多 1000 张
    bing_use_selenium=True        # ⭐ Bing 使用 Selenium 模式（推荐）
)

# 自动分页搜索
result = await downloader.search_with_pagination(
    keyword="风景",
    sources=["baidu", "bing"]
)

# 配置 Bing Selenium 参数
downloader.downloaders["bing"].selenium_max_scrolls = 20  # 最大滚动次数
```

### 分页搜索（获取更多图片）

```python
downloader = ImageDownloader(
    output_dir="downloads",
    max_concurrent=20,
    selenium_enabled=True,
    headless=True,
    verbose=False,
    max_total_images=500
)

# 自动分页搜索，可获取数百张图片
result = await downloader.search_with_pagination(
    keyword="熊猫",
    sources=["baidu", "bing"]
)
print(f"总数: {result['total']}, 成功: {result['success']}")
```

## 参数说明

### ImageDownloader

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_dir` | str | "output" | 输出目录 |
| `max_concurrent` | int | 25 | 最大并发下载数 |
| `selenium_enabled` | bool | True | 是否启用 Selenium |
| `headless` | bool | True | 是否使用无头浏览器 |
| `verbose` | bool | True | 是否显示详细日志 |
| `max_total_images` | int | 2000 | 每个来源最多收集的图片数 |
| `bing_use_selenium` | bool | False | **Bing 是否使用 Selenium 模式** |

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

### 百度配置

```python
downloader.downloaders["baidu"].page_size = 20   # 每页 20 张
downloader.downloaders["baidu"].max_pages = 50   # 最多 50 页
```

百度使用 **aiohttp 优先，Selenium 备用** 的智能回退机制：
- 优先使用 aiohttp 请求 JSON API（速度快）
- 失败时自动切换到 Selenium（稳定性高）

### Bing 配置

```python
# aiohttp 模式配置
downloader.downloaders["bing"].page_size = 35    # 每页 35 张
downloader.downloaders["bing"].max_pages = 50    # 最多 50 页
downloader.downloaders["bing"].request_delay_base = 2.5  # 请求间隔（秒）

# Selenium 模式配置
downloader.downloaders["bing"].selenium_max_scrolls = 20  # 最大滚动次数
downloader.downloaders["bing"].selenium_scroll_pause = 2   # 滚动后等待（秒）
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

## 运行示例

```bash
# 基础示例
python example.py

# Bing 模式对比测试
python test_bing_modes.py
```

## 注意事项

1. **Google 图片限制**
   - Google 图片搜索会触发 reCAPTCHA 验证
   - 建议优先使用 `baidu` + `bing` 来源
   - 如需使用 Google，可能需要代理或其他绕过方式

2. **网络环境**
   - 建议稳定的网络连接
   - 并发过高可能触发限制
   - Bing 推荐使用 Selenium 模式以获得更好结果

3. **Brotli 依赖**
   - Bing 返回 brotli 压缩内容
   - 已包含在 requirements.txt 中

4. **合法使用**
   - 请遵守目标网站的 robots.txt 和使用条款
   - 仅供学习和个人使用

## 项目结构

```
img_download/
├── example.py                 # 使用示例
├── proxy_example.py           # 代理实现示例
├── test_bing_modes.py         # Bing 模式对比测试
├── test_full_comparison.py    # 完整性能对比测试
├── CLAUDE.md                  # Claude Code 使用说明
├── README.md                  # 本文件
├── requirements.txt           # 依赖列表
├── img_download/              # 核心代码
│   ├── __init__.py
│   ├── core.py                # 核心调度器
│   ├── logger.py              # 日志模块
│   ├── utils.py               # 工具函数
│   ├── drivers/               # 驱动管理
│   │   └── selenium_driver.py # Selenium 驱动（单例模式）
│   └── downloaders/           # 下载器实现
│       ├── base.py            # 基类
│       ├── baidu.py           # 百度下载器（aiohttp + Selenium 混合）
│       ├── bing.py            # Bing 下载器（双模式支持）
│       ├── google.py          # Google 下载器
│       └── selenium_mixin.py  # Selenium 混入类
└── tests/                     # 测试文件
    ├── integration/           # 集成测试
    └── [单元测试]
```

## 架构设计

### 并行源执行

核心调度器 (`core.py`) 使用 `asyncio.gather()` 并行执行多个下载器：

```python
# 并行运行百度 + Bing
results = await downloader.search_with_pagination(
    keyword="测试",
    sources=["baidu", "bing"]
)
```

### 下载流程

```
1. 并行调度各下载器
   ├── BaiduDownloader: aiohttp → 失败 → Selenium 备用
   └── BingDownloader: aiohttp 模式 或 Selenium 模式

2. 全局去重（跨来源）

3. 并发下载（信号量控制）

4. 保存来源记录
```

### 搜索引擎对比

| 来源 | 方式 | 可靠性 | 抓取数量 |
|-----|------|--------|---------|
| 百度 | aiohttp + Selenium 回退 | 高 | ~1000 张 |
| Bing | aiohttp / Selenium 可选 | 中 | aiohttp: ~150 张<br>Selenium: ~350 张 |
| Google | Selenium | 低 | 受 reCAPTCHA 限制 |

## 许可

MIT License
