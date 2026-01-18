#!/usr/bin/env python3
"""
图片下载器使用示例

演示如何使用 img_download 模块搜索并下载图片

支持的图片来源:
  - baidu: 百度图片 (推荐 - 使用 JSON API，稳定可靠)
  - bing: Bing 图片 (推荐 - 反爬虫较弱，分页支持好)
  - google: Google 图片 (有限支持 - 受 reCAPTCHA 限制)

Bing 模式选择:
  - aiohttp 模式 (默认): 快速轻量，但抓取数量较少（约 100-200 张）
  - Selenium 模式 (推荐): 抓取数量更多（约 300-500 张），速度相当

使用方式:
  downloader = ImageDownloader(bing_use_selenium=True)  # 启用 Selenium 模式

注意事项:
  - Google 图片搜索会触发 reCAPTCHA 验证，可能无法正常工作
  - 建议优先使用 baidu + bing 来源
  - 分页搜索可获取更多图片（最多 2000 张/来源）
  - Bing 推荐使用 Selenium 模式以获得更多结果
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
        max_concurrent=10,
        verbose=True  # 显示每张图片的下载进度
    )

    # 搜索并下载 20 张猫的图片
    results = await downloader.search(
        keyword="猫",
        count=20,
        sources=["baidu", "bing"]  # 推荐：使用稳定来源
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  保存路径: {results['path']}")


async def example_pagination():
    """示例 2: 分页搜索 - 获取更多结果（推荐）"""
    print("\n" + "=" * 60)
    print("示例 2: 分页搜索（自动获取多页）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=20,           # 并发下载数
        selenium_enabled=True,        # 启用 Selenium 备用方案
        headless=True,                # 无头模式
        verbose=False,                # 简化日志输出
        max_total_images=500          # 每个来源最多 500 张
    )

    # 分页搜索，自动获取多页直到达到限制
    # 可以获取比基础搜索更多的图片
    results = await downloader.search_with_pagination(
        keyword="熊猫",
        sources=["baidu", "bing"]     # 推荐配置：百度 + Bing
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  保存路径: {results['path']}")

    # 显示各来源统计
    if results.get('sources'):
        print(f"\n各来源统计:")
        for source, stats in results['sources'].items():
            print(f"  {source}:")
            print(f"    成功: {stats['success']}")
            print(f"    失败: {stats['failed']}")


async def example_high_volume():
    """示例 3: 大量下载（1000+ 图片）- 使用 Selenium 模式"""
    print("\n" + "=" * 60)
    print("示例 3: 大量下载（1000 张图片）- Selenium 模式")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=25,            # 高并发
        selenium_enabled=True,
        headless=True,
        verbose=False,                # 简化日志，避免刷屏
        max_total_images=1000,        # 每个来源最多 1000 张
        bing_use_selenium=True        # ⭐ 使用 Selenium 模式抓取 Bing（推荐）
    )

    # 自定义每个来源的分页配置
    downloader.downloaders["baidu"].page_size = 20   # 每页 20 张
    downloader.downloaders["baidu"].max_pages = 50   # 最多 50 页

    downloader.downloaders["bing"].page_size = 35    # 每页 35 张
    downloader.downloaders["bing"].max_pages = 50    # 最多 50 页
    downloader.downloaders["bing"].selenium_max_scrolls = 20  # Selenium 最大滚动次数

    results = await downloader.search_with_pagination(
        keyword="阿里伯克级驱逐舰",
        sources=["baidu", "bing"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")

    # 显示各来源统计
    if results.get('sources'):
        print(f"\n各来源统计:")
        for source, stats in results['sources'].items():
            print(f"  {source}:")
            print(f"    成功: {stats['success']}")
            print(f"    失败: {stats['failed']}")


async def example_single_source():
    """示例 4: 只使用特定搜索引擎"""
    print("\n" + "=" * 60)
    print("示例 4: 只使用百度")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=20,
        selenium_enabled=True,
        verbose=True
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


async def example_debug_mode():
    """示例 5: 调试模式（显示浏览器）"""
    print("\n" + "=" * 60)
    print("示例 5: 调试模式（显示浏览器窗口）")
    print("=" * 60)

    downloader = ImageDownloader(
        output_dir="downloads",
        max_concurrent=5,             # 降低并发以便观察
        selenium_enabled=True,
        headless=False,               # 显示浏览器窗口（用于调试）
        verbose=True,
        max_total_images=50,          # 少量图片用于测试
        bing_use_selenium=True        # 使用 Selenium 模式
    )

    results = await downloader.search_with_pagination(
        keyword="测试",
        sources=["baidu", "bing"]
    )

    print(f"\n下载完成:")
    print(f"  总数: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")


async def example_bing_mode_comparison():
    """示例 6: Bing 模式对比"""
    print("\n" + "=" * 60)
    print("示例 6: Bing 模式对比")
    print("=" * 60)

    import time

    keyword = "测试"
    target_count = 100

    # aiohttp 模式
    print("\n--- aiohttp 模式 ---")
    downloader1 = ImageDownloader(
        output_dir="downloads",
        max_concurrent=20,
        selenium_enabled=True,
        headless=True,
        verbose=False,
        max_total_images=target_count,
        bing_use_selenium=False  # aiohttp 模式
    )
    downloader1.downloaders["bing"].max_pages = 5

    start = time.time()
    results1 = await downloader1.search_with_pagination(
        keyword=keyword,
        sources=["bing"]
    )
    time1 = time.time() - start
    bing_count1 = results1['sources']['bing']['success']

    print(f"  耗时: {time1:.1f} 秒")
    print(f"  Bing 抓取: {bing_count1} 张")
    print(f"  速度: {bing_count1/time1:.1f} 张/秒")

    # Selenium 模式
    print("\n--- Selenium 模式 ---")
    downloader2 = ImageDownloader(
        output_dir="downloads",
        max_concurrent=20,
        selenium_enabled=True,
        headless=True,
        verbose=False,
        max_total_images=target_count,
        bing_use_selenium=True  # Selenium 模式
    )
    downloader2.downloaders["bing"].selenium_max_scrolls = 5

    start = time.time()
    results2 = await downloader2.search_with_pagination(
        keyword=keyword,
        sources=["bing"]
    )
    time2 = time.time() - start
    bing_count2 = results2['sources']['bing']['success']

    print(f"  耗时: {time2:.1f} 秒")
    print(f"  Bing 抓取: {bing_count2} 张")
    print(f"  速度: {bing_count2/time2:.1f} 张/秒")

    # 对比
    print(f"\n--- 对比结果 ---")
    print(f"  数量差异: {bing_count2 - bing_count1:+d} 张 ({(bing_count2/bing_count1-1)*100:+.1f}%)")
    print(f"  速度差异: {bing_count2/time2 - bing_count1/time1:+.1f} 张/秒")


async def main():
    """运行示例"""
    print("\n" + "=" * 60)
    print("图片下载器 - 使用示例")
    print("=" * 60)

    # 选择要运行的示例（取消注释想要运行的示例）

    # 基础使用
    # await example_basic_search()

    # 分页搜索（推荐）
    # await example_pagination()

    # 大量下载 - 使用 Selenium 模式（推荐）
    await example_high_volume()

    # 单一来源
    # await example_single_source()

    # 调试模式
    # await example_debug_mode()

    # Bing 模式对比
    # await example_bing_mode_comparison()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
