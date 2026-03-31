#!/usr/bin/env node
import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('https://techcrunch.com/2026/03/15/google-and-accel-cut-through-wrappers-in-4000-ai-startup-pitches-to-pick-five-tied-to-india/', { 
    waitUntil: 'domcontentloaded',
    timeout: 30000 
  });
  
  await page.waitForTimeout(5000);
  
  // Get article content
  const content = await page.evaluate(() => {
    const paragraphs = document.querySelectorAll('p');
    return Array.from(paragraphs).map(p => p.textContent.trim()).filter(t => t.length > 50).join('\n\n');
  });
  
  console.log(content);
  
  await browser.close();
})();
