// Live reproduction of "Synchronizuj nieaktualne" bug.
// Runs against REAL backend on 127.0.0.1:8000 + REAL Vite dev server.
import { chromium } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:5173';
const TIMEOUT_MS = 120_000;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

// Capture everything
const consoleMsgs = [];
const pageErrors = [];
const networkRequests = [];
const networkResponses = [];

page.on('console', (msg) => {
    consoleMsgs.push(`[${msg.type()}] ${msg.text()}`);
});
page.on('pageerror', (err) => pageErrors.push(err.message));

// Intercept /mcc/overview and rewrite last_synced_at to force "stale" state
await page.route('**/api/v1/mcc/overview*', async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if (json?.accounts) {
        for (const a of json.accounts) {
            a.last_synced_at = '2025-01-01T00:00:00+00:00'; // ancient → stale
        }
    }
    await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(json),
    });
});

page.on('request', (req) => {
    if (req.url().includes('/api/v1/')) {
        networkRequests.push({ method: req.method(), url: req.url(), t: Date.now() });
    }
});
page.on('response', async (res) => {
    if (res.url().includes('/api/v1/')) {
        let body = '';
        try { body = (await res.text()).slice(0, 400); } catch {}
        networkResponses.push({ status: res.status(), url: res.url(), body, t: Date.now() });
    }
});
page.on('requestfailed', (req) => {
    if (req.url().includes('/api/v1/')) {
        networkResponses.push({
            status: 'FAILED',
            url: req.url(),
            body: req.failure()?.errorText || 'unknown',
            t: Date.now(),
        });
    }
});

console.log('>> Navigating to MCC Overview...');
await page.goto(`${FRONTEND_URL}/mcc-overview`, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });

// Wait for page render
try {
    await page.waitForSelector('h1:has-text("Wszystkie konta")', { timeout: 15_000 });
} catch {
    console.log('!! Header not found — dumping page HTML:');
    console.log((await page.content()).slice(0, 2000));
}

// Wait until accounts table has data or we see "no data"
await page.waitForTimeout(3000);

const buttonCount = await page.locator('button:has-text("Synchronizuj nieaktualne")').count();
console.log(`>> "Synchronizuj nieaktualne" button count: ${buttonCount}`);

if (buttonCount === 0) {
    console.log('!! Button not rendered — page may not be logged in.');
    console.log('Console messages:');
    consoleMsgs.forEach((m) => console.log('  ', m));
    console.log('Network:');
    networkResponses.forEach((r) => console.log(`  ${r.status} ${r.url}`));
    await browser.close();
    process.exit(1);
}

// Clear logs to focus on what happens after click
const preClickReq = networkRequests.length;
const preClickRes = networkResponses.length;
const preClickConsole = consoleMsgs.length;

console.log('>> Clicking "Synchronizuj nieaktualne"...');
const clickStart = Date.now();
await page.locator('button:has-text("Synchronizuj nieaktualne")').click();

// Wait 90s for all requests to complete or fail
console.log('>> Waiting 90s for sync requests to finish...');
await page.waitForTimeout(90_000);

console.log('\n========== RESULTS ==========');
console.log(`Elapsed: ${((Date.now() - clickStart) / 1000).toFixed(1)}s`);

console.log('\n-- Requests after click --');
networkRequests.slice(preClickReq).forEach((r) => {
    console.log(`  ${r.method} ${r.url}`);
});

console.log('\n-- Responses after click --');
networkResponses.slice(preClickRes).forEach((r) => {
    const elapsed = ((r.t - clickStart) / 1000).toFixed(1);
    console.log(`  [+${elapsed}s] ${r.status} ${r.url}`);
    if (r.status !== 200) {
        console.log(`    body: ${r.body}`);
    }
});

console.log('\n-- Console messages after click --');
consoleMsgs.slice(preClickConsole).forEach((m) => console.log('  ', m));

console.log('\n-- Page errors --');
pageErrors.forEach((e) => console.log('  ', e));

await browser.close();
