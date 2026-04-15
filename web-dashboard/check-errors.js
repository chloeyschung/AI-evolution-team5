import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  const logs = [];

  page.on('console', msg => {
    logs.push(`${msg.type()}: ${msg.text()}`);
  });

  page.on('pageerror', err => {
    errors.push(err.message);
  });

  console.log('Navigating to http://localhost:3001/login...');
  await page.goto('http://localhost:3001/login', { waitUntil: 'networkidle' });

  // Wait for Vue to render
  await page.waitForTimeout(3000);

  console.log('\n=== Console Logs ===');
  logs.forEach(log => console.log(log));

  console.log('\n=== Page Errors ===');
  if (errors.length === 0) {
    console.log('No errors');
  } else {
    errors.forEach(err => console.log(err));
  }

  console.log('\n=== Network Requests ===');
  const requests = await page.context().requests();
  console.log(`Total requests: ${requests.length}`);

  await browser.close();
})();
