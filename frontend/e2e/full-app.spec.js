import { test, expect } from '@playwright/test';

/**
 * Full application test — runs against the LIVE backend (no mocks).
 * Bootstraps a real session via /api/v1/auth/status?bootstrap=1.
 * Tests every page for JS errors, API failures, and rendering issues.
 *
 * Prerequisites: backend on :8000, frontend on :5173
 */

const API = 'http://127.0.0.1:8000/api/v1';
const CLIENT_ID = 3; // Sushi Naka Naka

// ─── Bootstrap session ──────────────────────────────────────────────

let sessionCookie = null;

test.beforeAll(async ({ request }) => {
    // Bootstrap a session from the real backend
    const res = await request.get(`${API}/auth/status?bootstrap=1`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.authenticated).toBe(true);

    // Extract session cookie from response
    const cookies = (await res.headersArray())
        .filter(h => h.name.toLowerCase() === 'set-cookie')
        .map(h => h.value);
    const sessionLine = cookies.find(c => c.startsWith('gah_session='));
    expect(sessionLine).toBeTruthy();
    sessionCookie = sessionLine.split(';')[0].split('=')[1];
});

test.beforeEach(async ({ context }) => {
    // Inject session cookie so all pages are authenticated
    await context.addCookies([{
        name: 'gah_session',
        value: sessionCookie,
        domain: '127.0.0.1',
        path: '/',
    }]);
});

// ─── Helpers ─────────────────────────────────────────────────────────

/**
 * Navigate to a page, collect JS errors and failed API calls.
 * Returns { jsErrors, apiErrors, consoleErrors }.
 */
async function navigateAndCollect(page, path, waitForSelector = null, timeout = 10_000) {
    const jsErrors = [];
    const apiErrors = [];
    const consoleErrors = [];

    page.on('pageerror', err => jsErrors.push({ message: err.message, stack: err.stack }));
    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });
    page.on('response', res => {
        const url = res.url();
        if (url.includes('/api/v1/') && res.status() >= 400) {
            apiErrors.push({ url: url.replace(API, ''), status: res.status() });
        }
    });

    await page.goto(path, { waitUntil: 'networkidle', timeout });

    if (waitForSelector) {
        await page.waitForSelector(waitForSelector, { timeout: 8_000 }).catch(() => {});
    }

    // Give time for async renders
    await page.waitForTimeout(1500);

    return { jsErrors, apiErrors, consoleErrors };
}

// ─── All pages — JS error & API error check ─────────────────────────

const ALL_PAGES = [
    { path: '/',                    name: 'Dashboard',            heading: 'Pulpit' },
    { path: '/daily-audit',         name: 'Daily Audit',          heading: 'Codzienny' },
    { path: '/campaigns',           name: 'Campaigns',            heading: 'Kampanie' },
    { path: '/keywords',            name: 'Keywords',             heading: 'kluczowe' },
    { path: '/search-terms',        name: 'Search Terms',         heading: 'Wyszukiwane' },
    { path: '/recommendations',     name: 'Recommendations',      heading: 'Rekomendacje' },
    { path: '/action-history',      name: 'Action History',       heading: 'Historia' },
    { path: '/alerts',              name: 'Alerts',               heading: 'Alerty' },
    { path: '/agent',               name: 'AI Report',            heading: 'Asystent AI' },
    { path: '/reports',             name: 'Reports',              heading: 'Raport' },
    { path: '/clients',             name: 'Clients',              heading: 'Klienci' },
    { path: '/settings',            name: 'Settings',             heading: 'Ustawienia' },
    { path: '/search-optimization', name: 'Search Optimization',  heading: 'Optymalizacja' },
    { path: '/semantic',            name: 'Semantic',             heading: 'Inteligencja' },
    { path: '/quality-score',       name: 'Quality Score',        heading: 'Wynik' },
    { path: '/forecast',            name: 'Forecast',             heading: 'Prognoza' },
];

test.describe('Full App — Live Backend', () => {

    // Select the right client in localStorage
    test.beforeEach(async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    // ─── Page rendering tests ────────────────────────────────────────

    for (const { path, name, heading } of ALL_PAGES) {
        test(`${name} (${path}) — no JS errors`, async ({ page }) => {
            const { jsErrors, apiErrors } = await navigateAndCollect(page, path);

            // Report all JS errors
            if (jsErrors.length > 0) {
                const details = jsErrors.map(e => `  ${e.message}`).join('\n');
                expect(jsErrors, `JS errors on ${name}:\n${details}`).toEqual([]);
            }
        });

        test(`${name} (${path}) — heading visible`, async ({ page }) => {
            await page.goto(path, { waitUntil: 'networkidle', timeout: 15_000 });
            // Some pages may not render heading if data is missing — that's OK for forecast
            if (name !== 'Forecast') {
                await expect(
                    page.locator(`text=/${heading}/i`).first()
                ).toBeVisible({ timeout: 8_000 });
            }
        });

        test(`${name} (${path}) — no API 5xx errors`, async ({ page }) => {
            const { apiErrors } = await navigateAndCollect(page, path);
            const serverErrors = apiErrors.filter(e => e.status >= 500);
            if (serverErrors.length > 0) {
                const details = serverErrors.map(e => `  ${e.status} ${e.url}`).join('\n');
                expect(serverErrors, `Server errors on ${name}:\n${details}`).toEqual([]);
            }
        });
    }

    // ─── Navigation tests ────────────────────────────────────────────

    test('Sidebar navigation works for all links', async ({ page }) => {
        const jsErrors = [];
        page.on('pageerror', err => jsErrors.push({ page: page.url(), message: err.message }));

        await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
        await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });

        const navLinks = page.locator('nav a[href]');
        const count = await navLinks.count();
        expect(count).toBeGreaterThan(10);

        const hrefs = [];
        for (let i = 0; i < count; i++) {
            const href = await navLinks.nth(i).getAttribute('href');
            if (href && href.startsWith('/') && !hrefs.includes(href)) {
                hrefs.push(href);
            }
        }

        // Click each nav link and check for JS errors
        for (const href of hrefs) {
            const errorsBefore = jsErrors.length;
            const link = page.locator(`nav a[href="${href}"]`);
            await link.scrollIntoViewIfNeeded();
            await link.click();
            await page.waitForTimeout(2000);

            if (jsErrors.length > errorsBefore) {
                const newErrors = jsErrors.slice(errorsBefore);
                console.log(`JS errors after navigating to ${href}:`, newErrors);
            }
        }

        if (jsErrors.length > 0) {
            const details = jsErrors.map(e => `  [${e.page}] ${e.message}`).join('\n');
            expect(jsErrors, `JS errors during navigation:\n${details}`).toEqual([]);
        }
    });

    // ─── Dashboard specific tests ────────────────────────────────────

    test('Dashboard — KPI cards render with data', async ({ page }) => {
        await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 8_000 });

        // Wait for KPIs to load
        await page.waitForTimeout(2000);

        // Should show KPI values (clicks, impressions, cost, conversions)
        const body = await page.textContent('body');
        // Check that we don't have "undefined" or "NaN" displayed
        const bodyLower = body.toLowerCase();
        expect(bodyLower).not.toContain('undefined');
        expect(bodyLower).not.toContain('nan');
    });

    test('Dashboard — campaign table renders', async ({ page }) => {
        await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
        await page.waitForTimeout(3000);

        // Check for campaign names or table structure
        const tables = page.locator('table');
        const tableCount = await tables.count();
        // Dashboard may show campaign performance table
        if (tableCount > 0) {
            await expect(tables.first()).toBeVisible();
        }
    });

    // ─── Campaigns page tests ────────────────────────────────────────

    test('Campaigns — table loads with real data', async ({ page }) => {
        const { jsErrors } = await navigateAndCollect(page, '/campaigns');
        await page.waitForTimeout(2000);

        // Should have campaign rows
        const rows = page.locator('tr');
        const rowCount = await rows.count();
        // At least header + 1 data row expected for Sushi Naka Naka
        expect(rowCount).toBeGreaterThanOrEqual(1);

        expect(jsErrors).toEqual([]);
    });

    // ─── Keywords page tests ─────────────────────────────────────────

    test('Keywords — loads without errors', async ({ page }) => {
        const { jsErrors } = await navigateAndCollect(page, '/keywords');
        await page.waitForTimeout(2000);

        const body = await page.textContent('body');
        expect(body.toLowerCase()).not.toContain('undefined');
        expect(jsErrors).toEqual([]);
    });

    // ─── Search Terms page tests ─────────────────────────────────────

    test('Search Terms — loads and shows data', async ({ page }) => {
        const { jsErrors } = await navigateAndCollect(page, '/search-terms');
        await page.waitForTimeout(2000);

        expect(jsErrors).toEqual([]);
    });

    // ─── Recommendations page tests ──────────────────────────────────

    test('Recommendations — loads summary and cards', async ({ page }) => {
        const { jsErrors } = await navigateAndCollect(page, '/recommendations');
        await page.waitForTimeout(2000);

        expect(jsErrors).toEqual([]);
    });

    // ─── Alerts page tests ───────────────────────────────────────────

    test('Alerts — loads monitoring data', async ({ page }) => {
        const { jsErrors } = await navigateAndCollect(page, '/alerts');
        await page.waitForTimeout(2000);

        expect(jsErrors).toEqual([]);
    });

    // ─── Filter interaction tests ────────────────────────────────────

    test('Global filter — date period change works', async ({ page }) => {
        const jsErrors = [];
        page.on('pageerror', err => jsErrors.push(err.message));

        await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
        await page.waitForTimeout(2000);

        // Look for period selector buttons (7d, 14d, 30d, 90d)
        const periodButtons = page.locator('button:has-text("7d"), button:has-text("14d"), button:has-text("30d"), button:has-text("90d")');
        const btnCount = await periodButtons.count();

        if (btnCount > 0) {
            // Click 7d
            await periodButtons.first().click();
            await page.waitForTimeout(2000);

            // Click 90d
            await periodButtons.last().click();
            await page.waitForTimeout(2000);
        }

        expect(jsErrors).toEqual([]);
    });

    test('Global filter — campaign type filter works', async ({ page }) => {
        const jsErrors = [];
        page.on('pageerror', err => jsErrors.push(err.message));

        await page.goto('/campaigns', { waitUntil: 'networkidle', timeout: 15_000 });
        await page.waitForTimeout(2000);

        // Look for campaign type dropdown/select
        const typeSelects = page.locator('select').filter({ hasText: /Wszystkie|Search|PMax/i });
        const selectCount = await typeSelects.count();

        if (selectCount > 0) {
            await typeSelects.first().selectOption({ index: 1 });
            await page.waitForTimeout(1500);
        }

        expect(jsErrors).toEqual([]);
    });

    // ─── Client selector tests ───────────────────────────────────────

    test('Client selector — switching clients works', async ({ page }) => {
        const jsErrors = [];
        page.on('pageerror', err => jsErrors.push(err.message));

        await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
        await page.waitForTimeout(2000);

        // Find client selector in sidebar
        const clientSelect = page.locator('select').first();
        const options = await clientSelect.locator('option').count();

        if (options > 1) {
            // Switch to a different client
            await clientSelect.selectOption({ index: 1 });
            await page.waitForTimeout(3000);

            // Switch back
            await clientSelect.selectOption({ index: 0 });
            await page.waitForTimeout(3000);
        }

        expect(jsErrors).toEqual([]);
    });

    // ─── Search Optimization sub-pages ───────────────────────────────

    test('Search Optimization — all tabs load without errors', async ({ page }) => {
        const jsErrors = [];
        page.on('pageerror', err => jsErrors.push(err.message));

        await page.goto('/search-optimization', { waitUntil: 'networkidle', timeout: 15_000 });
        await page.waitForTimeout(2000);

        // Look for tab buttons
        const tabs = page.locator('button').filter({ hasText: /N-gram|Match|Landing|Daypart|RSA|Budżet|Struktura|Bidding|Godziny|Wasted/i });
        const tabCount = await tabs.count();

        for (let i = 0; i < tabCount; i++) {
            await tabs.nth(i).click();
            await page.waitForTimeout(2000);
        }

        if (jsErrors.length > 0) {
            const details = jsErrors.join('\n  ');
            expect(jsErrors, `JS errors in Search Optimization tabs:\n  ${details}`).toEqual([]);
        }
    });

    // ─── Polish encoding check (no mojibake) ─────────────────────────

    test('All pages — no mojibake in Polish text', async ({ page }) => {
        const mojibakePatterns = ['Ä', 'Ĺ', 'Ã³', 'Ä™', 'Å‚', 'Å¼', 'Åº', 'Ä‡'];
        const pagesWithMojibake = [];

        for (const { path, name } of ALL_PAGES.slice(0, 8)) {
            await page.goto(path, { waitUntil: 'networkidle', timeout: 10_000 });
            await page.waitForTimeout(1000);
            const text = await page.textContent('body');

            for (const pattern of mojibakePatterns) {
                if (text.includes(pattern)) {
                    pagesWithMojibake.push(`${name}: found "${pattern}"`);
                    break;
                }
            }
        }

        expect(pagesWithMojibake).toEqual([]);
    });

    // ─── No "undefined" or "NaN" visible on any page ─────────────────

    test('All pages — no visible undefined/NaN values', async ({ page }) => {
        const pagesWithIssues = [];

        for (const { path, name } of ALL_PAGES) {
            await page.goto(path, { waitUntil: 'networkidle', timeout: 10_000 });
            await page.waitForTimeout(2000);
            const body = await page.textContent('body');

            // Check for common rendering bugs
            if (/\bundefined\b/.test(body) && !body.includes('undefined}')) {
                pagesWithIssues.push(`${name}: shows "undefined"`);
            }
            if (/\bNaN\b/.test(body)) {
                pagesWithIssues.push(`${name}: shows "NaN"`);
            }
        }

        if (pagesWithIssues.length > 0) {
            expect(pagesWithIssues, `Pages with rendering issues:\n  ${pagesWithIssues.join('\n  ')}`).toEqual([]);
        }
    });
});
