# 图片搜索与下载模块设计文档

**日期**: 2026-01-17
**状态**: 设计已确认

## 1. 概述

设计一个 Python 模块，支持通过关键词搜索并批量下载图片。模块可作为库导入到其他项目中使用。

## 2. 功能需求

| 需求项 | 说明 |
|--------|------|
| 支持来源 | 百度、谷歌、Bing、Pinterest、Unsplash、Pexels、Flickr |
| 下载数量 | 可配置，调用时指定 |
| 保存方式 | 按关键词创建子文件夹 |
| 并发下载 | 支持，默认 5-10 并发 |
| 认证方式 | 优先第三方库，失败则用爬虫兜底（无需 API 密钥） |
| 错误处理 | 打印警告 + 记录日志文件 |

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────┐
│      用户接口层 (API Layer)          │
│  ImageDownloader.search(keyword)     │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│        调度层 (Scheduler)            │
│  任务分配、并发控制、文件管理         │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│      下载器层 (Downloaders)          │
│  各来源下载器（第三方库 + 爬虫兜底）  │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│      通用工具层 (Utils)              │
│  日志、下载、文件操作                │
└─────────────────────────────────────┘
```

### 3.2 用户接口

```python
class ImageDownloader:
    def __init__(self, output_dir: str = "output"):
        ...

    def search(
        self,
        keyword: str,
        count: int = 50,
        sources: List[str] = None
    ) -> Dict[str, Any]:
        """
        搜索并下载图片

        Args:
            keyword: 搜索关键词
            count: 下载数量
            sources: 图片来源列表，None 则使用全部

        Returns:
            {
                "total": int,      # 请求数量
                "success": int,    # 成功数量
                "failed": int,     # 失败数量
                "sources": {...},  # 各来源统计
                "path": str        # 保存路径
            }
        """
```

### 3.3 下载器接口

```python
class BaseImageDownloader(ABC):
    @abstractmethod
    async def search(self, keyword: str, count: int) -> List[str]:
        """返回图片URL列表"""
        pass
```

每个下载器内部逻辑：
1. 尝试使用第三方库
2. 捕获异常，失败则切换爬虫
3. 返回指定数量的 URL

## 4. 数据流

```
用户调用 API
    ↓
调度层分配任务（按来源）
    ↓
下载器并发执行
    ├── 第三方库尝试
    └── 失败则爬虫兜底
    ↓
返回 URL 列表
    ↓
并发下载图片（5-10 并发）
    ↓
保存到 {keyword}/ 文件夹
    ↓
返回统计结果
```

## 5. 项目结构

```
img_download/
├── __init__.py           # 导出 ImageDownloader
├── core.py               # 主调度器
├── downloaders/          # 各来源下载器
│   ├── __init__.py
│   ├── base.py           # 抽象基类
│   ├── baidu.py
│   ├── google.py
│   ├── bing.py
│   ├── pinterest.py
│   ├── unsplash.py
│   ├── pexels.py
│   └── flickr.py
├── utils.py              # 通用工具
└── logger.py             # 日志配置
```

## 6. 依赖库

| 库 | 用途 |
|---|------|
| aiohttp | 异步网络请求 |
| selectolax | 快速 HTML 解析 |
| parsel | 备选解析器 |
| google-images-download | Google 图片第三方库 |
| bing-image-downloader | Bing 图片第三方库 |

## 7. 文件命名规则

- 格式：`{来源序号}_{原始文件名}`
- 示例：`bing_001_cat.jpg`, `google_002_cat.png`
- 保留原始扩展名，无法识别则默认 `.jpg`

## 8. 错误处理

| 场景 | 处理方式 |
|------|----------|
| 单张图片下载失败 | 记录日志，打印警告，继续 |
| 整个来源失败 | 跳过该来源，尝试其他 |
| 网络超时 | 重试 2 次，仍失败则跳过 |
| 磁盘空间不足 | 提前检测，空间不足则终止 |

## 9. 日志系统

- 双输出：`download.log` + 控制台
- 级别：INFO（正常）、WARNING（单张失败）、ERROR（来源失败）
- 格式包含时间戳

## 10. 使用示例

```python
from img_download import ImageDownloader

# 基本用法
downloader = ImageDownloader()
result = downloader.search("猫咪", count=50)
print(f"下载完成：{result['success']}/{result['total']}")

# 指定来源
result = downloader.search("汽车", count=100, sources=["bing", "google"])

# 自定义保存路径
downloader = ImageDownloader(output_dir="my_images")
```
