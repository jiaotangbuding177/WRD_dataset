const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 2 });
  await page.goto('file:///workspace/tmp/poster.html');
  await page.waitForTimeout(800);
  await page.screenshot({ path: process.argv[2] || '/workspace/tmp/poster.png' });
  await browser.close();
})();
