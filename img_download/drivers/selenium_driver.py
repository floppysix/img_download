"""Selenium 浏览器驱动管理器。"""
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import threading
import asyncio


class BrowserManager:
    """单例模式管理 Chrome 浏览器实例"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._driver: Optional[webdriver.Chrome] = None
        self._last_used: float = 0
        self._idle_timeout = 300  # 5 分钟
        self._headless = True
        self._init_lock = threading.Lock()
        self._initialized = True

    def set_headless(self, headless: bool):
        """设置是否无头模式"""
        self._headless = headless

    def get_driver(self) -> webdriver.Chrome:
        """获取浏览器实例（懒加载 + 复用）"""
        with self._init_lock:
            # 检查是否需要关闭旧实例
            if self._driver is not None:
                try:
                    self._driver.current_url  # 测试连接
                except Exception:
                    self._driver = None  # 浏览器崩溃，重新创建

            # 创建新实例
            if self._driver is None:
                options = self._create_options()
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(
                    service=service, options=options
                )
                self._driver.set_page_load_timeout(30)

                # 关键：隐藏 navigator.webdriver 标志
                # 这会修改 JavaScript 的 navigator 属性，使 webdriver 属性返回 undefined
                self._driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": """
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            // 也可以修改 chrome 对象
                            window.chrome = {
                                runtime: {}
                            };
                            // 修改 permissions
                            const originalQuery = window.navigator.permissions.query;
                            window.navigator.permissions.query = (parameters) => (
                                parameters.name === 'notifications' ?
                                    Promise.resolve({ state: Notification.permission }) :
                                    originalQuery(parameters)
                            );
                        """
                    },
                )

            self._last_used = self._get_time()
            return self._driver

    def _create_options(self) -> Options:
        """创建 Chrome 选项（推荐配置 + 反自动化检测）"""
        options = Options()

        # 无头模式
        if self._headless:
            options.add_argument("--headless=new")  # 使用新版无头模式

        # 性能优化
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # 窗口大小
        options.add_argument("--window-size=1920,1080")

        # 反自动化检测（防止 Google 等网站检测到 Selenium）
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # 设置更真实的 User-Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # 禁用 WebDriver 标志（通过执行脚本）
        # 注意：这会在 driver 创建后执行

        return options

    def _get_time(self) -> float:
        """获取当前时间"""
        try:
            loop = asyncio.get_event_loop()
            return loop.time()
        except RuntimeError:
            import time
            return time.time()

    def cleanup_if_idle(self):
        """空闲超时自动关闭"""
        if self._driver is None:
            return

        current_time = self._get_time()
        if current_time - self._last_used > self._idle_timeout:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def close(self):
        """强制关闭浏览器"""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
