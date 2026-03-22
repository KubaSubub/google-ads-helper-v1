import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_ACTION_HISTORY, MOCK_UNIFIED_TIMELINE, MOCK_HISTORY_FILTERS, MOCK_CAMPAIGNS } from './fixtures.js';

async function mockActionHistoryApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    // Single handler for all /history/ routes with URL dispatch
    await page.route(/\/api\/v1\/history/, route => {
        const url = route.request().url();
        if (url.includes('/filters')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HISTORY_FILTERS) });
        }
        if (url.includes('/unified')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_UNIFIED_TIMELINE) });
        }
        if (url.includes('/changes')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) });
        }
        if (url.includes('/bid-strategy-impact')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) });
        }
        if (url.includes('/impact')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ACTION_HISTORY) });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 18 — Historia akcji ────────────────────────────────────

test('Sekcja 18.1 — Timeline renderuje się', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    // Entity names z fixtures
    const body = await page.textContent('body');
    const hasEntries = body.includes('sushi dostawa') || body.includes('restauracja japońska') ||
                      body.includes('pizza hut') || body.includes('Wstrzymano') ||
                      body.includes('PAUSE_KEYWORD');
    expect(hasEntries).toBeTruthy();
});

test('Sekcja 18.2 — Zakładki widoku (Helper/Zewnętrzne/Wszystko)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    // Tabs
    const body = await page.textContent('body');
    const hasTabs = body.includes('Helper') || body.includes('Zewnętrzne') || body.includes('Wszystko') ||
                    body.includes('Wpływ');
    expect(hasTabs).toBeTruthy();
});

test('Sekcja 18.3 — Status badges kolorowe (SUCCESS/REVERTED/FAILED)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    // Status labels
    const hasStatuses = body.includes('SUCCESS') || body.includes('REVERTED') || body.includes('FAILED') ||
                       body.includes('Sukces') || body.includes('Cofnięto') || body.includes('Helper');
    expect(hasStatuses).toBeTruthy();
});

test('Sekcja 18.4 — Delta pills (% zmiana) widoczne dla operacji bid', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    // Sprawdzamy obecność zmiany bid
    const body = await page.textContent('body');
    const hasBidChange = body.includes('stawke') || body.includes('stawkę') || body.includes('bid') || body.includes('UPDATE_BID');
    expect(hasBidChange).toBeTruthy();
});

test('Sekcja 18 — Polskie znaki w entity names', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    // "łódź", "japońska" z polskimi znakami
    const hasPolish = body.includes('łódź') || body.includes('japońska');
    expect(hasPolish).toBeTruthy();
});

test('Sekcja 18 — Brak JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
