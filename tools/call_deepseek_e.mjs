// Call DeepSeek official API for route E. Key is read from .credentials.yaml (never printed).
import { readFileSync, writeFileSync } from 'node:fs';

const cred = readFileSync('C:/Users/34045/.dsh/.credentials.yaml', 'utf8');
const m = cred.match(/DEEPSEEK_API_KEY:\s*(\S+)/);
if (!m) { console.error('NO DEEPSEEK_API_KEY FOUND'); process.exit(1); }
const KEY = m[1];

const prompt = readFileSync('C:/Users/34045/Documents/ds harness/routeE_prompt.txt', 'utf8');

const models = [
  { model: 'deepseek-v4-pro', extra: { thinking: { type: 'enabled' }, reasoning_effort: 'max' } },
  { model: 'deepseek-v4-pro', extra: {} },
  { model: 'deepseek-chat', extra: {} },
  { model: 'deepseek-reasoner', extra: {} }
];
let lastErr = null;

for (const cfg of models) {
  try {
    const body = Object.assign({
      model: cfg.model,
      messages: [{ role: 'user', content: prompt }],
      stream: false,
      max_tokens: 64000
    }, cfg.extra);
    const resp = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY },
      body: JSON.stringify(body)
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.choices || !data.choices[0] || !data.choices[0].message) {
      lastErr = 'HTTP ' + resp.status + ' model=' + cfg.model + ' err=' + JSON.stringify(data.error || data).slice(0, 300);
      console.log('[try] ' + lastErr);
      continue;
    }
    const content = data.choices[0].message.content || '';
    writeFileSync('C:/Users/34045/Documents/ds harness/routeE_report.md', content, 'utf8');
    console.log('OK model=' + cfg.model);
    console.log('usage=' + JSON.stringify(data.usage || {}));
    console.log('content_len=' + content.length);
    console.log(content.slice(0, 300));
    process.exit(0);
  } catch (e) {
    lastErr = 'EXC ' + e.message;
    console.log('[try] model=' + cfg.model + ' ' + lastErr);
  }
}
console.error('ALL MODELS FAILED: ' + lastErr);
process.exit(2);
