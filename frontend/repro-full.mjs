// Full reproduction: Discover → Synchronizuj nieaktualne → capture everything
import { chromium } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const events = []; // unified log

function log(type, msg) {
    events.push({ t: Date.now(), type, msg });
}

page.on('console', (msg) => log('console', `[${msg.type()}] ${msg.text()}`));
page.on('pageerror', (err) => log('pageerror', err.message));
page.on('request', (req) => {
    if (req.url().includes('/api/v1/')) {
        log('request', `${req.method()} ${req.url().replace(FRONTEND_URL, '')}`);
    }
});
page.on('response', async (res) => {
    if (res.url().includes('/api/v1/')) {
        let bodyPreview = '';
        if (res.status() !== 200) {
            try { bodyPreview = (await res.text()).slice(0, 400); } catch {}
        }
        log('response', `${res.status()} ${res.url().replace(FRONTEND_URL, '')}${bodyPreview ? ' body=' + bodyPreview : ''}`);
    }
});
page.on('requestfailed', (req) => {
    if (req.url().includes('/api/v1/')) {
        log('failed', `${req.url().replace(FRONTEND_URL, '')} ${req.failure()?.errorText || ''}`);
    }
});

// Force all accounts to appear stale (match user's real situation)
await page.route('**/api/v1/mcc/overview*', async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if (json?.accounts) {
        for (const a of json.accounts) a.last_synced_at = '2025-01-01T00:00:00+00:00';
    }
    await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(json),
    });
});

log('step', '=== Navigate to MCC ===');
await page.goto(`${FRONTEND_URL}/mcc-overview`, { waitUntil: 'networkidle', timeout: 60_000 });

try {
    await page.waitForSelector('h1:has-text("Wszystkie konta")', { timeout: 10_000 });
} catch {
    log('fatal', 'MCC page header not found');
}

await page.waitForTimeout(2000);

log('step', '=== Click Odkryj konta ===');
await page.locator('button:has-text("Odkryj konta")').click();
await page.waitForTimeout(3000);

log('step', '=== Click Synchronizuj nieaktualne ===');
const clickT = Date.now();
await page.locator('button:has-text("Synchronizuj nieaktualne")').click();

// Wait 120s to cover 3 syncs at 40s each
log('step', '=== Waiting 120s ===');
await page.waitForTimeout(120_000);

log('step', '=== Done ===');

// Pretty print
const t0 = events[0]?.t || Date.now();
const ctxStart = clickT - t0;
console.log(`Click "Synchronizuj" at t=${(ctxStart / 1000).toFixed(1)}s relative\n`);
for (const e of events) {
    const elapsed = ((e.t - t0) / 1000).toFixed(1).padStart(6);
    console.log(`[${elapsed}s] ${e.type.padEnd(9)} ${e.msg}`);
}

// Summary
const responses = events.filter((e) => e.type === 'response');
const nonOk = responses.filter((e) => !e.msg.startsWith('200 '));
const failed = events.filter((e) => e.type === 'failed');
const consoleErrors = events.filter((e) => e.type === 'console' && e.msg.startsWith('[error]'));
console.log('\n========== SUMMARY ==========');
console.log(`API responses: ${responses.length}`);
console.log(`Non-200 responses: ${nonOk.length}`);
nonOk.forEach((r) => console.log(`  ${r.msg}`));
console.log(`Failed (aborted/network): ${failed.length}`);
failed.forEach((r) => console.log(`  ${r.msg}`));
console.log(`Console errors: ${consoleErrors.length}`);
consoleErrors.forEach((r) => console.log(`  ${r.msg}`));

await browser.close();
