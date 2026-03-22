import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_ALERTS, MOCK_ZSCORE_ANOMALIES } from './fixtures.js';

async function mockAlertsApi(page) {
    // Business alerts
    await page.route(/\/api\/v1\/analytics\/anomalies/, route => {
        const url = route.request().url();
        // Z-score anomalies endpoint (has metric param)
        if (url.includes('metric=') || url.includes('threshold=')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ZSCORE_ANOMALIES) });
        }
        // Business alerts (has status param)
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTS) });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockAlertsApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 14 — Alerty / Monitoring ───────────────────────────────

test('Sekcja 14.1 — Zakładki "Alerty" / "Anomalie (z-score)" obecne', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    // Main tabs
    await expect(page.locator('button:has-text("Alerty")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Anomalie")').first()).toBeVisible();
});

test('Sekcja 14.2 — Sub-taby: Nierozwiązane / Rozwiązane', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    // Sub-tabs w zakładce Alerty
    await expect(page.locator('button:has-text("Nierozwiązane")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Rozwiązane")').first()).toBeVisible();
});

test('Sekcja 14.3 — Alert cards z severity badges', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    // Alert severity labels
    await expect(page.locator('text=/Wysoki/').first()).toBeVisible();
    // Alert title
    await expect(page.locator('text=/Skok kosztów/').first()).toBeVisible();
});

test('Sekcja 14.4 — Przycisk "Rozwiąż" przy alercie', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('button:has-text("Rozwiąż")').first()).toBeVisible();
});

test('Sekcja 14.5 — Anomalie tab: metric pills', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    // Przełącz na Anomalie tab
    await page.locator('button:has-text("Anomalie")').first().click();
    await page.waitForTimeout(500);

    // Metric pills: Koszt, Kliknięcia, Wyświetlenia, Konwersje, CTR
    await expect(page.locator('button:has-text("Koszt")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Kliknięcia")').first()).toBeVisible();
    await expect(page.locator('button:has-text("CTR")').first()).toBeVisible();
});

test('Sekcja 14.6 — Anomalie tab: threshold selector (1.5σ/2.0σ/2.5σ/3.0σ)', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('button:has-text("Anomalie")').first().click();
    await page.waitForTimeout(500);

    // Threshold pills
    await expect(page.locator('button:has-text("1.5σ")').first()).toBeVisible();
    await expect(page.locator('button:has-text("2σ"), button:has-text("2.0σ")').first()).toBeVisible();
    await expect(page.locator('button:has-text("3σ"), button:has-text("3.0σ")').first()).toBeVisible();
});

test('Sekcja 14.7 — Anomalie tab: period selector (30d/60d/90d)', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('button:has-text("Anomalie")').first().click();
    await page.waitForTimeout(500);

    // Period pills
    await expect(page.locator('button:has-text("30d")').first()).toBeVisible();
    await expect(page.locator('button:has-text("60d")').first()).toBeVisible();
    await expect(page.locator('button:has-text("90d")').first()).toBeVisible();
});

test('Sekcja 14.8 — Anomalie tab: stats cards (Anomalie/Średnia/Odch. std.)', async ({ page }) => {
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    await page.locator('button:has-text("Anomalie")').first().click();
    await page.waitForTimeout(1500);

    // Stats cards
    await expect(page.locator('text=/Anomalie/').nth(1)).toBeVisible();
    await expect(page.locator('text=/Średnia/').first()).toBeVisible();
    await expect(page.locator('text=/Odch. std./').first()).toBeVisible();
});

test('Sekcja 14 — Brak JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/alerts');
    await expect(page.locator('text=/Monitoring/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
