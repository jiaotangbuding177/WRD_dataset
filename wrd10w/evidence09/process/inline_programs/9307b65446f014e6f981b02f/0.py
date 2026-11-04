from playwright.sync_api import sync_playwright
import json

results = {"errors": [], "pageErrors": []}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1100, "height": 1150})
    page.on("console", lambda m: results["errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: results["pageErrors"].append(str(e)))
    page.goto("file:///workspace/outputs/friction_demo.html")
    page.wait_for_timeout(800)
    page.screenshot(path="/workspace/tmp/shot_initial.png")
    # 点击开始演示，播放一段时间
    page.click("#play")
    page.wait_for_timeout(2000)
    v1 = page.text_content("#v1"); v2 = page.text_content("#v2")
    results["after_play_v1"] = v1; results["after_play_v2"] = v2
    page.screenshot(path="/workspace/tmp/shot_playing.png")
    # 再调大推力继续看运动
    page.fill("#push", "0"); page.dispatch_event("#push", "input")
    page.wait_for_timeout(2500)
    results["after_stop_v1"] = page.text_content("#v1")
    results["after_stop_v2"] = page.text_content("#v2")
    page.screenshot(path="/workspace/tmp/shot_stopped.png")
    # 重置功能
    page.click("#reset"); page.wait_for_timeout(300)
    results["after_reset_v1"] = page.text_content("#v1")
    b.close()
print(json.dumps(results, ensure_ascii=False, indent=2))
