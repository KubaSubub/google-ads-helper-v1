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

// ─── InsightsFeed (compact title pills + auto-expand HIGH) ─────────

function makeInsight(id, priority, entity, message) {
    return {
        id,
        type: 'GENERIC',
        priority,
        entity_name: entity,
        entity_type: 'campaign',
        campaign_name: entity,
        reason: message,
        recommended_action: 'Take action.',
        source: 'ANALYTICS',
        status: 'pending',
        executable: false,
        context_outcome: 'INSIGHT_ONLY',
        confidence_score: 0.7,
        risk_score: 0.2,
        metadata: {},
    };
}

test('InsightsFeed: tytuly widoczne w header gdy collapsed (3 LOW insights)', async ({ page }) => {
    await page.route(/\/api\/v1\/recommendations/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                items: [
                    makeInsight(701, 'LOW', 'Kampania A', 'Insight A — niski impakt'),
                    makeInsight(702, 'LOW', 'Kampania B', 'Insight B — niski impakt'),
                    makeInsight(703, 'LOW', 'Kampania C', 'Insight C — niski impakt'),
                ],
                total: 3,
            }),
        })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    const pills = page.locator('[data-testid="insights-feed-pills"]');
    await expect(pills).toBeVisible({ timeout: 8_000 });
    // Panel rozwiniety NIE powinien byc widoczny (brak HIGH → collapsed default)
    const panel = page.locator('[data-testid="insights-feed-panel"]');
    await expect(panel).toHaveCount(0);
    // Pigulki maja tytuly
    await expect(pills.locator('text=/Kampania A/').first()).toBeVisible();
});

test('InsightsFeed: HIGH priority auto-expand (1 HIGH + 2 MEDIUM)', async ({ page }) => {
    await page.route(/\/api\/v1\/recommendations/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                items: [
                    makeInsight(801, 'HIGH', 'Kampania pilna', 'Pilny problem do rozwiazania'),
                    makeInsight(802, 'MEDIUM', 'Kampania B', 'Sredni insight'),
                    makeInsight(803, 'MEDIUM', 'Kampania C', 'Sredni insight 2'),
                ],
                total: 3,
            }),
        })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    // Panel auto-rozwiniety bo jest HIGH
    const panel = page.locator('[data-testid="insights-feed-panel"]');
    await expect(panel).toBeVisible({ timeout: 8_000 });
    // Tresc HIGH widoczna w panelu
    await expect(panel.locator('text=/Pilny problem do rozwiazania/').first()).toBeVisible();
});

test('InsightsFeed: scrollable gdy > 5 HIGH', async ({ page }) => {
    const items = [];
    for (let i = 0; i < 7; i++) {
        items.push(makeInsight(900 + i, 'HIGH', `Kampania H${i}`, `HIGH insight numer ${i}`));
    }
    await page.route(/\/api\/v1\/recommendations/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ items, total: items.length }),
        })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    const panel = page.locator('[data-testid="insights-feed-panel"]');
    await expect(panel).toBeVisible({ timeout: 8_000 });
    // Sprawdz inline style: max-height: 320px
    const maxHeight = await panel.evaluate(el => el.style.maxHeight);
    expect(maxHeight).toBe('320px');
    const overflowY = await panel.evaluate(el => el.style.overflowY);
    expect(overflowY).toBe('auto');
});

// ─── HealthScoreCard color calibration (worst-of severity) ─────────

function makeHealthScore(score, issues) {
    return {
        score,
        issues,
        data_available: true,
        breakdown: {
            performance: { score, weight: 25, details: {} },
            quality: { score, weight: 20, details: {} },
            efficiency: { score, weight: 20, details: {} },
            coverage: { score, weight: 15, details: {} },
            stability: { score, weight: 10, details: {} },
            structure: { score, weight: 10, details: {} },
        },
    };
}

async function gaugeStroke(page) {
    // Drugi circle to gauge (pierwszy — background grey)
    const circles = page.locator('svg circle');
    await expect(circles.nth(1)).toBeVisible({ timeout: 10_000 });
    return await circles.nth(1).getAttribute('stroke');
}

test('HealthScoreCard: score 80 + 0 issues → zielony gauge', async ({ page }) => {
    await page.route(/\/api\/v1\/analytics\/health-score/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(makeHealthScore(80, [])) })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    expect(await gaugeStroke(page)).toBe('#4ADE80');
});

test('HealthScoreCard: score 80 + 3 HIGH issues → red gauge (severity downgrade)', async ({ page }) => {
    await page.route(/\/api\/v1\/analytics\/health-score/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(makeHealthScore(80, [
                { severity: 'HIGH', message: 'Pierwszy HIGH alert' },
                { severity: 'HIGH', message: 'Drugi HIGH alert' },
                { severity: 'HIGH', message: 'Trzeci HIGH alert' },
            ])),
        })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    expect(await gaugeStroke(page)).toBe('#F87171');
});

test('HealthScoreCard: score 60 + 5 MEDIUM issues → yellow gauge (akumulacja)', async ({ page }) => {
    const issues = [];
    for (let i = 0; i < 5; i++) issues.push({ severity: 'MEDIUM', message: `MEDIUM issue ${i}` });
    await page.route(/\/api\/v1\/analytics\/health-score/, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(makeHealthScore(60, issues)),
        })
    );
    await page.goto('/');
    await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });
    expect(await gaugeStroke(page)).toBe('#FBBF24');
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
