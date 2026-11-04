from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width":1280,"height":1000})
    pg.goto("file:///workspace/outputs/solar_system_teaching.html")
    pg.wait_for_timeout(2500)
    errors = pg.evaluate("() => window.__err || null")
    pg.screenshot(path="/workspace/tmp/render_full.png", full_page=True)
    print("title:", pg.title())
    print("canvas visible:", pg.is_visible("#stage"))
    print("table rows:", pg.eval_on_selector_all("#tbody tr", "els => els.length"))
    print("js errors:", errors)
    b.close()
