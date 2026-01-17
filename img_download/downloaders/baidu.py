from typing import List, Set, Dict, Any
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from .base import BaseImageDownloader
from .selenium_mixin import SeleniumMixin
from ..logger import setup_logger

logger = setup_logger()


class BaiduDownloader(BaseImageDownloader, SeleniumMixin):
    """百度图片下载器 - aiohttp + Selenium 混合模式"""

    # 分页配置参数
    page_size = 20
    max_pages = 20
    max_empty_pages = 2

    # HTTP 请求配置
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36"
    )
    REQUEST_TIMEOUT = 30

    def __init__(self):
        BaseImageDownloader.__init__(self, "baidu")
        SeleniumMixin.__init__(self)
        self.base_url = "https://image.baidu.com/search/index"
        self.api_url = "https://image.baidu.com/search/acjson"

    async def search(self, keyword: str, count: int) -> List[str]:
        """
        搜索百度图片

        使用爬虫方式
        """
        urls = []

        try:
            params: Dict[str, Any] = {
                "tn": "baiduimage",
                "word": keyword,
                "pn": 0,
                "rn": count * 2,
            }

            headers = {"User-Agent": self.USER_AGENT}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        urls = self._parse_image_urls(html)
                        urls = [u for u in urls if u.startswith("http")][:count]
                        logger.info(
                            f"Baidu: found {len(urls)} images "
                            f"for '{keyword}'"
                        )
                    else:
                        logger.warning(
                            f"Baidu: failed with status {response.status}"
                        )

        except Exception as e:
            logger.error(f"Baidu search error: {e}")

        return urls

    async def search_with_pagination(self, keyword: str) -> Set[str]:
        """
        分页搜索百度图片，返回去重后的 URL 集合

        Args:
            keyword: 搜索关键词

        Returns:
            去重后的图片 URL 集合
        """
        all_urls: Set[str] = set()
        empty_count = 0

        for page in range(self.max_pages):
            pn = page * self.page_size

            try:
                # 获取单页数据
                urls = await self._fetch_page(keyword, pn, self.page_size)

                # 验证 URL
                valid_urls = await self._validate_urls(urls)

                # 停止检查
                if len(valid_urls) == 0:
                    empty_count += 1
                    if empty_count >= self.max_empty_pages:
                        break
                    # 空页直接跳过，不添加也不继续
                    continue
                else:
                    empty_count = 0

                # 软性停止：结果数 < 30%
                # 先添加结果，再判断是否停止
                all_urls.update(valid_urls)
                logger.info(
                    f"Baidu page {page + 1}: "
                    f"found {len(valid_urls)} valid URLs "
                    f"(total: {len(all_urls)})"
                )

                if len(valid_urls) < self.page_size * 0.3:
                    break

            except Exception as e:
                logger.error(f"Error fetching Baidu page {page + 1}: {e}")
                # 继续尝试下一页，不中断整个流程

        logger.info(
            f"Baidu pagination complete: "
            f"{len(all_urls)} total unique URLs"
        )
        return all_urls

    async def _fetch_page(self, keyword: str, pn: int, count: int) -> List[str]:
        """
        获取单页图片 URL（混合模式：aiohttp 优先，Selenium 备用）

        Args:
            keyword: 搜索关键词
            pn: 起始位置偏移量（0, 20, 40, ...）
            count: 请求的数量

        Returns:
            图片 URL 列表
        """
        # 策略 1: 先尝试 aiohttp
        urls = await self._fetch_with_aiohttp(keyword, pn, count)
        if urls:
            return urls

        # 策略 2: aiohttp 失败，使用 Selenium
        logger.info("Baidu aiohttp failed, trying Selenium...")
        page_num = pn // self.page_size
        return await self._fetch_with_selenium(keyword, page_num)

    async def _fetch_with_aiohttp(
        self,
        keyword: str,
        pn: int,
        count: int
    ) -> List[str]:
        """
        使用 aiohttp 获取单页图片 URL

        Args:
            keyword: 搜索关键词
            pn: 起始位置偏移量（0, 20, 40, ...）
            count: 请求的数量

        Returns:
            图片 URL 列表
        """
        urls = []

        try:
            # 构建请求参数
            params: Dict[str, Any] = {
                "tn": "baiduimage",
                "word": keyword,
                "pn": pn,
                "rn": count,
            }

            headers = {
                "User-Agent": self.USER_AGENT,
                "Referer": "https://image.baidu.com/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        urls = self._parse_image_urls_from_json(json_data)
                    else:
                        logger.warning(
                            f"Baidu aiohttp failed (pn={pn}): "
                            f"status {response.status}"
                        )

        except Exception as e:
            logger.warning(f"Baidu aiohttp error: {e}")

        return urls

    def _parse_image_urls_from_json(self, json_data: dict) -> List[str]:
        """
        从 JSON 响应中解析图片 URL

        Args:
            json_data: Baidu API 返回的 JSON 数据

        Returns:
            图片 URL 列表
        """
        urls = []

        try:
            # Baidu JSON 格式:
            # {"data": [{"thumbURL": "...", "middleURL": "...", "objURL": "..."}]}
            # objURL 通常是原始图片 URL
            data = json_data.get("data", [])

            for item in data:
                # 优先使用 objURL (原始图片)，其次 middleURL，最后 thumbURL
                obj_url = item.get("objURL")
                middle_url = item.get("middleURL")
                thumb_url = item.get("thumbURL")

                url = obj_url or middle_url or thumb_url
                if url and url.startswith("http"):
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")

        return urls

    def _parse_image_urls(self, html: str) -> List[str]:
        """从 HTML 中解析图片 URL"""
        urls = []

        try:
            parser = LexborHTMLParser(html)

            # 百度的图片 URL 通常在 data-imgurl 属性中
            for node in parser.css("img[data-imgurl]"):
                url = node.attributes.get("data-imgurl")
                if url:
                    urls.append(url)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return urls

    # ========== Selenium 相关方法 ==========

    def _build_selenium_url(self, keyword: str, page: int) -> str:
        """
        构建百度搜索 URL（Selenium 用）

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            百度图片搜索 URL
        """
        offset = page * self.page_size
        return (
            f"https://image.baidu.com/search/index"
            f"?tn=baiduimage&word={keyword}&pn={offset}"
        )

    def _extract_image_urls(self, driver) -> List[str]:
        """
        从页面提取图片 URL（Selenium 用）

        Args:
            driver: Selenium WebDriver 实例

        Returns:
            图片 URL 列表
        """
        from selenium.webdriver.common.by import By

        urls = []

        try:
            # 百度的图片在 data-imgurl 属性中
            img_elements = driver.find_elements(
                By.CSS_SELECTOR,
                "img[data-imgurl]"
            )

            for img in img_elements:
                url = img.get_attribute("data-imgurl")
                if url and url.startswith("http"):
                    urls.append(url)

        except Exception as e:
            logger.warning(f"Error extracting URLs with Selenium: {e}")

        return urls
