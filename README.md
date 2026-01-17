# img_download

图片搜索与下载模块 - 支持百度、必应、谷歌三大搜索引擎

## 功能特性

- ✅ 支持百度图片、Bing 图片、Google 图片
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
        max_concurrent=10
    )

    # 下载 50 张猫咪图片
    result = await downloader.search("猫咪", count=50)
    print(f"下载完成：{result['success']}/{result['total']}")

asyncio.run(main())
```

### 分页搜索（获取更多图片）

```python
downloader = ImageDownloader(
    output_dir="downloads",
    selenium_enabled=True,  # 启用 Selenium 备用方案
    headless=True           # 无头模式
)

# 自动分页搜索，可获取数百张图片
result = await downloader.search_with_pagination(
    keyword="熊猫",
    sources=["baidu", "bing", "google"]
)
print(f"总数: {result['total']}, 成功: {result['success']}")
```

## 参数说明

### ImageDownloader

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_dir` | str | "output" | 输出目录 |
| `max_concurrent` | int | 10 | 最大并发下载数 |
| `selenium_enabled` | bool | True | 是否启用 Selenium 备用 |
| `headless` | bool | True | 是否使用无头浏览器 |

### search()

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | str | 必填 | 搜索关键词 |
| `count` | int | 必填 | 下载数量 |
| `sources` | list | ["baidu", "bing", "google"] | 搜索引擎 |

### search_with_pagination()

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyword` | str | 必填 | 搜索关键词 |
| `sources` | list | ["baidu", "bing", "google"] | 搜索引擎 |

## 搜索引擎配置

每源可配置页数限制：

```python
downloader.downloaders["baidu"].max_pages = 5
downloader.downloaders["bing"].max_pages = 3
downloader.downloaders["google"].max_pages = 2
```

## 输出结构

```
output_dir/
├── 关键词/
│   ├── 关键词_1.jpg
│   ├── 关键词_2.jpg
│   ├── ...
│   └── sources.json          # 来源记录
```

## Selenium 使用

当遇到反爬限制时，Selenium 会自动启用：

```python
downloader = ImageDownloader(
    selenium_enabled=True,
    headless=True  # 设为 False 可看到浏览器窗口（用于调试）
)
```

## 完整示例

查看 `example.py` 获取更多使用示例。

运行示例：

```bash
python example.py
```

## 注意事项

1. **网络环境**：Google 在中国可能需要 VPN
2. **并发控制**：建议不超过 20，避免被限制
3. **合法使用**：请遵守目标网站的 robots.txt 和使用条款
