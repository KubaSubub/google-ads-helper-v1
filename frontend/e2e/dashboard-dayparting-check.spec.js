// Visual check for the three dashboard dayparting widgets (DayOfWeek, Hourly, Heatmap).
// Two scenarios: happy path (data) + empty state (no hour_of_day).
import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';

const DOW_FIXTURE = {
    currency: 'PLN', period_days: 30, campaign_type_used: 'ALL',
    days: Array.from({ length: 7 }, (_, i) => ({
        day_of_week: i,
        day_name: ['Pn','Wt','Sr','Cz','Pt','Sb','Nd'][i],
        clicks: 300 + i * 40, conversions: 10 + i * 2,
        cpa: 25 - i, roas: 3 + i * 0.3, cvr: 4, cpc: 1.2,
        aov: 95, conversion_value_amount: 1500 + i * 200,
        observations: 4,
    })),
};

const HOURLY_FIXTURE_FULL = {
    currency: 'PLN', campaign_type_used: 'ALL',
    hours: Array.from({ length: 24 }, (_, h) => ({
        hour: h, hour_label: `${h}:00`,
        clicks: Math.max(2, Math.round(50 + 40 * Math.sin((h - 6) / 24 * Math.PI * 2))),
        conversions: Math.max(0, Math.round((2 + 3 * Math.sin((h - 10) / 24 * Math.PI * 2)) * 10) / 10),
        cost_usd: 25, cpa: 15, roas: 3.5,
    })),
};

const HOURLY_FIXTURE_EMPTY = {
    currency: 'PLN', campaign_type_used: 'ALL',
    hours: Array.from({ length: 24 }, (_, h) => ({
        hour: h, hour_label: `${h}:00`,
        clicks: 0, conversions: 0, cost_usd: 0, cpa: 0, roas: 0,
    })),
};

const HEATMAP_CELLS_FULL = [];
for (let dow = 0; dow < 7; dow++) for (let h = 0; h < 24; h++) {
    HEATMAP_CELLS_FULL.push({
        day_of_week: dow, hour: h,
        cost: 10 + dow, clicks: 40, conversions: 1.5,
        cpa: 15, roas: 3, cvr: 4,
    });
}
const HEATMAP_FIXTURE_FULL = { currency: 'PLN', window_days: 30, overall_cpa: 15, cells: HEATMAP_CELLS_FULL };

const HEATMAP_CELLS_EMPTY = [];
for (let dow = 0; dow < 7; dow++) for (let h = 0; h < 24; h++) {
    HEATMAP_CELLS_EMPTY.push({
        day_of_week: dow, hour: h,
        cost: null, clicks: 0, conversions: 0,
        cpa: null, roas: 0, cvr: 0,
    });
}
const HEATMAP_FIXTURE_EMPTY = { currency: 'PLN', window_days: 30, overall_cpa: null, cells: HEATMAP_CELLS_EMPTY };

async function setupCommon(page) {
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await page.route(/\/api\/v1\/analytics\/dayparting(\?|$)/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DOW_FIXTURE) })
    );
    await page.route(/\/api\/v1\/analytics\/dayparting-dow-suggestions/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ suggestions: [] }) })
    );
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
}

test('Dashboard dayparting — happy path (all 3 render)', async ({ page }) => {
    await setupCommon(page);
    await page.route(/\/api\/v1\/analytics\/hourly-dayparting/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HOURLY_FIXTURE_FULL) })
    );
    await page.route(/\/api\/v1\/analytics\/dayparting-heatmap/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HEATMAP_FIXTURE_FULL) })
    );

    const jsErrors = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    await page.goto('/dashboard');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'e2e-screenshots/dayparting-happy.png', fullPage: true });

    await expect(page.locator('text=/Dzien tygodnia/i').first()).toBeVisible();
    await expect(page.locator('text=/Godziny \\(0-23\\)/i').first()).toBeVisible();
    await expect(page.locator('text=/Heatmapa 7/i').first()).toBeVisible();
    expect(jsErrors).toEqual([]);
});

test('Dashboard dayparting — empty hour data (explicit empty state, not null)', async ({ page }) => {
    await setupCommon(page);
    await page.route(/\/api\/v1\/analytics\/hourly-dayparting/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HOURLY_FIXTURE_EMPTY) })
    );
    await page.route(/\/api\/v1\/analytics\/dayparting-heatmap/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HEATMAP_FIXTURE_EMPTY) })
    );

    await page.goto('/dashboard');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'e2e-screenshots/dayparting-empty.png', fullPage: true });

    // Both widgets should render their header + empty-state message, not return null
    await expect(page.locator('text=/Godziny \\(0-23\\)/i').first()).toBeVisible();
    await expect(page.locator('text=/Heatmapa 7/i').first()).toBeVisible();
    await expect(page.locator('text=/Brak danych godzinowych/i').first()).toBeVisible();
});
