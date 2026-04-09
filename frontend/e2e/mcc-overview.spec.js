import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';

// ─── MCC Overview fixture data ──────────────────────────────────────

const MOCK_MCC_OVERVIEW = {
    synced_at: '2026-04-09T12:00:00+00:00',
    date_from: '2026-03-10',
    date_to: '2026-04-09',
    accounts: [
        {
            client_id: 3,
            client_name: 'Sushi Naka Naka',
            google_customer_id: '174-803-8525',
            spend: 2388.12,
            spend_change_pct: 1.4,
            clicks: 1420,
            impressions: 27500,
            conversions: 254.2,
            conversion_value: 24500,
            ctr_pct: 5.16,
            avg_cpc: 1.68,
            cpa: 9.39,
            roas_pct: 1904,
            conversion_rate_pct: 17.9,
            search_impression_share_pct: 96.2,
            total_changes: 59,
            external_changes: 5,
            change_breakdown: { create: 57, update: 2 },
            google_recs_pending: 0,
            last_synced_at: '2026-04-09T08:00:00+00:00',
            unresolved_alerts: 0,
            alert_details: [],
            new_access_emails: ['nowy@example.com'],
            pacing: {
                status: 'on_track',
                pacing_pct: 86,
                days_elapsed: 9,
                days_in_month: 30,
                month_progress_pct: 30,
            },
        },
        {
            client_id: 4,
            client_name: 'Ohtime AN',
            google_customer_id: '201-583-7515',
            spend: 77.51,
            spend_change_pct: null,
            clicks: 45,
            impressions: 985,
            conversions: 1,
            conversion_value: 77.51,
            ctr_pct: 4.57,
            avg_cpc: 1.72,
            cpa: 77.51,
            roas_pct: 77,
            conversion_rate_pct: 2.2,
            search_impression_share_pct: null,
            total_changes: 95,
            external_changes: 95,
            change_breakdown: { create: 94, update: 1 },
            google_recs_pending: 0,
            last_synced_at: '2026-04-09T08:00:00+00:00',
            unresolved_alerts: 0,
            alert_details: [],
            new_access_emails: [],
            pacing: {
                status: 'overspend',
                pacing_pct: 86,
                days_elapsed: 9,
                days_in_month: 30,
                month_progress_pct: 30,
            },
        },
        {
            client_id: 2,
            client_name: 'Klimfix',
            google_customer_id: '485-292-2891',
            spend: 0,
            spend_change_pct: null,
            clicks: 0,
            impressions: 0,
            conversions: 0,
            conversion_value: 0,
            ctr_pct: null,
            avg_cpc: null,
            cpa: null,
            roas_pct: null,
            conversion_rate_pct: null,
            search_impression_share_pct: null,
            total_changes: 0,
            external_changes: 0,
            change_breakdown: {},
            google_recs_pending: 0,
            last_synced_at: '2026-04-09T08:00:00+00:00',
            unresolved_alerts: 0,
            alert_details: [],
            new_access_emails: [],
            pacing: { status: 'no_data' },
        },
    ],
};

const MOCK_SHARED_LISTS = {
    keyword_lists: [
        { id: 1, name: 'Wulgaryzmy i spam', description: 'Lista globalnych wykluczeń', source: 'MCC_SYNC', status: 'ENABLED', item_count: 10, ownership_level: 'mcc' },
        { id: 2, name: 'Nieistotne intencje', description: null, source: 'MCC_SYNC', status: 'ENABLED', item_count: 6, ownership_level: 'mcc' },
    ],
    placement_lists: [
        { id: 1, name: 'Spammerskie strony', description: 'Strony niskiej jakości', source: 'MCC_SYNC', status: 'ENABLED', item_count: 12, ownership_level: 'mcc' },
    ],
};

const MOCK_KEYWORD_ITEMS = {
    list_id: 1,
    list_type: 'keyword',
    items: [
        { id: 1, text: 'darmowe', match_type: 'PHRASE' },
        { id: 2, text: 'za darmo', match_type: 'PHRASE' },
        { id: 3, text: 'crack', match_type: 'EXACT' },
    ],
};

const MOCK_PLACEMENT_ITEMS = {
    list_id: 1,
    list_type: 'placement',
    items: [
        { id: 1, url: 'spamsite.com', placement_type: 'WEBSITE' },
        { id: 2, url: 'youtube.com/channel/spam123', placement_type: 'YOUTUBE_CHANNEL' },
    ],
};

const MOCK_BILLING = { status: 'ok', reason: null };

// ─── Mock setup ─────────────────────────────────────────────────────

async function mockMccApi(page) {
    await page.route(/\/api\/v1\/mcc\/overview/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_MCC_OVERVIEW) })
    );
    await page.route(/\/api\/v1\/mcc\/billing-status/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_BILLING) })
    );
    await page.route(/\/api\/v1\/mcc\/negative-keyword-lists/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    );
    // Register shared-lists catch-all FIRST (Playwright: last match wins)
    await page.route(/\/api\/v1\/mcc\/shared-lists(?!\/)/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SHARED_LISTS) })
    );
    // Then register drill-down LAST so it takes priority
    await page.route(/\/api\/v1\/mcc\/shared-lists\/\d+\/items/, route => {
        const url = route.request().url();
        const isPlacement = url.includes('list_type=placement');
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify(isPlacement ? MOCK_PLACEMENT_ITEMS : MOCK_KEYWORD_ITEMS),
        });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockMccApi(page);
    await mockAuthAndClient(page);
});

// ─── 1. Page structure ──────────────────────────────────────────────

test('MCC Overview — page title and subtitle render', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text=Przegląd MCC')).toBeVisible();
    await expect(page.locator('text=2026-03-10')).toBeVisible();
    await expect(page.locator('text=2026-04-09')).toBeVisible();
});

test('MCC Overview — KPI strip renders all values', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    // Wydatki (total = 2388.12 + 77.51 + 0 = 2465.63)
    await expect(page.locator('text=Wydatki').first()).toBeVisible();
    await expect(page.locator('text=/2[\\s.]?465,63/')).toBeVisible();

    // Konwersje (total = 254.2 + 1 + 0 = 255.2)
    await expect(page.locator('text=Konwersje').first()).toBeVisible();
    await expect(page.locator('text=255,2')).toBeVisible();

    // Aktywne konta (2 active out of 3)
    await expect(page.locator('text=Aktywne konta').first()).toBeVisible();
    await expect(page.locator('text=2 / 3')).toBeVisible();
});

// ─── 2. Accounts table ─────────────────────────────────────────────

test('MCC Overview — accounts table shows all accounts', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible();
    await expect(page.locator('text=Ohtime AN')).toBeVisible();
    await expect(page.locator('text=Klimfix')).toBeVisible();
});

test('MCC Overview — account row shows key metrics', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Sushi Naka Naka metrics in compact mode
    await expect(page.locator('text=254,2')).toBeVisible();      // conversions
    await expect(page.locator('text=9,39')).toBeVisible();       // CPA
    await expect(page.locator('text=1904%')).toBeVisible();      // ROAS
    await expect(page.locator('text=96.2%')).toBeVisible();      // IS (toFixed — dot, not comma)

    // Klimfix — inactive account shows zeros
    await expect(page.locator('text=Brak danych').first()).toBeVisible(); // pacing no_data
});

test('MCC Overview — table headers present in compact mode', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    const headers = ['Konto', 'Wydatki', 'Konwersje', 'CPA', 'ROAS', 'IS', 'Pacing', 'Płatności', 'Zmiany', 'Sync'];
    for (const h of headers) {
        await expect(page.locator(`th:has-text("${h}")`).first()).toBeVisible();
    }

    // Compact mode — these headers should NOT be visible
    await expect(page.locator('th:has-text("Kliknięcia")')).not.toBeVisible();
    await expect(page.locator('th:has-text("CTR")')).not.toBeVisible();
    await expect(page.locator('th:has-text("CPC")')).not.toBeVisible();
});

// ─── 3. Compact mode toggle ────────────────────────────────────────

test('MCC Overview — compact mode toggle shows all columns', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    // Initially compact — no CTR/CPC headers
    await expect(page.locator('th:has-text("CTR")')).not.toBeVisible();

    // Click columns toggle button
    await page.locator('button[title*="kolumny"]').click();

    // Now all columns should be visible
    await expect(page.locator('th:has-text("Kliknięcia")')).toBeVisible();
    await expect(page.locator('th:has-text("CTR")')).toBeVisible();
    await expect(page.locator('th:has-text("CPC")')).toBeVisible();
    await expect(page.locator('th:has-text("CVR")')).toBeVisible();
});

// ─── 4. Period buttons ─────────────────────────────────────────────

test('MCC Overview — period buttons are visible', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    for (const label of ['7d', '14d', '30d', 'MTD']) {
        await expect(page.locator(`button:has-text("${label}")`)).toBeVisible();
    }
});

// ─── 5. Action buttons ─────────────────────────────────────────────

test('MCC Overview — action buttons present', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    await expect(page.locator('button:has-text("Synchronizuj nieaktualne")')).toBeVisible();
    await expect(page.locator('button:has-text("Odkryj konta")')).toBeVisible();
});

// ─── 6. Sorting ─────────────────────────────────────────────────────

test('MCC Overview — clicking sort header changes order', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Default sort by spend desc — Sushi first
    const rows = page.locator('tbody tr');
    const firstRowText = await rows.first().textContent();
    expect(firstRowText).toContain('Sushi Naka Naka');

    // Click "Wydatki" header to toggle to asc
    await page.locator('th:has-text("Wydatki")').click();

    // Now Klimfix (spend=0) should be first
    const firstRowAfter = await rows.first().textContent();
    expect(firstRowAfter).toContain('Klimfix');
});

// ─── 7. Row click navigates to dashboard ────────────────────────────

test('MCC Overview — clicking account row navigates to dashboard', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Click on Sushi Naka Naka row
    await page.locator('tr:has-text("Sushi Naka Naka")').click();

    // Should navigate to /dashboard
    await expect(page).toHaveURL(/\/dashboard/);
});

// ─── 8. MCC Exclusion Lists ────────────────────────────────────────

test('MCC Overview — exclusion lists section expands', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    // Initially collapsed
    await expect(page.locator('text=Wykluczenia MCC')).toBeVisible();
    await expect(page.locator('text=Wykluczające frazy MCC')).not.toBeVisible();

    // Expand
    await page.locator('button:has-text("Wykluczenia MCC")').click();

    // Both sections visible
    await expect(page.locator('text=Wykluczające frazy MCC')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('text=Wykluczone miejsca docelowe MCC')).toBeVisible();

    // Lists visible
    await expect(page.locator('text=Wulgaryzmy i spam')).toBeVisible();
    await expect(page.locator('text=Nieistotne intencje')).toBeVisible();
    await expect(page.locator('text=Spammerskie strony')).toBeVisible();
});

test('MCC Overview — keyword list drill-down shows items', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    // Expand exclusions section
    await page.locator('button:has-text("Wykluczenia MCC")').click();
    await expect(page.locator('text=Wulgaryzmy i spam')).toBeVisible({ timeout: 5_000 });

    // Click on keyword list to expand
    await page.locator('tr:has-text("Wulgaryzmy i spam")').click();

    // Items should appear
    await expect(page.locator('text=darmowe')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('text=za darmo')).toBeVisible();
    await expect(page.locator('text=crack')).toBeVisible();
    await expect(page.locator('text=PHRASE').first()).toBeVisible();
});

// ─── 9. Pacing bars ────────────────────────────────────────────────

test('MCC Overview — pacing bars render for active accounts', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Sushi row should have pacing labels
    const sushiRow = page.locator('tr:has-text("Sushi Naka Naka")');
    await expect(sushiRow.locator('text=Budżet')).toBeVisible();
    await expect(sushiRow.locator('text=Miesiąc')).toBeVisible();
});

// ─── 10. Bulk selection ─────────────────────────────────────────────

test('MCC Overview — checkbox selection shows bulk bar', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Bulk bar should not be visible initially
    await expect(page.locator('text=Zaznaczono')).not.toBeVisible();

    // Click checkbox in first row
    const firstCheckbox = page.locator('tbody tr').first().locator('input[type="checkbox"]');
    await firstCheckbox.click();

    // Bulk bar should appear
    await expect(page.locator('text=Zaznaczono: 1')).toBeVisible();
    await expect(page.locator('button:has-text("Synchronizuj")').first()).toBeVisible();
});

// ─── 11. New access badge ───────────────────────────────────────────

test('MCC Overview — new access badge shows for Sushi', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Sushi has new_access_emails, should show UserPlus icon with title
    const badge = page.locator('[title*="nowy@example.com"]');
    await expect(badge).toBeVisible();
});

// ─── 12. Changes column ────────────────────────────────────────────

test('MCC Overview — changes column shows external changes', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Sushi row: 59 total, 5 external
    await expect(page.locator('text=5 zewn.').first()).toBeVisible();

    // Ohtime: 95 total, 95 external
    await expect(page.locator('text=95 zewn.').first()).toBeVisible();
});

// ─── 13. Empty state ────────────────────────────────────────────────

test('MCC Overview — empty state when no accounts', async ({ page }) => {
    // Override with empty data
    await page.route(/\/api\/v1\/mcc\/overview/, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ synced_at: '2026-04-09T12:00:00Z', date_from: '2026-03-10', date_to: '2026-04-09', accounts: [] }),
        })
    );

    await page.goto('/mcc-overview');
    await expect(page.locator('text=Brak kont')).toBeVisible({ timeout: 10_000 });
});

// ─── 14. No JS errors ──────────────────────────────────────────────

test('MCC Overview — no unhandled JS errors on page load', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto('/mcc-overview');
    await expect(page.locator('h1:has-text("Wszystkie konta")')).toBeVisible({ timeout: 10_000 });

    // Wait a bit for lazy loads
    await page.waitForTimeout(2000);

    expect(errors).toHaveLength(0);
});

// ─── 15. Sync indicator shows date ─────────────────────────────────

test('MCC Overview — sync date displayed', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    // Sync date "09.04.2026"
    await expect(page.locator('text=09.04.2026').first()).toBeVisible();
});

// ─── 16. Google Ads external link ───────────────────────────────────

test('MCC Overview — Google Ads external link present', async ({ page }) => {
    await page.goto('/mcc-overview');
    await expect(page.locator('text=Sushi Naka Naka')).toBeVisible({ timeout: 10_000 });

    const link = page.locator('a[href*="ads.google.com"]').first();
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('ocid=');
});
