#!/usr/bin/env python3
"""
图片下载器使用示例 - 优化版

演示如何使用 img_download 模块搜索并下载大量图片
"""
import asyncio
from img_download import ImageDownloader


async def example_max_collection():
    """示例 1: 最大化收集（每个来源最多 2000 张）"""
    print("=" * 60)
    print("示例 1: 最大化收集图片")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=25,        # 提高并发数
        selenium_enabled=True,
        headless=True,
        verbose=False,           # 非详细模式，每 100 张打印一次进度
        max_total_images=1000   # 每个来源最多 1000 张
    )

    results = await downloader.search_with_pagination(
        keyword="阿里伯克级驱逐舰",
        sources=["baidu", "bing", "google"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_custom_limit():
    """示例 2: 自定义每个来源的上限"""
    print("\n" + "=" * 60)
    print("示例 2: 自定义上限（每来源 500 张）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=25,
        selenium_enabled=True,
        headless=True,
        verbose=False,
        max_total_images=500     # 每个来源最多 500 张
    )

    # 也可以在创建后修改特定来源的上限
    downloader.downloaders["baidu"].max_total_images = 1000
    downloader.downloaders["google"].max_total_images = 300

    results = await downloader.search_with_pagination(
        keyword="美食",
        sources=["baidu", "google"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_debug_mode():
    """示例 3: 调试模式（详细日志）"""
    print("\n" + "=" * 60)
    print("示例 3: 调试模式（详细日志）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=5,          # 降低并发便于观察
        selenium_enabled=True,
        headless=False,           # 显示浏览器窗口
        verbose=True,             # 详细日志（每张图片都打印）
        max_total_images=50       # 只下载少量用于测试
    )

    results = await downloader.search_with_pagination(
        keyword="汽车",
        sources=["baidu"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def main():
    """运行示例"""
    print("\n" + "=" * 60)
    print("图片下载器 - 优化版使用示例")
    print("=" * 60)

    # 选择要运行的示例（取消注释想要运行的示例）
    await example_max_collection()
    # await example_custom_limit()
    # await example_debug_mode()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
