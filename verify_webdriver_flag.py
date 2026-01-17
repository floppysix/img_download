#!/usr/bin/env python3
"""验证 Selenium 是否成功隐藏了 navigator.webdriver 标志"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def test_webdriver_hidden():
    """测试 navigator.webdriver 是否被隐藏"""
    options = Options()

    # 添加反检测选项
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 设置 User-Agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # 无头模式
    options.add_argument("--headless=new")

    # 性能优化
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 关键：隐藏 navigator.webdriver 标志
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            """
        },
    )

    # 访问一个测试页面
    driver.get("https://www.google.com")

    # 检查 navigator.webdriver 的值
    webdriver_value = driver.execute_script("return navigator.webdriver;")
    user_agent = driver.execute_script("return navigator.userAgent;")

    print(f"navigator.webdriver: {webdriver_value}")
    print(f"User-Agent: {user_agent}")

    # 访问 Google Images 测试是否会被重定向
    driver.get("https://www.google.com/search?tbm=isch&q=cat")
    current_url = driver.current_url
    print(f"\n尝试访问 Google Images...")
    print(f"当前 URL: {current_url}")

    if "tbm=isch" in current_url or "udm=2" not in current_url:
        print("[SUCCESS] Google Images 访问成功！没有被重定向！")
    else:
        print("[FAIL] 仍被重定向到普通搜索")

    driver.quit()


if __name__ == "__main__":
    print("=" * 60)
    print("测试 navigator.webdriver 隐藏功能")
    print("=" * 60)
    test_webdriver_hidden()
