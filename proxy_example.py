#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代理方案示例 - 为 Bing 下载器添加代理支持"""

import asyncio
import aiohttp
from typing import List, Optional, Union


class BingDownloaderWithProxy:
    """支持代理的 Bing 下载器示例"""

    def __init__(self, proxy: Optional[str] = None):
        """
        初始化

        Args:
            proxy: 代理地址，格式：
                - HTTP: "http://proxy.example.com:8080"
                - HTTPS: "https://proxy.example.com:8080"
                - SOCKS5: "socks5://proxy.example.com:1080"
        """
        self.base_url = "https://www.bing.com/images/async"
        self.proxy = proxy

    async def fetch_with_proxy(self, url: str, params: dict) -> str:
        """
        使用代理请求（如果配置了）

        Args:
            url: 请求 URL
            params: 查询参数

        Returns:
            响应文本
        """
        kwargs = {
            "params": params,
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "timeout": aiohttp.ClientTimeout(total=30)
        }

        # 如果配置了代理，添加到请求参数
        if self.proxy:
            kwargs["proxy"] = self.proxy

        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.text()


# ========== 方案 1: 单个代理 ==========

async def example_single_proxy():
    """使用单个代理"""
    print("=== 方案 1: 单个代理 ===")

    # 使用 HTTP 代理
    downloader = BingDownloaderWithProxy(
        proxy="http://127.0.0.1:7890"  # 替换为你的代理地址
    )

    result = await downloader.fetch_with_proxy(
        "https://www.bing.com/images/async",
        {"q": "猫", "first": 0, "count": 35}
    )

    print(f"响应长度: {len(result)}")


# ========== 方案 2: 代理池轮换 ==========

class BingDownloaderWithProxyPool:
    """支持代理池轮换的 Bing 下载器"""

    def __init__(self, proxy_list: List[str]):
        """
        初始化

        Args:
            proxy_list: 代理列表
                ["http://proxy1.com:8080", "http://proxy2.com:8080", ...]
        """
        self.base_url = "https://www.bing.com/images/async"
        self.proxy_list = proxy_list
        self.current_proxy_index = 0

    def _get_next_proxy(self) -> Optional[str]:
        """获取下一个代理"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy

    async def fetch_with_proxy_rotation(self, url: str, params: dict, max_retries: int = 3) -> str:
        """
        使用代理池请求，失败时自动切换代理

        Args:
            url: 请求 URL
            params: 查询参数
            max_retries: 最大重试次数

        Returns:
            响应文本
        """
        for attempt in range(max_retries):
            proxy = self._get_next_proxy()

            try:
                kwargs = {
                    "params": params,
                    "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    "timeout": aiohttp.ClientTimeout(total=30)
                }

                if proxy:
                    kwargs["proxy"] = proxy
                    print(f"尝试代理 {attempt + 1}/{max_retries}: {proxy}")

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, **kwargs) as response:
                        if response.status == 200:
                            result = await response.text()
                            print(f"成功！响应长度: {len(result)}")
                            return result
                        else:
                            print(f"状态码: {response.status}")

            except Exception as e:
                print(f"代理 {proxy} 失败: {e}")
                continue

        raise Exception(f"所有代理均失败，已重试 {max_retries} 次")


async def example_proxy_pool():
    """使用代理池"""
    print("\n=== 方案 2: 代理池轮换 ===")

    # 代理池列表
    proxies = [
        "http://127.0.0.1:7890",
        "http://127.0.0.1:7891",
        "http://proxy.example.com:8080",  # 替换为实际代理
    ]

    downloader = BingDownloaderWithProxyPool(proxy_list=proxies)

    try:
        result = await downloader.fetch_with_proxy_rotation(
            "https://www.bing.com/images/async",
            {"q": "猫", "first": 0, "count": 35},
            max_retries=3
        )
        print(f"最终响应长度: {len(result)}")
    except Exception as e:
        print(f"失败: {e}")


# ========== 方案 3: 从 API 获取代理 ==========

import json


class BingDownloaderWithProxyAPI:
    """支持从 API 获取代理的下载器"""

    def __init__(self, proxy_api_url: Optional[str] = None):
        """
        初始化

        Args:
            proxy_api_url: 代理 API 地址
                例如: "http://proxy-api.com/get_proxy"
        """
        self.base_url = "https://www.bing.com/images/async"
        self.proxy_api_url = proxy_api_url
        self.current_proxy = None

    async def _fetch_proxy_from_api(self) -> Optional[str]:
        """从 API 获取代理"""
        if not self.proxy_api_url:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.proxy_api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # 假设 API 返回格式: {"proxy": "http://1.2.3.4:8080"}
                        return data.get("proxy")
        except Exception as e:
            print(f"获取代理失败: {e}")
            return None

    async def fetch_with_auto_proxy(self, url: str, params: dict) -> str:
        """自动获取代理并请求"""
        # 从 API 获取代理
        self.current_proxy = await self._fetch_proxy_from_api()

        kwargs = {
            "params": params,
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "timeout": aiohttp.ClientTimeout(total=30)
        }

        if self.current_proxy:
            kwargs["proxy"] = self.current_proxy
            print(f"使用 API 代理: {self.current_proxy}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.text()


# ========== 方案 4: SOCKS5 代理（需要 aiohttp-socks） ==========

class BingDownloaderWithSocksProxy:
    """支持 SOCKS5 代理的下载器"""

    def __init__(self, socks_proxy: str):
        """
        初始化

        Args:
            socks_proxy: SOCKS5 代理地址
                "socks5://127.0.0.1:1080"
        """
        self.base_url = "https://www.bing.com/images/async"
        self.socks_proxy = socks_proxy

    async def fetch_with_socks(self, url: str, params: dict) -> str:
        """
        使用 SOCKS5 代理请求

        注意：需要安装 aiohttp-socks
        pip install aiohttp-socks
        """
        try:
            from aiohttp_socks import ProxyConnector
        except ImportError:
            raise Exception("请先安装 aiohttp-socks: pip install aiohttp-socks")

        connector = ProxyConnector.from_url(self.socks_proxy)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return await response.text()


# ========== 使用示例 ==========

async def main():
    # 方案 1: 单个代理
    # await example_single_proxy()

    # 方案 2: 代理池
    # await example_proxy_pool()

    # 方案 3: API 获取代理
    # api_downloader = BingDownloaderWithProxyAPI("http://your-proxy-api/get")
    # result = await api_downloader.fetch_with_auto_proxy(...)

    print("代理方案示例代码已准备就绪")
    print("\n常用代理源:")
    print("  1. 自建代理: V2Ray, Clash, Shadowsocks")
    print("  2. 免费代理API: https://www.proxy-list.download/")
    print("  3. 付费代理服务: 阿布云, 快代理, 芝麻代理等")


if __name__ == "__main__":
    asyncio.run(main())
