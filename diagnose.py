#!/usr/bin/env python3
"""诊断脚本 - 检查 Selenium 环境"""
import sys
import asyncio


async def check_imports():
    """检查模块导入"""
    print("=" * 60)
    print("检查模块导入...")
    print("=" * 60)

    try:
        from img_download import ImageDownloader
        print("[OK] img_download 模块导入成功")
    except Exception as e:
        print(f"[FAIL] img_download 导入失败: {e}")
        return False

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        print("[OK] Selenium 模块导入成功")
    except Exception as e:
        print(f"[FAIL] Selenium 导入失败: {e}")
        return False

    return True


async def check_selenium():
    """检查 Selenium 能否启动浏览器"""
    print("\n" + "=" * 60)
    print("检查 Selenium 浏览器启动...")
    print("=" * 60)

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.options import Options

        print("正在启动 Chrome 浏览器...")

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        print("[OK] Chrome 浏览器启动成功")

        # 测试访问百度
        print("正在访问百度图片...")
        driver.get("https://image.baidu.com")
        print(f"[OK] 页面标题: {driver.title}")

        driver.quit()
        print("[OK] 浏览器关闭成功")
        return True

    except Exception as e:
        print(f"[FAIL] Selenium 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_basic_download():
    """测试基础下载功能（只用百度，1页）"""
    print("\n" + "=" * 60)
    print("测试基础下载功能...")
    print("=" * 60)

    try:
        from img_download import ImageDownloader

        print("创建下载器...")
        downloader = ImageDownloader(
            output_dir="test_output",
            selenium_enabled=True,
            headless=True,
            max_concurrent=3
        )

        # 只测试百度，1 页
        downloader.downloaders["baidu"].max_pages = 1

        print("开始下载（百度，猫，1页）...")
        results = await downloader.search_with_pagination(
            keyword="猫",
            sources=["baidu"]
        )

        print(f"\n[OK] 下载完成！")
        print(f"  总数: {results.get('total', 0)}")
        print(f"  成功: {results.get('success', 0)}")
        print(f"  失败: {results.get('failed', 0)}")

        return results.get('success', 0) > 0

    except Exception as e:
        print(f"[FAIL] 下载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有诊断"""
    print("\n" + "=" * 60)
    print("img_download 诊断脚本")
    print("=" * 60)

    # 检查导入
    if not await check_imports():
        print("\n[FAIL] 模块检查失败，请先安装依赖")
        print("请运行: pip install aiohttp selectolax selenium webdriver-manager")
        return

    # 检查 Selenium
    if not await check_selenium():
        print("\n[FAIL] Selenium 检查失败")
        return

    # 检查基础下载
    if not await check_basic_download():
        print("\n[FAIL] 下载功能检查失败")
        return

    print("\n" + "=" * 60)
    print("[SUCCESS] 所有检查通过！模块工作正常")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
