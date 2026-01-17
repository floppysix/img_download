"""Selenium 功能混入类。"""
from typing import List
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from ..drivers.selenium_driver import BrowserManager
from ..logger import setup_logger

logger = setup_logger()


class SeleniumMixin:
    """Selenium 功能混入类，为下载器提供备用方案"""

    # Selenium 配置（优化版）
    selenium_enabled = True
    page_load_timeout = 30
    scroll_pause_time = 1  # 减少等待时间：2秒 → 1秒
    max_scroll_attempts = 5  # 限制滚动次数：100 → 5次（性能优化）
    max_total_images = 2000  # 每个来源最多收集的图片数
    empty_scroll_tolerance = 2  # 连续 N 次滚动无新内容时停止：3 → 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._browser_manager = BrowserManager()
        self._collected_urls = set()  # 跟踪已收集的 URL

    def set_headless(self, headless: bool):
        """设置无头模式"""
        self._browser_manager.set_headless(headless)

    async def _fetch_with_selenium(
        self,
        keyword: str,
        page: int = 0,
        max_retries: int = 3
    ) -> List[str]:
        """
        使用 Selenium 获取图片 URL（备用方案）

        Args:
            keyword: 搜索关键词
            page: 页码
            max_retries: 最大重试次数

        Returns:
            图片 URL 列表
        """
        for attempt in range(max_retries):
            driver = None
            try:
                driver = self._browser_manager.get_driver()
                url = self._build_selenium_url(keyword, page)
                driver.get(url)

                # 混合加载策略：滚动 + 按钮
                self._load_more_content(driver)

                # 提取图片 URL
                urls = self._extract_image_urls(driver)

                logger.info(
                    f"Selenium: found {len(urls)} URLs "
                    f"for '{keyword}' (page {page})"
                )
                return urls

            except TimeoutException:
                # 超时：重试，间隔递增
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Selenium: timeout (attempt {attempt + 1}), "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Selenium: max retries exceeded")

            except NoSuchElementException:
                # 元素找不到：页面结构可能变了，不重试
                logger.error(
                    "Selenium: element not found, "
                    "page structure may have changed"
                )
                break

            except Exception as e:
                # 其他错误：重试
                logger.warning(
                    f"Selenium error (attempt {attempt + 1}): {e}"
                )

        return []

    def _build_selenium_url(self, keyword: str, page: int) -> str:
        """
        构建搜索 URL（Selenium 用）

        子类必须实现此方法

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            搜索 URL
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _build_selenium_url"
        )

    def _load_more_content(self, driver) -> None:
        """
        改进的滚动加载策略：滚动直到没有新内容或达到上限

        停止条件：
        1. 连续 N 次滚动没有增加图片数量
        2. 达到 max_total_images 上限

        Args:
            driver: Selenium WebDriver 实例
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By

        urls_count = 0
        empty_count = 0  # 连续无新内容的次数

        # 等待页面加载至少有一些图片
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
        except:
            pass  # 即使没有图片也继续

        for attempt in range(self.max_scroll_attempts):
            # 检查是否已达到上限
            if len(self._collected_urls) >= self.max_total_images:
                logger.info(
                    f"Reached max_total_images limit ({self.max_total_images}), stopping scroll"
                )
                break

            # 1. 滚动到页面底部
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(self.scroll_pause_time)

            # 2. 检查是否有新内容
            try:
                current_urls = len(driver.find_elements(By.TAG_NAME, "img"))
            except Exception:
                current_urls = urls_count

            if current_urls == urls_count:
                # 没有新内容
                empty_count += 1
                if empty_count >= self.empty_scroll_tolerance:
                    # 尝试找"加载更多"按钮
                    if not self._try_click_load_more(driver):
                        logger.info(
                            f"No new content after {self.empty_scroll_tolerance} scrolls, stopping"
                        )
                        break  # 没有按钮了，结束
                    else:
                        empty_count = 0  # 点击了按钮，重置计数
            else:
                # 有新内容，重置空计数
                empty_count = 0
                urls_count = current_urls

    def _try_click_load_more(self, driver) -> bool:
        """
        尝试点击"加载更多"按钮

        使用 JavaScript 点击以避免元素被覆盖的问题

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            是否成功点击
        """
        # 常见的按钮文本（多语言）
        button_texts = [
            "加载更多",
            "Load more",
            "Show more",
            "下一页",
            "Next",
            "更多",
            "Show all results",
        ]

        for text in button_texts:
            try:
                button = driver.find_element(
                    By.XPATH,
                    f"//*[contains(text(), '{text}')]"
                )
                # 使用 JavaScript 点击，避免元素被覆盖的问题
                driver.execute_script("arguments[0].click();", button)
                time.sleep(self.scroll_pause_time)
                return True
            except NoSuchElementException:
                continue
            except Exception:
                # 点击失败，继续尝试下一个按钮
                continue

        return False

    def _extract_image_urls(self, driver) -> List[str]:
        """
        从页面提取图片 URL（Selenium 用）

        子类应该重写此方法以实现特定网站的 URL 提取逻辑

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            图片 URL 列表
        """
        # 默认实现：提取所有 img 标签的 src
        urls = []
        try:
            img_elements = driver.find_elements(By.TAG_NAME, "img")
            for img in img_elements:
                src = img.get_attribute("src")
                if src and src.startswith("http"):
                    urls.append(src)
        except Exception as e:
            logger.warning(f"Error extracting image URLs: {e}")

        return urls
