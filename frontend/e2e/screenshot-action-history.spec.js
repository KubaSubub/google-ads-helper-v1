import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_ACTION_HISTORY, MOCK_UNIFIED_TIMELINE, MOCK_HISTORY_FILTERS, MOCK_CAMPAIGNS } from './fixtures.js';

async function mockActionHistoryApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    await page.route(/\/api\/v1\/actions\//, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ACTION_HISTORY) })
    );
    await page.route(/\/api\/v1\/history/, route => {
        const url = route.request().url();
        if (url.includes('/filters')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HISTORY_FILTERS) });
        }
        if (url.includes('/unified')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_UNIFIED_TIMELINE) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) });
    });
    await page.route(/\/api\/v1\/analytics\/change-impact/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
            items: [{
                action_log_id: 801, action_type: 'PAUSE_KEYWORD', entity_name: 'sushi dostawa łódź',
                executed_at: '2026-03-22T10:30:00', impact: 'POSITIVE',
                delta: { cost_usd_pct: -15.2, conversions_pct: 2.1, cpa_usd_pct: -12.5, ctr_pct: 3.8, roas_pct: 8.4 }
            }],
            summary: { positive: 1, neutral: 0, negative: 0 }
        }) })
    );
    await page.route(/\/api\/v1\/analytics\/bid-strategy-impact/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
            items: [{
                campaign_id: 101, campaign_name: 'Sushi Naka Naka — Brandówka',
                change_date: '2026-03-15', old_strategy: 'MANUAL_CPC', new_strategy: 'TARGET_CPA',
                impact: 'POSITIVE', delta: { conversions_pct: 18.5, cpa_usd_pct: -22.0, roas_pct: 15.3 }
            }]
        }) })
    );
}

// Separate test per tab to isolate failures

test('Screenshot Tab 1 - Wszystko (default)', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });

    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-screenshots/ah-wszystko.png' });
    if (errors.length) console.log('ERRORS tab1:', errors);
});

test('Screenshot Tab 2 - Helper', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });

    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);

    // Click Helper tab using text locator
    await page.locator('button:has-text("Helper")').first().click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-screenshots/ah-helper.png' });
    if (errors.length) console.log('ERRORS tab2:', errors);
});

test('Screenshot Tab 3 - Zewnętrzne', async ({ page }) => {
    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });

    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    await page.locator('button:has-text("Zewnętrzne")').click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-screenshots/ah-zewnetrzne.png' });
});

test('Screenshot Tab 4 - Wpływ zmian', async ({ page }) => {
    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });

    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    await page.locator('button:has-text("Wpływ zmian")').click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-screenshots/ah-wplyw-zmian.png' });
});

test('Screenshot Tab 5 - Wpływ strategii', async ({ page }) => {
    await mockEmptyApi(page);
    await mockActionHistoryApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });

    await page.goto('/action-history');
    await expect(page.locator('text=/Historia zmian/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    await page.locator('button:has-text("Wpływ strategii")').click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-screenshots/ah-wplyw-strategii.png' });
});
