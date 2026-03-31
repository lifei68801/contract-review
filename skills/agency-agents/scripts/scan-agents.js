#!/usr/bin/env node
/**
 * scan-agents.js — Scan all Agent markdown files and generate agents-index.json
 * Usage: node scan-agents.js [source-dir] [output-dir]
 */

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync, mkdirSync } from 'node:fs';
import { join, relative, dirname, basename } from 'node:path';

const SOURCE_DIR = process.argv[2] || '/tmp/agency-agents';
const OUTPUT_DIR = process.argv[3] || join(dirname(import.meta.url), '..', 'data');

// Category color map
const CATEGORY_COLORS = {
  academic:        '#8B5CF6',
  design:          '#EC4899',
  engineering:     '#3B82F6',
  'game-development': '#10B981',
  marketing:       '#F59E0B',
  'paid-media':    '#EF4444',
  product:         '#6366F1',
  'project-management': '#14B8A6',
  sales:           '#F97316',
  'spatial-computing': '#06B6D4',
  specialized:     '#A855F7',
  strategy:        '#0EA5E9',
  support:         '#22C55E',
  testing:         '#E11D48',
};

// Categories that contain agent files (not documentation)
const AGENT_CATEGORIES = [
  'academic', 'design', 'engineering', 'game-development', 'marketing',
  'paid-media', 'product', 'project-management', 'sales',
  'spatial-computing', 'specialized', 'strategy', 'support', 'testing'
];

/**
 * Parse YAML frontmatter from markdown content
 */
function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return null;

  const frontmatter = {};
  for (const line of match[1].split('\n')) {
    const m = line.match(/^(\w+):\s*(.*)$/);
    if (m) {
      let val = m[2].trim();
      // Strip surrounding quotes
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      frontmatter[m[1]] = val;
    }
  }

  return {
    frontmatter,
    body: match[2].trim()
  };
}

/**
 * Recursively find all .md files in a directory
 */
function findMarkdownFiles(dir) {
  const files = [];
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...findMarkdownFiles(fullPath));
      } else if (entry.name.endsWith('.md')) {
        files.push(fullPath);
      }
    }
  } catch (e) { /* skip inaccessible dirs */ }
  return files;
}

/**
 * Extract top-level category from file path
 */
function getCategory(filePath, sourceDir) {
  const rel = relative(sourceDir, filePath);
  const topDir = rel.split('/')[0];
  // For game-development subcategories, keep parent
  if (['blender', 'godot', 'roblox-studio', 'unity', 'unreal-engine'].includes(topDir)) {
    return 'game-development';
  }
  return topDir;
}

// ── Main ──
const allFiles = findMarkdownFiles(SOURCE_DIR);
const agents = [];
const errors = [];

for (const file of allFiles) {
  try {
    const content = readFileSync(file, 'utf-8');
    const parsed = parseFrontmatter(content);
    if (!parsed || !parsed.frontmatter.name) continue;

    const category = getCategory(file, SOURCE_DIR);
    if (!AGENT_CATEGORIES.includes(category)) continue;

    const fileName = basename(file, '.md');
    // Generate slug from category + filename
    const slug = `${category}/${fileName}`;

    agents.push({
      name: parsed.frontmatter.name,
      slug,
      description: parsed.frontmatter.description || '',
      emoji: parsed.frontmatter.emoji || '🤖',
      color: parsed.frontmatter.color || CATEGORY_COLORS[category] || '#6B7280',
      category,
      vibe: parsed.frontmatter.vibe || '',
      file_path: file,
      content: parsed.body,
      raw: content,
    });
  } catch (e) {
    errors.push({ file, error: e.message });
  }
}

// Sort by category then name
agents.sort((a, b) => {
  const cat = a.category.localeCompare(b.category);
  return cat !== 0 ? cat : a.name.localeCompare(b.name);
});

// Build category summary
const categories = {};
for (const agent of agents) {
  if (!categories[agent.category]) {
    categories[agent.category] = {
      name: agent.category,
      count: 0,
      color: CATEGORY_COLORS[agent.category] || '#6B7280',
    };
  }
  categories[agent.category].count++;
}

const index = {
  generated: new Date().toISOString(),
  total: agents.length,
  categories,
  agents,
};

if (!existsSync(OUTPUT_DIR)) mkdirSync(OUTPUT_DIR, { recursive: true });
const outputPath = join(OUTPUT_DIR, 'agents-index.json');
writeFileSync(outputPath, JSON.stringify(index, null, 2));

console.log(`✅ Scanned ${agents.length} agents across ${Object.keys(categories).length} categories`);
console.log(`   Output: ${outputPath}`);
if (errors.length > 0) {
  console.log(`⚠️  ${errors.length} errors encountered`);
  for (const e of errors) {
    console.log(`   ${e.file}: ${e.error}`);
  }
}
