#!/usr/bin/env python3
"""
图片下载器使用示例

演示如何使用 img_download 模块搜索并下载图片
"""
import asyncio
from img_download import ImageDownloader


async def example_basic_search():
    """示例 1: 基础搜索 - 指定数量"""
    print("=" * 60)
    print("示例 1: 基础搜索")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=10
    )

    # 搜索并下载 20 张猫的图片
    results = await downloader.search(
        keyword="猫",
        count=20,
        sources=["baidu", "bing"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_pagination():
    """示例 2: 分页搜索 - 获取更多结果"""
    print("\n" + "=" * 60)
    print("示例 2: 分页搜索（自动获取多页）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=5
    )

    # 分页搜索，自动获取多页直到达到限制
    # 可以获取比基础搜索更多的图片
    results = await downloader.search_with_pagination(
        keyword="熊猫",
        sources=["baidu", "bing", "google"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")

    # 读取来源统计
    import json
    from pathlib import Path
    sources_file = Path("downloads/熊猫/sources.json")
    if sources_file.exists():
        with open(sources_file, "r", encoding="utf-8") as f:
            sources = json.load(f)

        print(f"\n各来源统计:")
        source_counts = {}
        for item in sources:
            src = item.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        for source, count in sorted(source_counts.items()):
            print(f"  {source}: {count}")


async def example_with_selenium():
    """示例 3: 使用 Selenium 备用方案"""
    print("\n" + "=" * 60)
    print("示例 3: 使用 Selenium（当 aiohttp 失败时自动启用）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        selenium_enabled=True,  # 启用 Selenium 备用方案
        headless=True,          # 无头模式（不显示浏览器窗口）
        max_concurrent=5
    )

    # 限制百度和谷歌的页数
    downloader.downloaders["baidu"].max_pages = 3
    downloader.downloaders["google"].max_pages = 2

    results = await downloader.search_with_pagination(
        keyword="风景",
        sources=["baidu", "bing", "google"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_single_source():
    """示例 4: 只使用特定搜索引擎"""
    print("\n" + "=" * 60)
    print("示例 4: 只使用百度")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        selenium_enabled=True
    )

    # 只使用百度搜索
    results = await downloader.search_with_pagination(
        keyword="汽车",
        sources=["baidu"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_custom_config():
    """示例 5: 自定义配置"""
    print("\n" + "=" * 60)
    print("示例 5: 自定义配置")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="my_images",     # 自定义输出目录
        max_concurrent=3,           # 限制并发数（避免网络压力）
        selenium_enabled=True,      # 启用 Selenium
        headless=False             # 显示浏览器窗口（用于调试）
    )

    # 自定义每源页数
    downloader.downloaders["baidu"].max_pages = 5
    downloader.downloaders["bing"].max_pages = 3
    downloader.downloaders["google"].max_pages = 2

    results = await downloader.search_with_pagination(
        keyword="美食",
        sources=["baidu", "bing", "google"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("图片下载器 - 使用示例")
    print("=" * 60)

    # 选择要运行的示例（取消注释想要运行的示例）

    # await example_basic_search()
    # await example_pagination()
    # await example_with_selenium()
    # await example_single_source()
    await example_custom_config()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
