#!/usr/bin/env node
/**
 * server.js — Agency Agents Manager API Server
 * Pure Node.js http module, no external dependencies
 * Port: 3456
 */

import { createServer } from 'node:http';
import { readFileSync, writeFileSync, existsSync, copyFileSync, mkdirSync, readdirSync, unlinkSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || '3456');
const DATA_DIR = join(__dirname, '..', 'data');
const INDEX_PATH = join(DATA_DIR, 'agents-index.json');
const WEB_DIR = join(__dirname, '..', 'web');
const SOUL_MD = join(process.env.HOME || '/root', '.openclaw', 'workspace', 'SOUL.md');
const SOUL_BACKUP = SOUL_MD + '.backup.default';
const ACTIVE_FILE = join(DATA_DIR, 'active-agent.json');

// ── CORS helpers ──
function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, PUT, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function jsonResponse(res, data, status = 200) {
  setCors(res);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function textResponse(res, text, status = 200) {
  setCors(res);
  res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end(text);
}

// ── Index management ──
function loadIndex() {
  if (!existsSync(INDEX_PATH)) {
    return { generated: null, total: 0, categories: {}, agents: [] };
  }
  return JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
}

function saveIndex(index) {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });
  index.generated = new Date().toISOString();
  writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2));
}

// ── Active agent management ──
function getActiveAgent() {
  if (!existsSync(ACTIVE_FILE)) return null;
  try { return JSON.parse(readFileSync(ACTIVE_FILE, 'utf-8')); } catch { return null; }
}

function setActiveAgent(agent) {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });
  writeFileSync(ACTIVE_FILE, JSON.stringify({
    slug: agent.slug,
    name: agent.name,
    emoji: agent.emoji,
    activatedAt: new Date().toISOString(),
  }));
}

function clearActiveAgent() {
  if (existsSync(ACTIVE_FILE)) {
    try { unlinkSync(ACTIVE_FILE); } catch {}
  }
}

// ── Route parsing ──
function parseRoute(url) {
  const [pathname, qs] = url.split('?');
  const params = {};
  if (qs) {
    for (const pair of qs.split('&')) {
      const [k, v] = pair.split('=');
      params[decodeURIComponent(k)] = decodeURIComponent(v || '');
    }
  }
  return { pathname, params };
}

// ── Request body parser ──
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf-8');
      try { resolve(JSON.parse(raw)); } catch { resolve(raw); }
    });
    req.on('error', reject);
  });
}

// ── Route handlers ──

// GET /api/agents — list all agents
function handleListAgents(params) {
  const index = loadIndex();
  const { category, search, sort } = params;
  let agents = [...index.agents];

  if (category && category !== 'all') {
    agents = agents.filter(a => a.category === category);
  }

  if (search) {
    const q = search.toLowerCase();
    agents = agents.filter(a =>
      a.name.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      a.category.toLowerCase().includes(q)
    );
  }

  if (sort === 'name') agents.sort((a, b) => a.name.localeCompare(b.name));
  else if (sort === 'category') agents.sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));

  // Mark customized agents
  const customSet = new Set();
  try {
    if (existsSync(join(DATA_DIR, 'customized.json'))) {
      const custom = JSON.parse(readFileSync(join(DATA_DIR, 'customized.json'), 'utf-8'));
      for (const s of custom) customSet.add(s);
    }
  } catch {}

  return {
    total: agents.length,
    agents: agents.map(a => ({
      name: a.name,
      slug: a.slug,
      description: a.description,
      emoji: a.emoji,
      color: a.color,
      category: a.category,
      customized: customSet.has(a.slug),
    })),
  };
}

// GET /api/agents/:slug — single agent detail
function handleGetAgent(slug) {
  const index = loadIndex();
  const agent = index.agents.find(a => a.slug === slug);
  if (!agent) return { error: 'Agent not found', slug };

  return {
    ...agent,
    customized: isCustomized(slug),
  };
}

// PUT /api/agents/:slug — update agent content
function handleUpdateAgent(slug, body) {
  if (!body || !body.content) return { error: 'Missing content field' };

  const index = loadIndex();
  const agentIndex = index.agents.findIndex(a => a.slug === slug);
  if (agentIndex === -1) return { error: 'Agent not found', slug };

  const agent = index.agents[agentIndex];

  // Rebuild the full markdown with original frontmatter
  const newRaw = `---\nname: ${agent.name}\ndescription: ${agent.description}\ncolor: "${agent.color}"\nemoji: ${agent.emoji}\n---\n\n${body.content}\n`;

  // Write back to source file
  try {
    writeFileSync(agent.file_path, newRaw);
    // Update index
    index.agents[agentIndex].content = body.content;
    index.agents[agentIndex].raw = newRaw;
    saveIndex(index);

    // Mark as customized
    markCustomized(slug);
  } catch (e) {
    return { error: 'Failed to write file', details: e.message };
  }

  return { success: true, slug, name: agent.name };
}

// POST /api/agents/:slug/activate — activate agent
function handleActivate(slug) {
  const index = loadIndex();
  const agent = index.agents.find(a => a.slug === slug);
  if (!agent) return { error: 'Agent not found', slug };

  try {
    // Backup current SOUL.md if not already backed up
    if (!existsSync(SOUL_BACKUP) && existsSync(SOUL_MD)) {
      copyFileSync(SOUL_MD, SOUL_BACKUP);
    }

    // Write agent content to SOUL.md
    const soulContent = `# SOUL.md — ${agent.emoji} ${agent.name}\n\n> Activated from Agency Agents on ${new Date().toISOString()}\n> Original: ${slug}\n\n${agent.content}\n`;
    writeFileSync(SOUL_MD, soulContent);

    setActiveAgent(agent);
    return { success: true, name: agent.name, slug, message: `Activated ${agent.name}` };
  } catch (e) {
    return { error: 'Failed to activate', details: e.message };
  }
}

// POST /api/agents/deactivate — restore default SOUL.md
function handleDeactivate() {
  try {
    if (existsSync(SOUL_BACKUP)) {
      copyFileSync(SOUL_BACKUP, SOUL_MD);
      clearActiveAgent();
      return { success: true, message: 'Restored default SOUL.md' };
    }
    return { error: 'No backup found. Cannot restore.' };
  } catch (e) {
    return { error: 'Failed to restore', details: e.message };
  }
}

// GET /api/status — current active agent
function handleStatus() {
  const active = getActiveAgent();
  return {
    active: active,
    backupExists: existsSync(SOUL_BACKUP),
    totalAgents: loadIndex().total,
  };
}

// GET /api/categories — category list
function handleCategories() {
  const index = loadIndex();
  const cats = [];
  for (const [key, val] of Object.entries(index.categories)) {
    cats.push({ name: key, count: val.count, color: val.color });
  }
  return { categories: cats };
}

// ── Customized tracking ──
function isCustomized(slug) {
  try {
    const path = join(DATA_DIR, 'customized.json');
    if (!existsSync(path)) return false;
    const arr = JSON.parse(readFileSync(path, 'utf-8'));
    return arr.includes(slug);
  } catch { return false; }
}

function markCustomized(slug) {
  try {
    const path = join(DATA_DIR, 'customized.json');
    let arr = [];
    if (existsSync(path)) arr = JSON.parse(readFileSync(path, 'utf-8'));
    if (!arr.includes(slug)) {
      arr.push(slug);
      writeFileSync(path, JSON.stringify(arr, null, 2));
    }
  } catch {}
}

// ── Main request handler ──
async function handleRequest(req, res) {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    setCors(res);
    res.writeHead(204);
    res.end();
    return;
  }

  const { pathname, params } = parseRoute(req.url);

  try {
    // ── Static HTML ──
    if (pathname === '/' && req.method === 'GET') {
      const htmlPath = join(WEB_DIR, 'index.html');
      const html = readFileSync(htmlPath, 'utf-8');
      setCors(res);
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }

    // ── API routes ──
    if (pathname === '/api/agents' && req.method === 'GET') {
      jsonResponse(res, handleListAgents(params));
      return;
    }

    // GET /api/agents/:slug  (slug may contain /, e.g. design/design-ui-designer)
    // We match /api/agents/(anything) but not /api/agents/(anything)/activate or /api/agents/deactivate
    const agentsBase = '/api/agents/';
    if (pathname.startsWith(agentsBase) && req.method === 'GET') {
      const slug = decodeURIComponent(pathname.slice(agentsBase.length));
      if (slug && slug !== 'deactivate') {
        jsonResponse(res, handleGetAgent(slug));
        return;
      }
    }

    // PUT /api/agents/:slug
    if (pathname.startsWith(agentsBase) && req.method === 'PUT') {
      const slug = decodeURIComponent(pathname.slice(agentsBase.length));
      const body = await readBody(req);
      jsonResponse(res, handleUpdateAgent(slug, body));
      return;
    }

    // POST /api/agents/:slug/activate
    if (pathname.startsWith(agentsBase) && req.method === 'POST') {
      const suffix = decodeURIComponent(pathname.slice(agentsBase.length));
      if (suffix.endsWith('/activate')) {
        const slug = suffix.slice(0, -'/activate'.length);
        jsonResponse(res, handleActivate(slug));
        return;
      }
    }

    // POST /api/agents/deactivate
    if (pathname === '/api/agents/deactivate' && req.method === 'POST') {
      jsonResponse(res, handleDeactivate());
      return;
    }

    // GET /api/status
    if (pathname === '/api/status' && req.method === 'GET') {
      jsonResponse(res, handleStatus());
      return;
    }

    // GET /api/categories
    if (pathname === '/api/categories' && req.method === 'GET') {
      jsonResponse(res, handleCategories());
      return;
    }

    // 404
    jsonResponse(res, { error: 'Not found', path: pathname }, 404);

  } catch (e) {
    console.error('Server error:', e);
    jsonResponse(res, { error: 'Internal server error', details: e.message }, 500);
  }
}

// ── Start server ──
const server = createServer(handleRequest);
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Agency Agents Manager running at http://localhost:${PORT}`);
  console.log(`   API: http://localhost:${PORT}/api/agents`);
  console.log(`   Total agents: ${loadIndex().total}`);
});
