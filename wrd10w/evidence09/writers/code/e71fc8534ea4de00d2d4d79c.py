import asyncio, json, re
from playwright.async_api import async_playwright

QUERIES = [
    "视比特机器人 融资",
    "视比特机器人 深圳 机器视觉 主营业务",
    "视比特机器人 C轮 估值",
]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--no-sandbox"], executable_path="/usr/bin/chromium")
        pg = await b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        out = {}
        for q in QUERIES:
            url = "https://cn.bing.com/search?q=" + q.replace(" ", "+")
            try:
                await pg.goto(url, timeout=30000, wait_until="domcontentloaded")
                await pg.wait_for_timeout(2500)
                items = await pg.eval_on_selector_all("li.b_algo", "els => els.map(e => {const a=e.querySelector('h2 a'); const s=e.querySelector('.b_caption p, p'); return {t:a?a.innerText:'',u:a?a.href:'',s:s?s.innerText:''}})")
                out[q] = items[:8]
            except Exception as e:
                out[q] = ["ERR", str(e)]
        await b.close()
        print(json.dumps(out, ensure_ascii=False, indent=1))

asyncio.run(main())
