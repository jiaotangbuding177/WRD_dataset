import asyncio
from playwright.async_api import async_playwright

OUT = "/workspace/tmp/archery"

CARDS = [
    ("title1", "攻防箭小游戏", "color:#fff; -webkit-text-stroke:10px #1a3a8f; text-shadow:0 10px 30px rgba(0,0,0,.45); font-size:190px;"),
    ("win", "胜利！", "color:#ffd83d; -webkit-text-stroke:10px #b3541e; text-shadow:0 10px 30px rgba(0,0,0,.5); font-size:210px;"),
    ("end", "快来试试攻防箭！<svg viewBox=\"0 0 48 48\" style=\"width:104px;height:104px;vertical-align:-10px;margin-left:8px;\"><path d=\"M 8 40 Q 34 34 40 8\" stroke=\"#8b5a2b\" stroke-width=\"4.5\" fill=\"none\" stroke-linecap=\"round\"/><line x1=\"8\" y1=\"40\" x2=\"40\" y2=\"8\" stroke=\"#f5f5f5\" stroke-width=\"2\"/><line x1=\"12\" y1=\"36\" x2=\"38\" y2=\"10\" stroke=\"#6b4226\" stroke-width=\"3\"/><path d=\"M 38 10 L 30 12 L 36 18 Z\" fill=\"#e74c3c\"/><path d=\"M 12 36 L 10 30 M 12 36 L 18 38\" stroke=\"#3498db\" stroke-width=\"3\" stroke-linecap=\"round\"/></svg>", "color:#fff; -webkit-text-stroke:8px #d64545; text-shadow:0 8px 24px rgba(0,0,0,.45); font-size:120px;"),
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
