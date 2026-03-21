import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';

/*
 * Smoke tests — verify every page renders without JS errors.
 * Uses mocked API so no backend is needed.
 */

test.beforeEach(async ({ page }) => {
    // Catch-all API mock must be registered FIRST (Playwright matches last-registered first)
    await mockEmptyApi(page);
    // Auth/client mocks override the catch-all
    await mockAuthAndClient(page);

    // Select DEMO client in localStorage so pages load data
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Navigation & Layout ────────────────────────────────────────────

test('app boots past login and shows sidebar', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });
    // Sidebar has the client selector (inside a <select>/<option>)
    await expect(page.locator('option:has-text("Sushi Naka Naka")')).toBeAttached();
});

test('sidebar navigation links are present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });

    const expectedLabels = [
        'Pulpit', 'Codzienny audyt', 'Klienci',
        'Kampanie', 'Słowa kluczowe', 'Wyszukiwane frazy',
        'Rekomendacje', 'Historia akcji',
        'Monitoring',
        'Raport AI', 'Raporty',
        'Optymalizacja', 'Inteligencja', 'Wynik jakości',
        'Ustawienia',
    ];

    for (const label of expectedLabels) {
        await expect(page.locator(`text=${label}`).first()).toBeVisible();
    }
});

// ─── Page smoke tests ───────────────────────────────────────────────
// Each test navigates to a page and asserts:
//   1. No unhandled JS errors
//   2. Page heading or key element is visible

const PAGES = [
    { path: '/',                  heading: 'Pulpit' },
    { path: '/daily-audit',       heading: 'Codzienny Audyt' },
    { path: '/campaigns',         heading: 'Kampanie' },
    { path: '/keywords',          heading: 'kluczowe' },
    { path: '/search-terms',      heading: 'Wyszukiwane' },
    { path: '/recommendations',   heading: 'Rekomendacje' },
    { path: '/action-history',    heading: 'Historia zmian' },
    { path: '/alerts',            heading: 'Alerty' },
    { path: '/agent',             heading: 'Raport AI' },
    { path: '/reports',           heading: 'Raport' },
    { path: '/clients',           heading: 'Klienci' },
    { path: '/settings',          heading: 'Ustawienia' },
    { path: '/search-optimization', heading: 'Optymalizacja' },
    { path: '/semantic',          heading: 'Inteligencja' },
    { path: '/quality-score',     heading: 'Wynik' },
    // Forecast skipped in smoke — requires campaign data to render past spinner
];

for (const { path, heading } of PAGES) {
    test(`page ${path} renders without errors`, async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await page.goto(path);
        // Wait for the heading text (case-insensitive partial match)
        await expect(
            page.locator(`text=/${heading}/i`).first()
        ).toBeVisible({ timeout: 8_000 });

        expect(errors).toEqual([]);
    });
}

// ─── Polish character encoding ──────────────────────────────────────

test('Dashboard shows correct Polish characters', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });
    // These were previously broken by mojibake
    const text = await page.textContent('body');
    expect(text).not.toContain('Ä');
    expect(text).not.toContain('Ĺ');
    expect(text).not.toContain('Ã³');
});

test('ActionHistory shows correct Polish characters', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia/i').first()).toBeVisible({ timeout: 8_000 });
    // Wait for content to fully render
    await page.waitForTimeout(1000);
    const text = await page.textContent('body');
    expect(text).not.toContain('Ä');
    expect(text).not.toContain('Ĺ');
    expect(text).not.toContain('Ã³');
});
