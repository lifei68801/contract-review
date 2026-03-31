#!/usr/bin/env node
import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('https://www.theverge.com/ai-artificial-intelligence', { 
    waitUntil: 'networkidle',
    timeout: 30000 
  });
  
  await page.waitForTimeout(3000);
  
  // Get AI news headlines
  const headlines = await page.evaluate(() => {
    const articles = document.querySelectorAll('h2 a, h3 a, .duet--article--title a');
    return Array.from(articles).slice(0, 20).map(a => ({
      title: a.textContent.trim(),
      url: a.href
    }));
  });
  
  console.log(JSON.stringify(headlines, null, 2));
  
  await browser.close();
})();
