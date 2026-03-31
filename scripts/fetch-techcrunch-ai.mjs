#!/usr/bin/env node
import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('https://techcrunch.com/category/artificial-intelligence/', { 
    waitUntil: 'domcontentloaded',
    timeout: 30000 
  });
  
  await page.waitForTimeout(5000);
  
  // Get AI news headlines
  const headlines = await page.evaluate(() => {
    const articles = document.querySelectorAll('h2 a, h3 a, .post-block__title a');
    return Array.from(articles).slice(0, 15).map(a => ({
      title: a.textContent.trim(),
      url: a.href
    }));
  });
  
  console.log(JSON.stringify(headlines, null, 2));
  
  await browser.close();
})();
