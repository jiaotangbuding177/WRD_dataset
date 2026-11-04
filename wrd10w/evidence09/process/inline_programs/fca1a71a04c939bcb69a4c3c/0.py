from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1920,'height':1080})
    pg.set_content('<h1 style="font-family:\'Noto Sans CJK SC\'">测试渲染</h1>')
    pg.screenshot(path='/workspace/tmp/test.png')
    b.close()
print('ok')
