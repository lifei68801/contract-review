#!/usr/bin/env node
/**
 * headless-browser - A drop-in replacement for agent-browser on headless servers
 * 
 * Usage:
 *   headless-browser open <url> [waitMs]   # waitMs defaults to 2000ms
 *   headless-browser snapshot
 *   headless-browser click @e1
 *   headless-browser fill @e2 "text"
 *   headless-browser get title
 *   headless-browser screenshot <path>
 *   headless-browser text
 *   headless-browser close
 * 
 * Examples:
 *   headless-browser open https://example.com        # Wait 2s after load
 *   headless-browser open https://example.com 5000   # Wait 5s after load
 *   headless-browser open https://example.com 0      # No extra wait
 *   headless-browser screenshot /tmp/page.png
 *   headless-browser text  # Get page text content
 */

import { chromium } from 'playwright';
import { readFile, writeFile } from 'fs/promises';
import { existsSync } from 'fs';

const STATE_FILE = '/tmp/headless-browser-state.json';

let browser = null;
let page = null;
let refs = {};

async function loadState() {
  if (existsSync(STATE_FILE)) {
    const data = JSON.parse(await readFile(STATE_FILE, 'utf8'));
    refs = data.refs || {};
  }
}

async function saveState() {
  await writeFile(STATE_FILE, JSON.stringify({ refs }, null, 2));
}

async function open(url, waitTime = 2000) {
  browser = await chromium.launch({ headless: true });
  page = await browser.newPage();
  
  // Wait for network idle (CDN resources loaded)
  await page.goto(url, { 
    waitUntil: 'networkidle',
    timeout: 30000 
  });
  
  // Additional wait for dynamic content
  if (waitTime > 0) {
    await page.waitForTimeout(waitTime);
  }
  
  console.log(JSON.stringify({ success: true, url: page.url() }));
}

async function snapshot() {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  const content = await page.evaluate(() => {
    const elements = document.querySelectorAll('a, button, input, textarea, select, [role="button"]');
    return Array.from(elements).slice(0, 50).map((el, i) => {
      const ref = `e${i + 1}`;
      el.setAttribute('data-ref', ref);
      return {
        ref,
        tag: el.tagName.toLowerCase(),
        type: el.type || undefined,
        text: el.textContent?.trim().slice(0, 50) || undefined,
        placeholder: el.placeholder || undefined,
        name: el.name || undefined,
        aria: el.getAttribute('aria-label') || undefined,
      };
    });
  });
  
  refs = {};
  content.forEach(item => {
    refs[`@${item.ref}`] = item;
    delete item.ref;
  });
  
  await saveState();
  console.log(JSON.stringify({ success: true, elements: content }, null, 2));
}

async function click(ref) {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  const selector = `[data-ref="${ref.replace('@', '')}"]`;
  await page.click(selector);
  console.log(JSON.stringify({ success: true }));
}

async function fill(ref, text) {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  const selector = `[data-ref="${ref.replace('@', '')}"]`;
  await page.fill(selector, text);
  console.log(JSON.stringify({ success: true }));
}

async function get(what) {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  let result;
  switch (what) {
    case 'title':
      result = await page.title();
      break;
    case 'url':
      result = page.url();
      break;
    default:
      result = await page.title();
  }
  
  console.log(JSON.stringify({ success: true, data: result }));
}

async function screenshot(path) {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  await page.screenshot({ path, fullPage: false });
  console.log(JSON.stringify({ success: true, path }));
}

async function text() {
  if (!page) {
    console.log(JSON.stringify({ success: false, error: 'No page open' }));
    return;
  }
  
  const content = await page.textContent('body');
  console.log(JSON.stringify({ success: true, content }));
}

async function close() {
  if (browser) {
    await browser.close();
    browser = null;
    page = null;
  }
  console.log(JSON.stringify({ success: true }));
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  
  await loadState();
  
  try {
    switch (cmd) {
      case 'open':
        const waitTime = args[2] ? parseInt(args[2]) : 2000;
        await open(args[1], waitTime);
        break;
      case 'snapshot':
        await snapshot();
        break;
      case 'click':
        await click(args[1]);
        break;
      case 'fill':
        await fill(args[1], args[2]);
        break;
      case 'type':
        await fill(args[1], args[2]);
        break;
      case 'get':
        await get(args[1]);
        break;
      case 'screenshot':
        await screenshot(args[1]);
        break;
      case 'text':
        await text();
        break;
      case 'close':
        await close();
        break;
      default:
        console.log(JSON.stringify({ success: false, error: `Unknown command: ${cmd}` }));
    }
  } catch (e) {
    console.log(JSON.stringify({ success: false, error: e.message }));
    process.exit(1);
  }
}

main();
