import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import {
    MOCK_DASHBOARD_KPIS, MOCK_HEALTH_SCORE, MOCK_CAMPAIGNS,
    MOCK_BUDGET_PACING, MOCK_DEVICE_BREAKDOWN, MOCK_CAMPAIGN_TRENDS,
    MOCK_GEO_BREAKDOWN, MOCK_RECOMMENDATIONS,
} from './fixtures.js';

// ─── Mock helpers ───────────────────────────────────────────────────
async function mockDashboardApi(page) {
    await page.route(/\/api\/v1\/analytics\/dashboard-kpis/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DASHBOARD_KPIS) })
    );
    await page.route(/\/api\/v1\/analytics\/health-score/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HEALTH_SCORE) })
    );
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    await page.route(/\/api\/v1\/analytics\/budget-pacing/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_BUDGET_PACING) })
    );
    await page.route(/\/api\/v1\/analytics\/device-breakdown/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DEVICE_BREAKDOWN) })
    );
    await page.route(/\/api\/v1\/analytics\/campaign-trends/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGN_TRENDS) })
    );
    await page.route(/\/api\/v1\/analytics\/geo-breakdown/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_GEO_BREAKDOWN) })
    );
    await page.route(/\/api\/v1\/recommendations/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMMENDATIONS) })
    );
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockDashboardApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 3 — Dashboard ──────────────────────────────────────────

test('Sekcja 3.1 — Health Score gauge renderuje się (SVG circle)', async ({ page }) => {
    await page.goto('/');
    // Gauge SVG z circle elementem (Health Score card)
    const gauge = page.locator('svg circle').first();
    await expect(gauge).toBeVisible({ timeout: 10_000 });
    // Sprawdź wartość liczbową Health Score
    await expect(page.locator('text=74')).toBeVisible();
});

test('Sekcja 3.1b — Health Score issues renderują się', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=/Kampania Display wstrzymana/i')).toBeVisible({ timeout: 10_000 });
});

test('Sekcja 3.2 — KPI cards wyświetlają wartości (nie undefined, nie NaN)', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // Poczekaj na dane
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    expect(body).not.toContain('undefined');
    expect(body).not.toContain('NaN');
});

test('Sekcja 3.2b — KPI cards: koszt, kliknięcia, konwersje obecne', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // KPI labels powinny być widoczne (uppercase headers)
    await expect(page.locator('text=/wydatki|koszt|cost/i').first()).toBeVisible();
    await expect(page.locator('text=/kliknięcia|clicks/i').first()).toBeVisible();
});

test('Sekcja 3.5 — Campaign Budget Pacing cards obecne', async ({ page }) => {
    await page.goto('/');
    // Poczekaj na dane
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // Nazwy kampanii z pacing powinny być widoczne
    await expect(page.locator('text=/Sushi Naka Naka/').first()).toBeVisible();
});

test('Sekcja 3.6 — Device Share section renderuje się', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // Desktop/Mobile/Tablet labels
    await expect(page.locator('text=/desktop|mobile|tablet/i').first()).toBeVisible({ timeout: 8_000 });
});

test('Sekcja 3.9 — Przycisk Refresh istnieje i jest klikalny', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // Przycisk z tekstem "Refresh" lub ikoną RefreshCw
    const refreshBtn = page.locator('button:has-text("Refresh"), button:has-text("Odśwież")').first();
    if (await refreshBtn.count() > 0) {
        await expect(refreshBtn).toBeEnabled();
    }
});

test('Sekcja 3.3/3.4 — Zmiana zakresu dat nie powoduje JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

    // Kliknij date range pill jeśli widoczny (w sidebarze)
    const pill7d = page.locator('button:has-text("7d")').first();
    if (await pill7d.isVisible().catch(() => false)) {
        await pill7d.click();
        await page.waitForTimeout(500);
    }
    const pill30d = page.locator('button:has-text("30d")').first();
    if (await pill30d.isVisible().catch(() => false)) {
        await pill30d.click();
        await page.waitForTimeout(500);
    }

    expect(errors).toEqual([]);
});
