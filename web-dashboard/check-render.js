import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  console.log('Navigating to http://localhost:3001/login...');
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle' });

  // Wait for Vue to render
  await page.waitForTimeout(2000);

  console.log('\n=== Page Title ===');
  console.log(await page.title());

  console.log('\n=== Page URL ===');
  console.log(page.url());

  console.log('\n=== Body Text ===');
  const bodyText = await page.locator('body').textContent();
  console.log(bodyText || '(empty)');

  console.log('\n=== All h1 elements ===');
  const h1s = await page.locator('h1').allTextContents();
  console.log(h1s);

  console.log('\n=== All buttons ===');
  const buttons = await page.locator('button').allTextContents();
  console.log(buttons);

  await page.screenshot({ path: 'check-render.png', fullPage: true });
  console.log('\nScreenshot saved to check-render.png');

  await browser.close();
  console.log('\nDone!');
})();
