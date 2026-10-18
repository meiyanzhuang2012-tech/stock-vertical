# stock-vertical

**免 API key** 从 Pixabay 抓取免费商用素材，转成短视频用的竖屏片段。

```
python fetch.py search "artificial intelligence" -n 8 --to-video
```

```
found 8
1. 264KB 360x640 https://cdn.pixabay.com/photo/2024/09/20/04/34/robot-9060344_1280.jpg
   -> ./materials/robot-9060344-1280.mp4
...
videos: 8
```

English: [README.md](README.md)

## 为什么有这个工具

Pixabay 和 Pexels 都把 API 注册表单放在了反爬后面——截至 2026 年 10 月，
用程序提交注册表单会返回 *"Please do not use automatic tools to fill out
this form"*。想要 key，只能人工注册。

但**搜索和下载根本不需要 key**。图片 CDN（`cdn.pixabay.com`）是公开的，
不要 cookie、不要 referer、不要 token。所以这个工具绕开 API，直接走网页：

1. 用**有界面**的 Chromium 打开搜索页（无头模式下过不了 Cloudflare 验证）；
2. 从 DOM 里收集 `cdn.pixabay.com` 的图片地址，把尺寸段改写成 `_1280` 拿到可
   用分辨率（`_1920` 会返回 403）；
3. 用 `curl` 逐个下载；
4. 可选：用 ffmpeg 渲染成片段（`zoompan` 缓慢推近、H.264、`yuv420p`，保证
   各家剪辑软件和播放器都能吃）。

## 安装

```bash
pip install nodriver pillow
# ffmpeg 需在 PATH 中
```

## 用法

```bash
# 竖屏、每段 5 秒、输出到 ./materials
python fetch.py search "data center" -n 6 --to-video

# 横屏、更长的片段、自定义目录
python fetch.py search "city night" --orientation horizontal \
    -n 5 --to-video --size 1920x1080 --duration 8 --outdir ./clips

# 只要图，不做视频
python fetch.py search "office meeting" -n 10 --outdir ./stills
```

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--orientation` | `vertical` | `vertical` / `horizontal` / `all` |
| `-n`, `--count` | `8` | 保留多少个素材 |
| `--to-video` | 关 | 用 ffmpeg 渲染片段 |
| `--duration` | `5` | 片段时长（秒） |
| `--size` | `1080x1920` | 输出片段的 `宽x高` |
| `--outdir` | `./materials` | 片段落盘目录 |
| `--profile` | `~/.cache/stock-vertical` | Chromium profile 目录（可复用已过的验证） |

## 内建处理的两个坑

**透明 PNG 会变成纯黑视频。** 如果命中结果是 RGBA/LA/P 的 PNG，会先摊平到白
底再交给 ffmpeg。平均亮度仍低于 15 的帧直接跳过，不会产出黑屏片段。

**分辨率。** Pixabay 公开提供的最大档是 `_1280`，所以竖图宽度常见只有
360–500 px。放大到 1080 交给 ffmpeg 处理——当背景素材没问题，但别指望它能
当主视觉用。

**profile 目录损坏。** 如果报 `Failed to connect to browser`，先删掉
`--profile` 指向的目录再重跑（旧的 SingletonLock 残留会让浏览器起不来）。

## 环境要求

- Python 3.10+
- `nodriver`、`Pillow`
- Chromium/Chrome（不在标准路径时用 `CHROME_PATH` 指定）
- 一个显示环境——X11、Xvfb 或 VNC——因为浏览器必须是有界面的

## 许可证

MIT，见 [LICENSE](LICENSE)。

通过本工具下载的图片仍受
[Pixabay Content License](https://pixabay.com/service/license-summary/)
约束。本工具只是把你要手动做的浏览动作自动化了。
