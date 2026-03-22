import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_DAILY_AUDIT } from './fixtures.js';

async function mockDailyAuditApi(page) {
    await page.route(/\/api\/v1\/daily-audit/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DAILY_AUDIT) })
    );
    await page.route(/\/api\/v1\/recommendations\/bulk-apply/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, applied: 0, message: 'Dry run' }) })
    );
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockDailyAuditApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 8 — Codzienny Audyt ────────────────────────────────────

test('Sekcja 8.1 — Health Score gauge obecny', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Mini gauge SVG circle
    const gauge = page.locator('svg circle').first();
    await expect(gauge).toBeVisible();
    // Wartość score
    await expect(page.locator('text="74"').first()).toBeVisible();
});

test('Sekcja 8.2 — KPI chips (Wydatki/Kliknięcia/Konwersje) obecne', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // KPI chip labels (component uses ASCII Polish: Wydatki, Klikniecia, Konwersje)
    await expect(page.locator('text=/wydatki/i').first()).toBeVisible();
    await expect(page.locator('text=/klikni/i').first()).toBeVisible();
    await expect(page.locator('text=/konwersje/i').first()).toBeVisible();
});

test('Sekcja 8.2b — KPI chips wyświetlają wartości liczbowe', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    expect(body).not.toContain('undefined');
    expect(body).not.toContain('NaN');
    // Wartości KPI powinny być liczbowe (today_clicks = 765, formatted as "765")
    expect(body).toMatch(/765|110/); // clicks or spend value
});

test('Sekcja 8.3 — Sekcja anomalii', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Anomalia 24h — component displays alert_type.replace(/_/g, ' ') = "COST SPIKE"
    await expect(page.locator('text=/COST SPIKE/').first()).toBeVisible();
});

test('Sekcja 8.4 — Disapproved ads sekcja', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Disapproved ad section — component shows "Odrzucona reklama" label
    await expect(page.locator('text=/Odrzucona reklama/').first()).toBeVisible();
});

test('Sekcja 8.5 — Search terms needing action', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Search terms do akcji
    await expect(page.locator('text=/jak zrobić sushi w domu/').first()).toBeVisible();
});

test('Sekcja 8.6 — Quick Optimization Scripts buttons obecne', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Quick script labels
    const body = await page.textContent('body');
    const hasScripts = body.includes('Clean') || body.includes('Pause') || body.includes('Boost') ||
                       body.includes('Wyczyść') || body.includes('Wstrzymaj') || body.includes('do wykonania');
    expect(hasScripts).toBeTruthy();
});

test('Sekcja 8.7 — Budget Pacing table z progress bars', async ({ page }) => {
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    // Budget pacing — kampanie z pacing
    await expect(page.locator('text=/Sushi Naka Naka/').first()).toBeVisible();
});

test('Sekcja 8 — Brak JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/daily-audit');
    await expect(page.locator('text=/Codzienny Audyt/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
