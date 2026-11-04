import asyncio
from playwright.async_api import async_playwright

OUT = "/workspace/tmp/archery"

CARDS = [
    ("title1", "攻防箭小游戏", "color:#fff; -webkit-text-stroke:10px #1a3a8f; text-shadow:0 10px 30px rgba(0,0,0,.45); font-size:190px;"),
    ("win", "胜利！", "color:#ffd83d; -webkit-text-stroke:10px #b3541e; text-shadow:0 10px 30px rgba(0,0,0,.5); font-size:210px;"),
    ("end", "快来试试攻防箭！🏹", "color:#fff; -webkit-text-stroke:8px #d64545; text-shadow:0 8px 24px rgba(0,0,0,.45); font-size:120px;"),
]

HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@font-face {{ font-family: CJK; src: url("file:///usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"); }}
html,body {{ margin:0; padding:0; background:transparent; }}
.wrap {{ width:2000px; height:{h}px; display:flex; align-items:center; justify-content:center; }}
.txt {{ font-family: CJK, sans-serif; font-weight:900; letter-spacing:0.05em; {style} }}
</style></head><body><div class="wrap"><div class="txt">{text}</div></div></body></html>'''

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 2000, "height": 500})
        for name, text, style in CARDS:
            h = 520 if len(text) <= 5 else 300
            await page.set_content(HTML.format(text=text, style=style, h=h))
            await page.wait_for_timeout(300)
            await page.screenshot(path=f"{OUT}/{name}.png", omit_background=True, clip={"x": 0, "y": 0, "width": 2000, "height": h})
            print(name, "rendered")
        await browser.close()

asyncio.run(main())
