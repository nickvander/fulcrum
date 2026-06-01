// Brand-moments screenshot capture (loop 4).
// Usage: node brand-capture.mjs [theme:dark|light]
// Writes PNGs to work/ux-loop/shots/<theme>/
// Reuses the proven login flow from work/redesign/shots/capture2.mjs.
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const THEME = (process.argv[2] || 'dark').toLowerCase();
const BASE = process.env.SHOT_BASE || 'http://127.0.0.1:4200';
const EMAIL = 'admin@example.com';
const PASS = 'SecurePass123!';
const OUTDIR = new URL('.', import.meta.url).pathname + THEME + '/';
mkdirSync(OUTDIR, { recursive: true });

// Brand surfaces that actually exercise the loop-4 work.
const routes = [
  ['dashboard', '/dashboard'],          // honest-number hero KPIs + profit-summary widget
  ['profit', '/reports/profit'],        // the "honest MXN number" signature page
  ['buyer-questions', '/reports/qa'],   // peer empty-state (if no questions) / Q&A
  ['products', '/products'],            // peer empty-state (if no products)
  ['orders', '/orders'],                // orders list (margin column, money)
  ['marketing', '/marketing'],          // entry to the AI quick-post dialog
];

const log = (...a) => console.log('[brand-shot]', ...a);

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(25000);

await ctx.addInitScript((theme) => {
  try {
    localStorage.setItem('fulcrum_settings', JSON.stringify({
      ai_provider: '', ai_api_key: '', theme, language: 'es-MX',
    }));
  } catch (e) {}
}, THEME);

async function loginOnce() {
  let lastStatus = null;
  const onResp = (r) => {
    if (/\/login\/access-token/.test(r.url()) && r.request().method() === 'POST') lastStatus = r.status();
  };
  page.on('response', onResp);
  try {
    await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
    await page.waitForTimeout(600);
    await page.locator('input[type="email"], input[formcontrolname="email"]').first().fill(EMAIL);
    await page.locator('input[type="password"], input[formcontrolname="password"]').first().fill(PASS);
    await page.waitForFunction(
      () => { const b = document.querySelector('button[type="submit"]'); return b && !b.disabled; },
      { timeout: 6000 },
    ).catch(() => {});
    await page.locator('button[type="submit"]').first().click();
    try { await page.waitForURL(/dashboard|products/, { timeout: 12000 }); }
    catch { return { ok: false, reason: 'no-nav', status: lastStatus, url: page.url() }; }
    if (lastStatus !== null && lastStatus !== 200) return { ok: false, reason: 'auth-' + lastStatus };
    return { ok: true, status: lastStatus };
  } finally { page.off('response', onResp); }
}

async function robustLogin() {
  let last = null;
  for (let attempt = 1; attempt <= 4; attempt++) {
    last = await loginOnce();
    if (last.ok) { log('login OK', page.url(), 'theme=', THEME); return; }
    log('login attempt', attempt, 'failed', JSON.stringify(last), '- reload+retry');
    await page.reload({ waitUntil: 'networkidle' }).catch(() => {});
    await page.waitForTimeout(1200);
  }
  throw new Error('login failed: ' + JSON.stringify(last));
}

await robustLogin();

async function shot(name, route) {
  try {
    await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 25000 });
    await page.waitForTimeout(1600);
    await page.screenshot({ path: `${OUTDIR}${name}.png`, fullPage: true });
    log('captured', name, route);
  } catch (e) { log('FAIL', name, route, e.message); }
}

for (const [name, route] of routes) await shot(name, route);

// Best-effort: open the AI quick-post dialog from /marketing to capture the
// gold AI treatment (ai-prompt-preview / panel header auto_awesome icon).
try {
  await page.goto(BASE + '/marketing', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  // Find a button that opens the quick-post / "publicación" dialog.
  const trigger = page.locator(
    'button:has-text("Publicación"), button:has-text("publicación"), button:has-text("Quick"), button:has-text("Post"), button:has-text("IA"), button:has-text("Crear")'
  ).first();
  if (await trigger.count()) {
    await trigger.click();
    await page.waitForTimeout(1500);
    const dialog = page.locator('mat-dialog-container, [role="dialog"]').first();
    if (await dialog.count()) {
      await dialog.screenshot({ path: `${OUTDIR}ai-quick-post-dialog.png` });
      log('captured ai-quick-post-dialog');
    } else { log('no dialog appeared for AI capture'); }
  } else { log('no quick-post trigger found on /marketing'); }
} catch (e) { log('AI dialog capture skipped:', e.message); }

await browser.close();
log('DONE theme=', THEME);
