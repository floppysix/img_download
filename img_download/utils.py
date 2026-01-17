import asyncio
import aiohttp
from pathlib import Path
from typing import Optional
from .logger import setup_logger

logger = setup_logger()


async def download_image(
    url: str,
    save_path: Path,
    session: aiohttp.ClientSession,
    timeout: int = 30
) -> bool:
    """
    下载单张图片

    Args:
        url: 图片 URL
        save_path: 保存路径
        session: aiohttp 会话
        timeout: 超时时间（秒）

    Returns:
        是否下载成功
    """
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                content = await response.read()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(content)
                logger.info(f"Downloaded: {save_path}")
                return True
            else:
                logger.warning(f"Failed {url}: status {response.status}")
                return False
    except asyncio.TimeoutError:
        logger.warning(f"Timeout: {url}")
        return False
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return False
