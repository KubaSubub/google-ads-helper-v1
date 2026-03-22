import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import {
    MOCK_CAMPAIGNS, MOCK_QUALITY_SCORE_AUDIT, MOCK_FORECAST,
    MOCK_SEMANTIC_CLUSTERS, MOCK_ANALYTICS_EMPTY,
} from './fixtures.js';

async function mockAnalyticsApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    // Catch-all for analytics endpoints — zwracaj puste dane
    const analyticsEndpoints = [
        'dayparting', 'rsa-analysis', 'ngram-analysis', 'match-type-analysis',
        'landing-pages', 'wasted-spend', 'account-structure', 'bidding-advisor',
        'hourly-dayparting', 'conversion-health', 'ad-group-health',
        'smart-bidding-health', 'pareto-analysis', 'scaling-opportunities',
        'target-vs-actual', 'bid-strategy-report', 'learning-status',
        'portfolio-health', 'conversion-quality', 'demographics',
        'pmax-channels', 'asset-group-performance', 'pmax-search-themes',
        'audience-performance', 'missing-extensions', 'extension-performance',
        'device-breakdown', 'geo-breakdown', 'budget-pacing', 'impression-share',
        'keyword-expansion', 'search-term-trends', 'close-variants',
    ];
    for (const endpoint of analyticsEndpoints) {
        await page.route(new RegExp(`/api/v1/analytics/${endpoint}`), route =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ANALYTICS_EMPTY) })
        );
    }
}

async function mockQualityScoreApi(page) {
    await page.route(/\/api\/v1\/analytics\/quality-score-audit/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_QUALITY_SCORE_AUDIT) })
    );
}

async function mockForecastApi(page) {
    await page.route(/\/api\/v1\/analytics\/forecast/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_FORECAST) })
    );
}

async function mockSemanticApi(page) {
    await page.route(/\/api\/v1\/semantic\/clusters/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SEMANTIC_CLUSTERS) })
    );
}

// ─── Sekcja 10 — SearchOptimization ────────────────────────────────

test.describe('Sekcja 10 — Search Optimization', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAnalyticsApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 10.1 — Search Optimization page renderuje się', async ({ page }) => {
        await page.goto('/search-optimization');
        await expect(page.locator('text=/Optymalizacja/i').first()).toBeVisible({ timeout: 10_000 });
    });

    test('Sekcja 10.2 — Narzędzia analityczne obecne jako sekcje/przyciski', async ({ page }) => {
        await page.goto('/search-optimization');
        await expect(page.locator('text=/Optymalizacja/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(2000);
        const body = await page.textContent('body');
        // Sprawdzamy obecność kluczowych sekcji analitycznych
        // Nazwy mogą być po polsku lub angielsku
        const tools = [
            'N-gram', 'Match', 'Landing', 'RSA', 'Dayparting',
            'Bidding', 'Pareto', 'Demograf', 'PMax', 'Audien', 'Rozszerz',
            'Wasted', 'Zmarnowane', 'Device', 'Urządz', 'Geo', 'Struktur',
        ];
        let found = 0;
        for (const tool of tools) {
            if (body.toLowerCase().includes(tool.toLowerCase())) found++;
        }
        expect(found).toBeGreaterThanOrEqual(2);
    });

    test('Sekcja 10.3 — Strona renderuje się bez krytycznych crashy', async ({ page }) => {
        await page.goto('/search-optimization');
        await expect(page.locator('text=/Optymalizacja/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);
        // Sprawdź że strona nie pokazuje białego ekranu (heading jest widoczny)
        const heading = page.locator('h1, h2').first();
        await expect(heading).toBeVisible();
    });
});

// ─── Quality Score ──────────────────────────────────────────────────

test.describe('Sekcja 10 — Quality Score', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockQualityScoreApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 10.4 — Quality Score page renderuje się', async ({ page }) => {
        await page.goto('/quality-score');
        await expect(page.locator('text=/Wynik/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1500);
        // Strona renderuje się — heading jest widoczny
        const body = await page.textContent('body');
        expect(body).not.toContain('undefined');
    });
});

// ─── Forecast ───────────────────────────────────────────────────────

test.describe('Sekcja 10 — Forecast', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAnalyticsApi(page);
        await mockForecastApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 10.5 — Forecast page renderuje się', async ({ page }) => {
        await page.goto('/forecast');
        // Forecast potrzebuje wybranej kampanii — sprawdzamy heading
        await page.waitForTimeout(2000);
        const body = await page.textContent('body');
        // Strona powinna się załadować bez białego ekranu
        const rendered = body.includes('Forecast') || body.includes('Prognoza') || body.includes('kampani');
        expect(rendered).toBeTruthy();
    });
});

// ─── Semantic ───────────────────────────────────────────────────────

test.describe('Sekcja 10 — Semantic', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockSemanticApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 10.6 — Semantic page renderuje się', async ({ page }) => {
        await page.goto('/semantic');
        await expect(page.locator('text=/Inteligencja/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1500);
        const body = await page.textContent('body');
        // Strona załadowała się poprawnie
        expect(body).not.toContain('undefined');
    });
});
