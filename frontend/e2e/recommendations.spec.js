import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_RECOMMENDATIONS, MOCK_RECOMMENDATIONS_SUMMARY, MOCK_CAMPAIGNS } from './fixtures.js';

async function mockRecommendationsApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    // Single handler for all /recommendations/ requests with URL-based dispatch
    await page.route(/\/api\/v1\/recommendations/, route => {
        const url = route.request().url();
        if (url.includes('/summary')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMMENDATIONS_SUMMARY) });
        }
        if (route.request().method() === 'GET') {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RECOMMENDATIONS) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockRecommendationsApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 7 — Rekomendacje ───────────────────────────────────────

test('Sekcja 7.1 — Lista rekomendacji renderuje się', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    // Karty rekomendacji — nazwy entity z mock data
    await expect(page.locator('text=/sushi dostawa/i').first()).toBeVisible({ timeout: 5_000 });
});

test('Sekcja 7.2 — Filtr priorytetów (ALL/HIGH/MEDIUM/LOW pills)', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });

    // Priority filter pills
    await expect(page.locator('button:has-text("ALL")').first()).toBeVisible();
    await expect(page.locator('button:has-text("HIGH")').first()).toBeVisible();
    await expect(page.locator('button:has-text("MEDIUM")').first()).toBeVisible();
    await expect(page.locator('button:has-text("LOW")').first()).toBeVisible();

    // Kliknięcie HIGH filtruje
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.locator('button:has-text("HIGH")').first().click();
    await page.waitForTimeout(500);
    expect(errors).toEqual([]);
});

test('Sekcja 7.3 — Karta rekomendacji: priority badge, type pill, outcome badge', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Priority pill (HIGH) — w filter pills i kart
    await expect(page.locator('text="HIGH"').first()).toBeVisible();

    // Type pill — np. "Wstrzymaj słowo" lub "Dodaj wykluczenie"
    const body = await page.textContent('body');
    const hasTypePill = body.includes('Wstrzymaj') || body.includes('Dodaj') || body.includes('Quality');
    expect(hasTypePill).toBeTruthy();
});

test('Sekcja 7.4 — Context outcome badge (ACTION/INSIGHT_ONLY/BLOCKED)', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Summary cards show context outcome counts
    const body = await page.textContent('body');
    const hasOutcomes = body.includes('Action') && body.includes('Blocked');
    expect(hasOutcomes).toBeTruthy();
});

test('Sekcja 7.5 — Disabled Apply button dla INSIGHT_ONLY cards', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);

    // Non-executable cards show "Manual review" with disabled state
    const manualBtn = page.locator('button:has-text("Manual review")').first();
    if (await manualBtn.count() > 0) {
        const isDisabled = await manualBtn.isDisabled();
        expect(isDisabled).toBeTruthy();
    } else {
        // Or check for Apply buttons (executable ones)
        const applyBtn = page.locator('button:has-text("Apply")').first();
        await expect(applyBtn).toBeVisible();
    }
});

test('Sekcja 7.6 — Przycisk Dismiss obecny', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    await expect(page.locator('button:has-text("Dismiss")').first()).toBeVisible({ timeout: 5_000 });
});

test('Sekcja 7.7 — Summary widget z licznikami', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });

    // Summary counters: Total, Executable, High
    await expect(page.locator('text=/Total/i').first()).toBeVisible();
    await expect(page.locator('text=/Executable/i').first()).toBeVisible();

    // Wartość Total = 5
    await expect(page.locator('text="5"').first()).toBeVisible();
});

test('Sekcja 7 — Polskie znaki w entity names', async ({ page }) => {
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    // "łódź" z polskimi znakami — w entity names
    const body = await page.textContent('body');
    const hasPolish = body.includes('łódź') || body.includes('żółć') || body.includes('Główna');
    expect(hasPolish).toBeTruthy();
});

test('Sekcja 7 — Brak JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/recommendations');
    await expect(page.locator('text=/Recommendations/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
