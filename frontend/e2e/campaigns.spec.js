import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_CAMPAIGNS, MOCK_BUDGET_PACING, MOCK_DEVICE_BREAKDOWN, MOCK_GEO_BREAKDOWN } from './fixtures.js';

async function mockCampaignsApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    await page.route(/\/api\/v1\/analytics\/budget-pacing/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_BUDGET_PACING) })
    );
    await page.route(/\/api\/v1\/analytics\/device-breakdown/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DEVICE_BREAKDOWN) })
    );
    await page.route(/\/api\/v1\/analytics\/geo-breakdown/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_GEO_BREAKDOWN) })
    );
    await page.route(/\/api\/v1\/analytics\/impression-share/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    );
    await page.route(/\/api\/v1\/history\/unified/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
    );
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockCampaignsApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 4 — Kampanie ───────────────────────────────────────────

test('Sekcja 4.1 — Tabela kampanii renderuje się z wierszami', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    // Nazwy kampanii widoczne w tabeli
    await expect(page.locator('text=/Sushi Naka Naka/').first()).toBeVisible();
    await expect(page.locator('text=/PMax/').first()).toBeVisible();
});

test('Sekcja 4.2 — Status badges (ENABLED/PAUSED) widoczne', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    // Status labels w tabeli
    await expect(page.locator('text=/Aktywna/i').first()).toBeVisible();
    await expect(page.locator('text=/Wstrzymana/i').first()).toBeVisible();
});

test('Sekcja 4.3 — Campaign type badges widoczne', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    // Type badges: Search, PMax, Display
    await expect(page.locator('text=/Search/').first()).toBeVisible();
    await expect(page.locator('text=/PMax/').first()).toBeVisible();
});

test('Sekcja 4.1b — Kolumny tabeli obecne', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    // Nagłówki tabeli (uppercase)
    const body = await page.textContent('body');
    // Sprawdź że kluczowe nagłówki są obecne
    expect(body).toMatch(/nazwa|name/i);
});

test('Sekcja 4.8 — KPI row wyświetla metryki', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    // Brak undefined/NaN w metrykach
    expect(body).not.toContain('undefined');
    expect(body).not.toContain('NaN');
});

test('Sekcja 4 — Polskie znaki w nazwach kampanii', async ({ page }) => {
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    // Nazwa z polskim znakiem "żółć"
    await expect(page.locator('text=/żółć/').first()).toBeVisible();
});

test('Sekcja 4 — Brak JS errors na stronie kampanii', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/campaigns');
    await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
