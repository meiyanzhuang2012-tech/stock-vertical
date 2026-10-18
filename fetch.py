#!/usr/bin/env python3
"""stock-vertical — grab free stock photos from Pixabay *without* an API key
and turn them into short vertical clips ready for shorts / reels / TikTok.

Why not the official API?
-------------------------
As of 2026-10 both Pixabay and Pexels gate their sign-up forms behind bot
detection ("Please do not use automatic tools to fill out this form"), so
obtaining a key programmatically is a dead end. Searching and downloading,
however, needs no key at all — the CDN serves ``cdn.pixabay.com/photo/...``
publicly.

Usage
-----
    python fetch.py search "artificial intelligence" -n 8 --to-video
    python fetch.py search "city night" -n 5 --to-video --outdir ./clips --size 1920x1080

Install
-------
    pip install nodriver pillow
    # plus ffmpeg on PATH

Notes
-----
* A **visible** browser is required — Cloudflare's challenge does not clear
  in headless mode. On a server run this under Xvfb or a VNC session.
* Transparent PNGs are flattened onto white first; ffmpeg would otherwise
  encode them as pure black frames.
* Frames whose average luminance is below 15 are skipped for the same reason.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys

CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]

SEARCH_JS = """(()=>{
  const seen=new Set(); const out=[];
  document.querySelectorAll('img').forEach(i=>{
    const u=(i.currentSrc||i.src||'');
    if(!u.includes('cdn.pixabay.com')) return;
    const big=u.replace(/_\\d+\\.(jpg|png|webp)$/,'_1280.$1');
    if(seen.has(big)) return; seen.add(big);
    if(i.naturalWidth<300) return;
    out.push({src:big, w:i.naturalWidth, h:i.naturalHeight});
  });
  return JSON.stringify(out);
})()"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    raise SystemExit("No Chromium found — set CHROME_PATH=/path/to/chrome")


def ensure_not_black(img: str) -> str:
    """Flatten transparent PNGs onto white; reject near-black frames."""
    from PIL import Image

    im = Image.open(img)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        out = img.rsplit(".", 1)[0] + "-flat.jpg"
        bg.save(out, "JPEG", quality=92)
        img = out
    g = Image.open(img).convert("L").resize((32, 32))
    avg = sum(g.get_flattened_data()) / 1024
    if avg < 15:
        raise ValueError(f"frame is almost black (avg={avg:.1f})")
    return img


def to_video(img: str, outdir: str, dur: int = 5, size: str = "1080x1920") -> str:
    w, h = (int(x) for x in size.lower().split("x"))
    os.makedirs(outdir, exist_ok=True)
    name = re.sub(r"\W+", "-", os.path.basename(img).rsplit(".", 1)[0])[:50]
    out = os.path.join(outdir, f"{name}.mp4")
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='min(zoom+0.0008,1.12)':d={dur * 25}:s={w}x{h}:fps=25,"
        f"format=yuv420p"
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-loop", "1", "-i", img,
         "-t", str(dur), "-vf", vf, "-r", "25", "-y", out],
        check=True,
    )
    return out


async def search(query: str, orientation: str | None, n: int,
                 profile: str, chrome: str, timeout_s: int = 45):
    import nodriver as uc

    url = f"https://pixabay.com/images/search/{query.replace(' ', '%20')}/"
    if orientation:
        url += f"?orientation={orientation}"

    browser = await uc.start(
        headless=False,
        browser_executable_path=chrome,
        user_data_dir=profile,
        sandbox=False,           # root has no user namespace
        browser_args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--window-size=1400,950"],
    )
    page = await browser.get(url)

    waited = 0
    while waited < timeout_s:
        await asyncio.sleep(3)
        waited += 3
        title = str(await page.evaluate("document.title"))
        if "Just a moment" not in title and "security verification" not in title:
            break
    else:
        raise SystemExit("Cloudflare challenge did not clear — "
                         "run inside a desktop/Xvfb session")

    found: dict[str, dict] = {}
    for _ in range(3):
        raw = await page.evaluate(SEARCH_JS)
        try:
            for item in json.loads(raw or "[]"):
                found[item["src"]] = item
        except json.JSONDecodeError:
            pass
        if len(found) >= n:
            break
        await page.evaluate("window.scrollBy(0,1600)")
        await asyncio.sleep(2.5)
    browser.stop()

    items = list(found.values())
    # taller-than-wide first: better for vertical crops
    items.sort(key=lambda x: -(x["h"] / max(x["w"], 1)))
    return items[:n]


def download(url: str, dest: str) -> int:
    subprocess.run(["curl", "-sSL", "--max-time", "40", "-o", dest, url], check=True)
    return os.path.getsize(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="search Pixabay, download images / clips")
    s.add_argument("query")
    s.add_argument("--orientation", default="vertical",
                   choices=["vertical", "horizontal", "all"])
    s.add_argument("-n", "--count", type=int, default=8)
    s.add_argument("--to-video", action="store_true",
                   help="also render short mp4 clips")
    s.add_argument("--outdir", default="./materials")
    s.add_argument("--duration", type=int, default=5, help="clip length in seconds")
    s.add_argument("--size", default="1080x1920", help="WxH, e.g. 1920x1080")
    s.add_argument("--profile",
                   default=os.path.expanduser("~/.cache/stock-vertical"))
    s.add_argument("--tmpdir", default="/tmp")
    args = ap.parse_args()

    chrome = find_chrome()
    items = asyncio.run(
        search(args.query,
               None if args.orientation == "all" else args.orientation,
               args.count, args.profile, chrome)
    )
    print(f"found {len(items)}", flush=True)

    made = 0
    for i, item in enumerate(items, 1):
        ext = os.path.splitext(item["src"].split("?")[0])[1] or ".jpg"
        img = os.path.join(args.tmpdir,
                           f"stock_{abs(hash(item['src'])) % 10**9}{ext}")
        try:
            size = download(item["src"], img)
            print(f"{i}. {size / 1024:.0f}KB {item['w']}x{item['h']} {item['src']}")
            if args.to_video:
                clip = to_video(ensure_not_black(img), args.outdir,
                                args.duration, args.size)
                print(f"   -> {clip}")
                made += 1
        except Exception as exc:  # noqa: BLE001 — one bad asset shouldn't abort a batch
            print(f"{i}. FAILED: {exc}", file=sys.stderr)
    if args.to_video:
        print(f"videos: {made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
