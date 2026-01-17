import asyncio
from img_download import ImageDownloader

async def main():
    downloader = ImageDownloader()
    result = await downloader.search("阿利·伯克级驱逐舰", count=100)
    print(f"下载完成：{result['success']}/{result['total']}")

asyncio.run(main())