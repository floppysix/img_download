# 图片下载量优化设计文档

**日期**: 2026-01-17
**状态**: 设计已确认

## 1. 概述

增加图片下载量，实现多来源并行分页收集，尽可能多地获取图片。

**当前问题**：只获取第一页结果，数量有限（约 30-50 张）

**目标**：实现分页加载，支持多来源并行收集，自动验证 URL 有效性，尽可能多地收集图片（目标 500+ 张）。

---

## 2. 方案选择

### 2.1 分页实现方案

选择：**多次请求 + first 参数偏移**

利用 Bing API 的 `first` 参数进行分页：
- 第1次：`first=0, count=35`
- 第2次：`first=35, count=35`
- 第3次：`first=70, count=35`
- ...持续获取直到达到停止条件

### 2.2 多来源方案

选择：**方案一 - 并行多来源**

同时从 Bing、Baidu 等多个来源获取，每个来源独立实现分页逻辑。

---

## 3. 停止条件

### 3.1 组合停止策略

1. **硬性上限**：最多请求 20 页（约 700-1000 张）
2. **软性停止**：连续 2 次请求返回 0 个新 URL
3. **末页检测**：返回数量 < 请求数量的 30%

### 3.2 URL 去重

使用 `Set` 自动去重，全局去重在调度器层面实现。

### 3.3 图片验证

**HEAD 请求验证**：
- 并发验证（10 个并发）
- 超时时间 10 秒
- 检查 Content-Type 是否为 `image/*`

---

## 4. 架构设计

### 4.1 类结构

```python
class BaseImageDownloader(ABC):
    @abstractmethod
    async def search_with_pagination(self, keyword: str) -> Set[str]:
        """分页搜索，返回去重后的 URL 集合"""
        pass
```

### 4.2 Bing 分页实现

```python
class BingDownloader(BaseImageDownloader):
    page_size = 35
    max_pages = 20
    max_empty = 2

    async def search_with_pagination(self, keyword: str) -> Set[str]:
        all_urls = set()
        empty_count = 0

        for page in range(self.max_pages):
            first = page * self.page_size
            urls = await self._fetch_page(keyword, first, self.page_size)

            # 验证
            valid_urls = await self._validate_urls(urls)

            # 停止检查
            if len(valid_urls) == 0:
                empty_count += 1
                if empty_count >= self.max_empty:
                    break
            else:
                empty_count = 0

            # 软性停止
            if len(valid_urls) < self.page_size * 0.3:
                break

            all_urls.update(valid_urls)

        return all_urls
```

### 4.3 Baidu 分页实现

百度使用 `pn` 参数实现分页：
- 第1页：`pn=0`
- 第2页：`pn=20`
- 第3页：`pn=40`

---

## 5. 数据流

```
用户请求 "熊猫"
    ↓
调度器并行调用所有来源
    ├─ Bing: search_with_pagination() → {url1, url2, ..., url150}
    ├─ Baidu: search_with_pagination() → {url30, url31, ..., url100}
    └─ Google: search_with_pagination() → {url50, url51, ..., url80}
    ↓
全局去重: Set 合并 → 200 个唯一 URL
    ↓
HEAD 验证（10 并发）→ 180 个有效 URL
    ↓
并发下载 → 熊猫_1.jpg, 熊猫_2.jpg, ...
    ↓
保存 sources.json 记录来源
```

---

## 6. 可配置参数

```python
class ImageDownloader:
    def __init__(
        self,
        output_dir: str = "output",
        max_concurrent: int = 10,
        max_pages: int = 20,           # 每个来源最大页数
        page_size: int = 35,            # 每页数量
        validate_concurrency: int = 10,  # 验证并发数
        max_empty_pages: int = 2        # 连续空页停止条件
    ):
```

---

## 7. 错误处理

### 7.1 异常定义

```python
class DownloadError(Exception):
    """下载错误"""
    pass

class ValidationError(Exception):
    """验证错误"""
    pass
```

### 7.2 失败率监控

当验证失败率 > 50% 时记录警告日志。

---

## 8. 修改的文件

1. `img_download/downloaders/base.py` - 添加分页接口
2. `img_download/downloaders/bing.py` - 实现分页
3. `img_download/downloaders/baidu.py` - 实现分页
4. `img_download/core.py` - 并行多来源调度
5. `tests/test_*.py` - 分页和验证测试

---

## 9. 预期效果

- **单来源**：Bing 可获取 500-700 张图片
- **多来源**：Bing + Baidu 可获取 800-1200 张图片
- **去重后**：实际可用 500-1000 张
- **验证通过率**：预计 80-90%
