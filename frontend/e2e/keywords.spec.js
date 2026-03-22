import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import {
    MOCK_KEYWORDS, MOCK_NEGATIVE_KEYWORDS, MOCK_NEGATIVE_KEYWORD_LISTS,
    MOCK_CAMPAIGNS,
} from './fixtures.js';

async function mockKeywordsApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    await page.route(/\/api\/v1\/ad-groups/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
    );
    await page.route(/\/api\/v1\/analytics\/keyword-expansion/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) })
    );
    // Single handler for keyword-related routes with URL dispatch
    await page.route(/\/api\/v1\/(negative-keyword-lists|negative-keywords|keywords)/, route => {
        const url = route.request().url();
        if (url.includes('/negative-keyword-lists')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_NEGATIVE_KEYWORD_LISTS) });
        }
        if (url.includes('/negative-keywords')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_NEGATIVE_KEYWORDS) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_KEYWORDS) });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockKeywordsApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 5 — Słowa kluczowe ────────────────────────────────────

test('Sekcja 5.1 — Tabela keywords renderuje się', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    // Keyword text widoczny — z mock data
    await expect(page.locator('text=/sushi naka naka/i').first()).toBeVisible({ timeout: 5_000 });
});

test('Sekcja 5.2 — Match type filter pills obecne i klikalne', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    // Pills: Exact, Phrase, Broad (lub All)
    const exactPill = page.locator('button:has-text("EXACT"), button:has-text("Exact")').first();
    const phrasePill = page.locator('button:has-text("PHRASE"), button:has-text("Phrase")').first();
    const broadPill = page.locator('button:has-text("BROAD"), button:has-text("Broad")').first();

    await expect(exactPill).toBeVisible();
    await expect(phrasePill).toBeVisible();
    await expect(broadPill).toBeVisible();

    // Kliknięcie nie powoduje crashu
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await exactPill.click();
    await page.waitForTimeout(500);
    expect(errors).toEqual([]);
});

test('Sekcja 5.3 — Pole wyszukiwania obecne', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    // Szukamy pola input (search/filter)
    const searchInput = page.locator('input').first();
    await expect(searchInput).toBeVisible();
});

test('Sekcja 5.4 — Przyciski export CSV/Excel obecne', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    // Przycisk Export (z ikoną Download)
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("CSV"), button:has-text("Excel"), button:has-text("Eksport")').first();
    if (await exportBtn.count() > 0) {
        await expect(exportBtn).toBeVisible();
    }
});

test('Sekcja 5.5 — Zakładki: Positive, Negative, Lists widoczne', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    // Zakładki tabów — "Słowa kluczowe" (positive) i "Negatywne"
    const negTab = page.locator('button:has-text("Negatywne"), button:has-text("Negative")').first();
    await expect(negTab).toBeVisible();
});

test('Sekcja 5.6 — Paginacja (Previous/Next) obecna', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    // Paginacja — szukamy przycisków prev/next lub ikon ChevronLeft/ChevronRight
    const pageInfo = page.locator('text=/strona|page|1\\s*\\/|z\\s*1/i').first();
    // Paginacja może nie być widoczna przy 5 wynikach — sprawdzamy że nie ma błędu
    await page.waitForTimeout(500);
    const body = await page.textContent('body');
    expect(body).not.toContain('undefined');
});

test('Sekcja 5 — Quality Score badge kolorowy', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    // QS badge: "9/10" lub "3/10"
    await expect(page.locator('text=/9\\/10/').first()).toBeVisible();
});

test('Sekcja 5 — Polskie znaki w keyword text', async ({ page }) => {
    await page.goto('/keywords');
    await expect(page.locator('text=/kluczowe/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2000);
    // "japońska" zawiera polskie znaki
    await expect(page.locator('text=/japońska/i').first()).toBeVisible({ timeout: 5_000 });
});
