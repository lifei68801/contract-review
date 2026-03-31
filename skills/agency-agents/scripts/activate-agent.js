#!/usr/bin/env node
/**
 * activate-agent.js — Activate an agent by writing its prompt to SOUL.md
 * Usage: node activate-agent.js <slug> [--restore]
 */

import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, '..', 'data');
const INDEX_PATH = join(DATA_DIR, 'agents-index.json');
const ACTIVE_FILE = join(DATA_DIR, 'active-agent.json');
const SOUL_MD = join(process.env.HOME || '/root', '.openclaw', 'workspace', 'SOUL.md');
const SOUL_BACKUP = SOUL_MD + '.backup.default';

function loadIndex() {
  return JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
}

// Restore mode
if (process.argv.includes('--restore')) {
  if (existsSync(SOUL_BACKUP)) {
    copyFileSync(SOUL_BACKUP, SOUL_MD);
    console.log('✅ Restored default SOUL.md');
    if (existsSync(ACTIVE_FILE)) {
      try { require('node:fs').unlinkSync(ACTIVE_FILE); } catch {}
    }
  } else {
    console.log('⚠️  No backup found');
    process.exit(1);
  }
  process.exit(0);
}

const slug = process.argv[2];
if (!slug) {
  console.log('Usage: node activate-agent.js <category/filename> [--restore]');
  console.log('Example: node activate-agent.js design/design-ui-designer');
  process.exit(1);
}

const index = loadIndex();
const agent = index.agents.find(a => a.slug === slug);

if (!agent) {
  console.log(`❌ Agent not found: ${slug}`);
  console.log(`   Run 'node scan-agents.js' to regenerate the index`);
  process.exit(1);
}

// Backup current SOUL.md
if (existsSync(SOUL_MD) && !existsSync(SOUL_BACKUP)) {
  copyFileSync(SOUL_MD, SOUL_BACKUP);
  console.log('📦 Backed up current SOUL.md');
}

// Write agent content to SOUL.md
const soulContent = `# SOUL.md — ${agent.emoji} ${agent.name}\n\n> Activated from Agency Agents on ${new Date().toISOString()}\n> Source: ${slug}\n\n${agent.content}\n`;
writeFileSync(SOUL_MD, soulContent);

// Save active agent info
const activeInfo = {
  slug: agent.slug,
  name: agent.name,
  emoji: agent.emoji,
  activatedAt: new Date().toISOString(),
};
writeFileSync(ACTIVE_FILE, JSON.stringify(activeInfo, null, 2));

console.log(`✅ Activated: ${agent.emoji} ${agent.name}`);
console.log(`   Slug: ${slug}`);
console.log(`   SOUL.md updated`);
