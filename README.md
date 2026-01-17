# img_download

图片搜索与下载模块

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```python
import asyncio
from img_download import ImageDownloader

async def main():
    downloader = ImageDownloader()
    result = await downloader.search("猫咪", count=50)
    print(f"下载完成：{result['success']}/{result['total']}")

asyncio.run(main())
```
