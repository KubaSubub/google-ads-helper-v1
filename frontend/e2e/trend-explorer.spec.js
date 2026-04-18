import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';

// Minimal trend payload — 14 days so rolling-correlation etc. are "possible"
// but the chart just needs >= 2 points.
// Fabricate dates relative to today so the default 30-day filter always includes them.
function daysAgoIso(n) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - n);
    return d.toISOString().slice(0, 10);
}

function mockTrends(page) {
    const days = [];
    for (let i = 13; i >= 0; i--) {
        days.push({
            date: daysAgoIso(i),
            cost: 100 + (13 - i) * 5,
            clicks: 50 + (13 - i) * 2,
            impressions: 1000 + (13 - i) * 40,
            conversions: 2 + ((13 - i) % 3),
            conversion_value: 400 + (13 - i) * 10,
            ctr: 5.2, cpc: 2.0, cpa: 50, cvr: 4.0, roas: 4.0,
        });
    }
    return page.route(/\/api\/v1\/analytics\/trends(\?|$)/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ period_days: 14, is_mock: false, data: days, totals: { cost: 1400, clicks: 800, conversions: 25 } }),
        })
    );
}

// One helper action + one external change, each on a day that exists in the trend series.
function mockTimeline(page) {
    const dayA = `${daysAgoIso(8)}T10:30:00Z`;
    const dayB = `${daysAgoIso(3)}T14:15:00Z`;
    return page.route(/\/api\/v1\/history\/unified/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                entries: [
                    {
                        timestamp: dayA,
                        operation: 'UPDATE_BID',
                        entity_name: 'keyword: buty sportowe',
                        source: 'helper',
                        campaign_name: 'Demo - Buty',
                        old_value_json: { bid_micros: 450000 },
                        new_value_json: { bid_micros: 620000 },
                    },
                    {
                        timestamp: dayB,
                        operation: 'UPDATE_BUDGET',
                        entity_name: 'campaign: Demo - Buty',
                        source: 'external',
                        campaign_name: 'Demo - Buty',
                        old_value_json: { budget_micros: 50000000 },
                        new_value_json: { budget_micros: 80000000 },
                    },
                ],
            }),
        })
    );
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await mockTrends(page);
    await mockTimeline(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

test('Trend Explorer — fullscreen covers full viewport via portal', async ({ page }) => {
    await page.goto('/dashboard');

    // Scroll the widget into view and find the Rozwiń button inside the card.
    const card = page.locator('[data-trend-explorer-card]').first();
    await expect(card).toBeVisible();
    await card.scrollIntoViewIfNeeded();

    // Not fullscreen yet — overlay should not exist
    await expect(page.locator('[data-trend-explorer-fullscreen]')).toHaveCount(0);

    await card.getByRole('button', { name: /Rozwiń/i }).click();

    // Portal overlay is attached to body and takes the full viewport
    const overlay = page.locator('[data-trend-explorer-fullscreen]');
    await expect(overlay).toBeVisible();
    const box = await overlay.boundingBox();
    const vp = page.viewportSize();
    expect(box.width).toBeGreaterThanOrEqual(vp.width - 2);
    expect(box.height).toBeGreaterThanOrEqual(vp.height - 2);

    // Same header collapses the modal back
    await overlay.getByRole('button', { name: /Zwiń/i }).click();
    await expect(page.locator('[data-trend-explorer-fullscreen]')).toHaveCount(0);
});

test('Trend Explorer — ESC closes fullscreen', async ({ page }) => {
    await page.goto('/dashboard');
    const card = page.locator('[data-trend-explorer-card]').first();
    await card.scrollIntoViewIfNeeded();
    await card.getByRole('button', { name: /Rozwiń/i }).click();
    await expect(page.locator('[data-trend-explorer-fullscreen]')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.locator('[data-trend-explorer-fullscreen]')).toHaveCount(0);
});

test('Trend Explorer — "Ukryj zmiany" toggles action markers off the chart', async ({ page }) => {
    await page.goto('/dashboard');
    const card = page.locator('[data-trend-explorer-card]').first();
    await card.scrollIntoViewIfNeeded();

    // Default state: markers on → "Ukryj zmiany" button is present with our actions-count drawer toggle beside it.
    const hideBtn = card.getByRole('button', { name: 'Ukryj zmiany' });
    await expect(hideBtn).toBeVisible({ timeout: 10000 });

    // Count the g wrappers around event markers that we render on top of each
    // ReferenceLine (each has a <title> describing the date + action count).
    const eventBadgeTitles = card.locator('svg title', { hasText: /kliknij aby otworzyć Action History/i });
    const beforeCount = await eventBadgeTitles.count();
    expect(beforeCount).toBeGreaterThan(0);

    await hideBtn.click();

    // After toggle the markers (and their titles) disappear.
    await expect(card.locator('svg title', { hasText: /kliknij aby otworzyć Action History/i })).toHaveCount(0);
    // Button label flips — confirms state.
    await expect(card.getByRole('button', { name: 'Pokaż zmiany' })).toBeVisible();
});
