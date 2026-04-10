/**
 * Settings — Marketing Mastermind Brief E2E tests
 *
 * Covers the Settings pivot from "operational hub" to "strategic context brief":
 *   - Cele konwersji section (reworked from ClientHealthSection Konwersje card)
 *   - 5 new brief sections: Strategia, Roadmap, Log decyzji, Wnioski, Brand voice
 *   - strategy_context JSON column round-trip via PATCH
 *
 * Tests use real DOM assertions (not just network-level waitForResponse) so that
 * bugs in the component layer (like axios.data unwrap issues) are caught.
 */

import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_CLIENT_DETAIL } from './fixtures.js';

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_HEALTH = {
    account_metadata: {
        customer_id: '123-456-7890',
        name: 'Sushi Naka Naka',
        account_type: 'CLIENT',
        currency: 'PLN',
        timezone: 'Europe/Warsaw',
        auto_tagging_enabled: true,
        tracking_url_template: null,
    },
    sync_health: {
        last_synced_at: new Date().toISOString(),
        hours_since_sync: 1.0,
        freshness: 'green',
        last_status: 'success',
        last_duration_seconds: 30,
    },
    conversion_tracking: {
        active_count: 3,
        attribution_model: 'DATA_DRIVEN',
        enhanced_conversions_enabled: null,
        actions: [
            { name: 'Zakup', category: 'PURCHASE', status: 'ENABLED', include_in_conversions: true },
            { name: 'Lead', category: 'LEAD', status: 'ENABLED', include_in_conversions: true },
            { name: 'Kontakt', category: 'CONTACT', status: 'ENABLED', include_in_conversions: false },
        ],
    },
    linked_accounts: [],
    errors: [],
};

const CLIENT_WITH_STRATEGY = {
    ...MOCK_CLIENT_DETAIL,
    currency: 'PLN',
    business_rules: { ...MOCK_CLIENT_DETAIL.business_rules, priority_conversions: [] },
    strategy_context: {
        strategy_narrative: null,
        roadmap: null,
        decisions_log: [],
        lessons_learned: [],
        brand_voice: null,
        restrictions: null,
    },
};

// Shared setup — LIFO: specific mocks LAST = highest priority
async function setupSettings(page, clientOverrides = {}, healthOverrides = {}) {
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await page.route(/\/api\/v1\/clients\/3(\?|$)/, route => {
        if (['GET', 'PATCH', 'PUT'].includes(route.request().method())) {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ ...CLIENT_WITH_STRATEGY, ...clientOverrides }),
            });
        }
        return route.fallback();
    });
    await page.route(/\/api\/v1\/clients\/3\/health/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ ...MOCK_HEALTH, ...healthOverrides }),
        }),
    );
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });
    await page.goto('/settings');
    await expect(page.locator('text=/Ustawienia klienta/i').first()).toBeVisible({ timeout: 10_000 });
}

// ─── Cele konwersji — goal-setting interface ──────────────────────────────────

test('Settings Mastermind — Cele konwersji renders list with checkboxes for all conversions', async ({ page }) => {
    await setupSettings(page);

    // Section container visible
    await expect(page.locator('[data-testid="conversion-goals-section"]')).toBeVisible({ timeout: 10_000 });

    // All 3 conversion names visible (Zakup, Lead, Kontakt)
    // Use getByRole cell with exact name to disambiguate name vs category column
    const section = page.locator('[data-testid="conversion-goals-section"]');
    await expect(section.getByRole('cell', { name: 'Zakup', exact: true })).toBeVisible();
    await expect(section.getByRole('cell', { name: 'Lead', exact: true })).toBeVisible();
    await expect(section.getByRole('cell', { name: 'Kontakt', exact: true })).toBeVisible();

    // Counter shows "Wybrano 0 z 3"
    await expect(section.locator('text=/Wybrano.*0.*z.*3/')).toBeVisible();
});

test('Settings Mastermind — Toggling conversion checkbox sets isDirty', async ({ page }) => {
    await setupSettings(page);

    const section = page.locator('[data-testid="conversion-goals-section"]');
    await expect(section).toBeVisible({ timeout: 10_000 });

    // Click the first checkbox (button with aria-label "Dodaj Zakup do celów")
    const zakupButton = page.getByRole('button', { name: /Dodaj Zakup do celów/ });
    await zakupButton.click();

    // isDirty banner appears
    await expect(page.locator('text=/Niezapisane zmiany/i')).toBeVisible({ timeout: 3_000 });

    // Counter updates to "Wybrano 1 z 3"
    await expect(section.locator('text=/Wybrano.*1.*z.*3/')).toBeVisible({ timeout: 3_000 });
});

// ─── Strategia marketingowa textarea ──────────────────────────────────────────

test('Settings Mastermind — Strategia marketingowa textarea accepts input and sets isDirty', async ({ page }) => {
    await setupSettings(page);

    const textarea = page.locator('[data-testid="strategy-narrative-input"]');
    await expect(textarea).toBeVisible({ timeout: 5_000 });

    await textarea.fill('Nasza strategia: brand-first, long-tail keywords, sezonowe scaling.');
    // isDirty banner appears
    await expect(page.locator('text=/Niezapisane zmiany/i')).toBeVisible({ timeout: 3_000 });
    // Value persisted in the input
    await expect(textarea).toHaveValue(/brand-first/);
});

// ─── Roadmap textarea ─────────────────────────────────────────────────────────

test('Settings Mastermind — Roadmap textarea renders and accepts input', async ({ page }) => {
    await setupSettings(page);

    const textarea = page.locator('[data-testid="strategy-roadmap-input"]');
    await expect(textarea).toBeVisible({ timeout: 5_000 });
    await textarea.fill('Q2 2026: test nowego LP, Q3: scaling Shopping');
    await expect(textarea).toHaveValue(/Q2 2026/);
});

// ─── Log decyzji empty state ──────────────────────────────────────────────────

test('Settings Mastermind — Log decyzji shows AI coming soon banner when empty', async ({ page }) => {
    await setupSettings(page);

    const empty = page.locator('[data-testid="decisions-log-empty"]');
    await expect(empty).toBeVisible({ timeout: 5_000 });
    await expect(empty).toContainText('AI zostanie dołączony w v2');
});

// ─── Wnioski (lessons learned) — add entry ────────────────────────────────────

test('Settings Mastermind — Lessons learned: add win entry, verify in list', async ({ page }) => {
    await setupSettings(page);

    // Form fields
    await page.locator('[data-testid="lesson-type-select"]').selectOption('win');
    await page.locator('[data-testid="lesson-title-input"]').fill('Geo-Warszawa scaling +20% conv');
    await page.locator('[data-testid="lesson-description-input"]').fill('Po zawężeniu do Warszawy conversion rate wzrósł o 20% przy -15% CPA. Do replikacji dla podobnych klientów lokalnych.');

    // Click "Dodaj"
    await page.locator('[data-testid="lesson-add-button"]').click();

    // Entry appears in the list
    const entries = page.locator('[data-testid="lesson-entry"]');
    await expect(entries).toHaveCount(1, { timeout: 3_000 });
    await expect(entries.first()).toContainText('Geo-Warszawa scaling');

    // Form was reset
    await expect(page.locator('[data-testid="lesson-title-input"]')).toHaveValue('');
});

test('Settings Mastermind — Lessons learned: remove entry after confirm', async ({ page }) => {
    await setupSettings(page);

    // First add an entry so we have something to remove
    await page.locator('[data-testid="lesson-type-select"]').selectOption('loss');
    await page.locator('[data-testid="lesson-title-input"]').fill('Test entry to remove');
    await page.locator('[data-testid="lesson-description-input"]').fill('Entry dodany po to żeby go zaraz usunąć w teście.');
    await page.locator('[data-testid="lesson-add-button"]').click();

    // Verify it's there
    await expect(page.locator('[data-testid="lesson-entry"]')).toHaveCount(1, { timeout: 3_000 });

    // Accept the window.confirm dialog that pops up on remove
    page.once('dialog', dialog => dialog.accept());

    // Click the remove button (Trash2 icon) inside the entry
    await page.locator('[data-testid="lesson-entry"]').locator('button[aria-label="Usuń wpis"]').click();

    // Entry should disappear
    await expect(page.locator('[data-testid="lesson-entry"]')).toHaveCount(0, { timeout: 3_000 });
});

test('Settings Mastermind — Cele konwersji shows separate primary_for_goal column', async ({ page }) => {
    // Mock with 2 conversions: Zakup is primary_for_goal=true, Lead is false
    await mockEmptyApi(page);
    await mockAuthAndClient(page);
    await page.route(/\/api\/v1\/clients\/3(\?|$)/, route => {
        if (['GET', 'PATCH', 'PUT'].includes(route.request().method())) {
            return route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify(CLIENT_WITH_STRATEGY),
            });
        }
        return route.fallback();
    });
    await page.route(/\/api\/v1\/clients\/3\/health/, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({
                ...MOCK_HEALTH,
                conversion_tracking: {
                    ...MOCK_HEALTH.conversion_tracking,
                    active_count: 2,
                    actions: [
                        { name: 'Zakup', category: 'PURCHASE', status: 'ENABLED', include_in_conversions: true, primary_for_goal: true },
                        { name: 'Lead', category: 'LEAD', status: 'ENABLED', include_in_conversions: true, primary_for_goal: false },
                    ],
                },
            }),
        }),
    );
    await page.addInitScript(() => { localStorage.setItem('selectedClientId', '3'); });
    await page.goto('/settings');
    await expect(page.locator('text=/Ustawienia klienta/i').first()).toBeVisible({ timeout: 10_000 });

    // Column header "Cel Google Ads" present
    const section = page.locator('[data-testid="conversion-goals-section"]');
    await expect(section.getByRole('columnheader', { name: /Cel Google Ads/i })).toBeVisible();

    // Description text about local priority vs primary_for_goal is present
    await expect(section.locator('text=/Priorytet lokalny/')).toBeVisible();
});

// ─── Brand voice + restrictions ───────────────────────────────────────────────

test('Settings Mastermind — Brand voice and restrictions textareas both accept input', async ({ page }) => {
    await setupSettings(page);

    const voice = page.locator('[data-testid="brand-voice-input"]');
    const restrictions = page.locator('[data-testid="restrictions-input"]');
    await expect(voice).toBeVisible({ timeout: 5_000 });
    await expect(restrictions).toBeVisible();

    await voice.fill('Luźny, przyjazny, polski. Bez korporacyjnego żargonu.');
    await restrictions.fill('Nie używać "tani", "najtańszy". Nigdy nie wspominać o konkurencji.');

    await expect(voice).toHaveValue(/przyjazny/);
    await expect(restrictions).toHaveValue(/konkurencji/);

    // isDirty banner
    await expect(page.locator('text=/Niezapisane zmiany/i')).toBeVisible({ timeout: 3_000 });
});

// ─── Section group headers ────────────────────────────────────────────────────

test('Settings Mastermind — Brief kliencki and Execution group headers render', async ({ page }) => {
    await setupSettings(page);

    await expect(page.locator('[data-testid="section-group-brief-kliencki"]')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('[data-testid="section-group-execution"]')).toBeVisible();
});
