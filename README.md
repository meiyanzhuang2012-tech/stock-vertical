# stock-vertical

Grab free stock photos from Pixabay **without an API key** and turn them into
short vertical clips for shorts / reels / TikTok-style video.

**English** | [中文](README.zh-CN.md)

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

## Why this exists

Pixabay and Pexels both gate their API sign-up forms behind bot detection —
as of October 2026, submitting the registration form programmatically returns
*"Please do not use automatic tools to fill out this form"*. If you need a key
you have to register by hand.

But **searching and downloading needs no key at all**. The image CDN
(`cdn.pixabay.com`) serves files publicly with no cookie, no referer and no
token. So this tool skips the API entirely:

1. drive a *visible* Chromium to the search page (Cloudflare's challenge does
   not clear in headless mode),
2. collect `cdn.pixabay.com` image URLs from the DOM, rewriting the size
   segment to `_1280` for a usable resolution (`_1920` returns 403),
3. download each file with `curl`,
4. optionally render a clip with ffmpeg (`zoompan` slow push-in, H.264,
   `yuv420p` so every editor/player accepts it).

## Install

```bash
pip install nodriver pillow
# ffmpeg must be on PATH
```

## Usage

```bash
# vertical clips, 5 seconds each, into ./materials
python fetch.py search "data center" -n 6 --to-video

# landscape, longer clips, custom output
python fetch.py search "city night" --orientation horizontal \
    -n 5 --to-video --size 1920x1080 --duration 8 --outdir ./clips

# images only (no ffmpeg step)
python fetch.py search "office meeting" -n 10 --outdir ./stills
```

| flag | default | meaning |
| --- | --- | --- |
| `--orientation` | `vertical` | `vertical` / `horizontal` / `all` |
| `-n`, `--count` | `8` | how many assets to keep |
| `--to-video` | off | render clips with ffmpeg |
| `--duration` | `5` | clip length in seconds |
| `--size` | `1080x1920` | `WxH` of the output clip |
| `--outdir` | `./materials` | where clips land |
| `--profile` | `~/.cache/stock-vertical` | Chromium profile dir (keeps past challenges) |

## Two gotchas baked in

**Transparent PNGs encode as black video.** If a result is an RGBA/LA/P PNG it
is flattened onto white before ffmpeg sees it. Frames whose average luminance
is still below 15 are skipped instead of producing a black clip.

**Resolution.** Pixabay's `_1280` variant is the largest that is publicly
served; vertical images are therefore often ~360–500 px wide. The upscale to
1080 is handled by ffmpeg — fine for background footage, not for a hero shot
you want pixel-perfect.

## Requirements

- Python 3.10+
- `nodriver`, `Pillow`
- Chromium/Chrome (set `CHROME_PATH` if it is not in a standard location)
- a display — X11, Xvfb or VNC — because the browser must be visible

## License

MIT — see [LICENSE](LICENSE).

Images downloaded through this tool remain subject to the
[Pixabay Content License](https://pixabay.com/service/license-summary/).
This tool only automates the browsing you would otherwise do by hand.
