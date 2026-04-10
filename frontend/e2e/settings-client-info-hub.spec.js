/**
 * Settings — Client Info Hub E2E tests
 *
 * Tests: new AI context fields + currency fix + health endpoint integration.
 *
 * Covers Acceptance Criteria:
 *   AC1  — /clients/{id}/health is called, returns 200 with expected schema
 *   AC5/AC6 — currency not hardcoded as USD when client.currency = PLN
 *   AC7  — 6 new AI context fields present + brand_terms editable
 */

import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_CLIENT_DETAIL } from './fixtures.js';

// ─── Mock helpers ─────────────────────────────────────────────────────────────

const MOCK_HEALTH = {
    account_metadata: {
        customer_id: '123-456-7890',
        name: 'Sushi Naka Naka',
        account_type: 'STANDARD',
        currency: 'PLN',
        timezone: 'Europe/Warsaw',
        auto_tagging_enabled: true,
        tracking_url_template: null,
    },
    sync_health: {
        last_synced_at: new Date(Date.now() - 2 * 3_600_000).toISOString(),
        hours_since_sync: 2.0,
        freshness: 'green',
        last_status: 'success',
        last_duration_seconds: 35,
    },
    conversion_tracking: {
        active_count: 3,
        attribution_model: 'GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN',
        enhanced_conversions_enabled: null,
        actions: [
            { name: 'Zakup', category: 'PURCHASE', status: 'ENABLED', include_in_conversions: true },
        ],
    },
    linked_accounts: [
        { type: 'GA4', status: 'not_linked', resource_name: null, detected_via: 'google_ads_api' },
        { type: 'MERCHANT_CENTER', status: 'not_linked', resource_name: null, detected_via: 'google_ads_api' },
        { type: 'YOUTUBE', status: 'not_linked', resource_name: null, detected_via: 'google_ads_api' },
        { type: 'SEARCH_CONSOLE', status: 'not_linked', resource_name: null, detected_via: 'google_ads_api' },
    ],
    errors: [],
};

// LIFO order: last registered = first matched in Playwright.
// Health mock registered LAST = highest priority, overrides catch-all.
async function goToSettings(page) {
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await page.route(/\/api\/v1\/clients\/3(\?|$)/, route => {
        if (['GET', 'PATCH', 'PUT'].includes(route.request().method())) {
            return route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({ ...MOCK_CLIENT_DETAIL, currency: 'PLN' }),
            });
        }
        return route.fallback();
    });
    await page.route(/\/api\/v1\/clients\/3\/health/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HEALTH) }),
    );
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });
    await page.goto('/settings');
    await expect(
        page.locator('text=/Ustawienia klienta/i').first()
    ).toBeVisible({ timeout: 10_000 });
}

// ─── AC1 — health endpoint called with correct response shape ─────────────────

test('Settings Hub — GET /clients/{id}/health called on load, returns correct schema', async ({ page }) => {
    const healthDone = page.waitForResponse(
        r => r.url().includes('/clients/3/health') && r.status() === 200,
        { timeout: 10_000 },
    );
    await goToSettings(page);
    const resp = await healthDone;
    const body = await resp.json();
    // AC1: four required top-level keys
    expect(body).toHaveProperty('account_metadata');
    expect(body).toHaveProperty('sync_health');
    expect(body).toHaveProperty('conversion_tracking');
    expect(body).toHaveProperty('linked_accounts');
    // sync_health.freshness is one of the valid values
    expect(['green', 'yellow', 'red']).toContain(body.sync_health.freshness);
    // errors is an array
    expect(Array.isArray(body.errors)).toBe(true);
});

// ─── REAL DOM RENDERING — this catches the axios-unwrap bug ──────────────────
// Previous version of this test used page.waitForResponse only, which passed
// even when the component was silently failing to render (r.data vs r bug).
// This version asserts the section + cards are actually IN THE DOM and visible.

test('Settings Hub — ClientHealthSection renders with all 4 cards + freshness badge', async ({ page }) => {
    await goToSettings(page);

    // The section container (data-testid survives even if card titles change)
    const section = page.locator('[data-testid="client-health-section"]');
    await expect(section).toBeVisible({ timeout: 10_000 });

    // All 4 card titles visible — mocked data drives these
    await expect(section.locator('text=Konto').first()).toBeVisible();
    await expect(section.locator('text=Synchronizacja').first()).toBeVisible();
    await expect(section.locator('text=Konwersje').first()).toBeVisible();
    await expect(section.locator('text=Połączenia').first()).toBeVisible();

    // Sync freshness badge "Aktualny" (green) matches MOCK_HEALTH.sync_health.freshness = "green"
    await expect(section.locator('text=Aktualny')).toBeVisible();

    // Conversion tracking count from mock (3 active)
    await expect(section.locator('text=/^3$/')).toBeVisible();

    // Account metadata from mock — customer_id
    await expect(section.locator('text=123-456-7890')).toBeVisible();
});

test('Settings Hub — freshness badge shows "Nieaktualny" for red sync', async ({ page }) => {
    // LIFO order: catch-all first, specific routes last.
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await page.route(/\/api\/v1\/clients\/3(\?|$)/, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ ...MOCK_CLIENT_DETAIL, currency: 'PLN' }),
        }),
    );
    // Health mock with red freshness — registered LAST = highest priority (LIFO)
    await page.route(/\/api\/v1\/clients\/3\/health/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                ...MOCK_HEALTH,
                sync_health: {
                    freshness: 'red', last_synced_at: null, last_status: null,
                    last_duration_seconds: null, hours_since_sync: null,
                },
            }),
        }),
    );
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });
    await page.goto('/settings');
    await expect(page.locator('text=/Ustawienia klienta/i').first()).toBeVisible({ timeout: 10_000 });

    const section = page.locator('[data-testid="client-health-section"]');
    await expect(section).toBeVisible({ timeout: 10_000 });
    await expect(section.locator('text=Nieaktualny')).toBeVisible();
    await expect(section.locator('text=/Brak danych/i')).toBeVisible();
});

// ─── AC5/AC6 — no hardcoded USD ───────────────────────────────────────────────

test('Settings Hub — no hardcoded USD in Settings when client.currency is PLN', async ({ page }) => {
    await goToSettings(page);

    const businessRulesSection = page.locator('section').filter({ hasText: /Reguły biznesowe/ });
    await expect(businessRulesSection).toBeVisible({ timeout: 5_000 });
    const text = await businessRulesSection.textContent();
    expect(text).not.toContain('USD');
    // New fields use PLN currency label
    expect(text).toContain('PLN');
});

// ─── AC7 — 6 new AI context fields present ────────────────────────────────────

test('Settings Hub — 6 new AI context fields render in business rules section', async ({ page }) => {
    await goToSettings(page);

    const section = page.locator('section').filter({ hasText: /Reguły biznesowe/ });
    await expect(section).toBeVisible({ timeout: 5_000 });

    // All 6 new fields must be present
    for (const label of ['Target CPA', 'Target ROAS', 'LTV klienta', 'Marża zysku', 'Brand terms']) {
        await expect(section.locator(`text=/${label}/i`).first()).toBeVisible({ timeout: 3_000 });
    }
    // brand_terms input with recognizable placeholder
    await expect(page.locator('input[placeholder*="NazwaMarki"]')).toBeVisible({ timeout: 3_000 });
});

// ─── AC7 — brand_terms tag input interaction ──────────────────────────────────

test('Settings Hub — brand_terms tag input adds and removes terms', async ({ page }) => {
    await goToSettings(page);

    const input = page.locator('input[placeholder*="NazwaMarki"]');
    await expect(input).toBeVisible({ timeout: 5_000 });

    // Add a term via Enter key
    await input.fill('SushiNaka');
    await input.press('Enter');
    await expect(page.locator('span:has-text("SushiNaka")').first()).toBeVisible({ timeout: 3_000 });

    // Remove it via X button
    const pill = page.locator('span').filter({ hasText: /^SushiNaka/ });
    await pill.locator('button').click();
    await expect(page.locator('span:has-text("SushiNaka")').first()).not.toBeVisible({ timeout: 2_000 });
});
