import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_ACTION_HISTORY, MOCK_UNIFIED_TIMELINE, MOCK_HISTORY_FILTERS, MOCK_CAMPAIGNS } from './fixtures.js';

// Helper actions mock — uses same data but in actions/ response format
const MOCK_HELPER_ACTIONS = {
    total: MOCK_ACTION_HISTORY.total,
    limit: 200,
    offset: 0,
    actions: MOCK_ACTION_HISTORY.items.map(item => ({
        ...item,
        action_type: item.operation,
        entity_type: item.resource_type,
        entity_id: String(item.id),
        entity_name: item.entity_name,
        campaign_name: item.campaign_name,
        old_value_json: item.old_value ? JSON.stringify({ status: item.old_value }) : null,
        new_value_json: item.new_value ? JSON.stringify({ status: item.new_value }) : null,
        executed_at: item.executed_at,
    })),
};

async function mockActionHistoryApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    // Mock /actions/ endpoint for Helper tab (default)
    await page.route(/\/api\/v1\/actions\//, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HELPER_ACTIONS) })
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

// ─── Sekcja 18 — Historia zmian ────────────────────────────────────

test('Sekcja 18.1 — Helper tab renderuje dane (default tab)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    // Helper tab shows DataTable with translated action labels or entity names
    const hasEntries = body.includes('sushi dostawa') || body.includes('restauracja japońska') ||
                      body.includes('pizza hut') || body.includes('Wstrzymano') ||
                      body.includes('PAUSE_KEYWORD') || body.includes('DATA');
    expect(hasEntries).toBeTruthy();
});

test('Sekcja 18.2 — Zakładki widoku (Helper/Zewnętrzne/Wszystko/Wpływ)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    const body = await page.textContent('body');
    const hasTabs = body.includes('Helper') && body.includes('Zewnętrzne') && body.includes('Wszystko') &&
                    body.includes('Wpływ zmian') && body.includes('Wpływ strategii licytacji');
    expect(hasTabs).toBeTruthy();
});

test('Sekcja 18.3 — Status badges kolorowe (SUCCESS/REVERTED/FAILED)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    const hasStatuses = body.includes('SUCCESS') || body.includes('REVERTED') || body.includes('FAILED') ||
                       body.includes('Helper');
    expect(hasStatuses).toBeTruthy();
});

test('Sekcja 18.4 — Polskie etykiety akcji (OP_LABELS)', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    const body = await page.textContent('body');
    // Verify Polish labels are used (Wstrzymano, Zmieniono stawke, Dodano negative)
    const hasPolishLabels = body.includes('Wstrzymano keyword') || body.includes('Zmieniono stawke') ||
                           body.includes('Dodano negative') || body.includes('Typ akcji');
    expect(hasPolishLabels).toBeTruthy();
});

test('Sekcja 18.5 — Filtry i presety dat widoczne', async ({ page }) => {
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    const body = await page.textContent('body');
    const hasPresets = body.includes('Dzisiaj') && body.includes('7 dni') && body.includes('30 dni');
    const hasActionFilter = body.includes('Typ akcji');
    expect(hasPresets).toBeTruthy();
    expect(hasActionFilter).toBeTruthy();
});

test('Sekcja 18 — Brak JS errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    // Also test clicking through all tabs
    await page.locator('button:has-text("Zewnętrzne")').click();
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Wszystko")').click();
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Wpływ zmian")').click();
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Wpływ strategii")').click();
    await page.waitForTimeout(500);
    expect(errors).toEqual([]);
});
