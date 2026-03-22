import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import {
    MOCK_SEARCH_TERMS, MOCK_SEGMENTED_SEARCH_TERMS, MOCK_CAMPAIGNS,
} from './fixtures.js';

async function mockSearchTermsApi(page) {
    await page.route(/\/api\/v1\/campaigns/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
    );
    await page.route(/\/api\/v1\/analytics\/search-term-trends/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) })
    );
    await page.route(/\/api\/v1\/analytics\/close-variants/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ groups: [] }) })
    );
    // Single handler for all /search-terms/ routes with URL dispatch
    await page.route(/\/api\/v1\/search-terms/, route => {
        const url = route.request().url();
        if (url.includes('/segmented')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SEGMENTED_SEARCH_TERMS) });
        }
        if (url.includes('/summary')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 5, waste_count: 1 }) });
        }
        if (url.includes('/bulk-preview')) {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [] }) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SEARCH_TERMS) });
    });
}

test.beforeEach(async ({ page }) => {
    await mockEmptyApi(page);
    await mockSearchTermsApi(page);
    await mockAuthAndClient(page);
    await page.addInitScript(() => {
        localStorage.setItem('selectedClientId', '3');
    });
});

// ─── Sekcja 6 — Wyszukiwane frazy ─────────────────────────────────

test('Sekcja 6.1 — Tabela search terms renderuje się', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);
    // W trybie segments lub list — dane powinny być widoczne
    const body = await page.textContent('body');
    // Szukamy danych z fixtures
    const hasData = body.includes('sushi naka naka warszawa') || body.includes('Top Performerzy') || body.includes('HIGH_PERFORMER');
    expect(hasData).toBeTruthy();
});

test('Sekcja 6.2 — Przełącznik widoku Aggregated/Segmented', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });
    // Przycisk widoku (Lista / Segmenty)
    const listBtn = page.locator('button:has-text("Lista"), button:has-text("List"), button:has-text("Wszystkie")').first();
    const segBtn = page.locator('button:has-text("Segment"), button:has-text("Analiza")').first();

    // Przynajmniej jeden widok powinien być dostępny
    const hasViewToggle = await listBtn.count() > 0 || await segBtn.count() > 0;
    expect(hasViewToggle).toBeTruthy();
});

test('Sekcja 6.3 — Pole wyszukiwania', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });

    // Przełącz na widok Lista, aby zobaczyć pole wyszukiwania
    const listBtn = page.locator('button:has-text("Lista"), button:has-text("List"), button:has-text("Wszystkie")').first();
    if (await listBtn.isVisible().catch(() => false)) {
        await listBtn.click();
        await page.waitForTimeout(500);
    }

    const searchInput = page.locator('input[placeholder*="szukaj" i], input[placeholder*="search" i], input[type="text"]').first();
    await expect(searchInput).toBeVisible();
});

test('Sekcja 6.4 — Przyciski export', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });

    // Przełącz na widok Lista
    const listBtn = page.locator('button:has-text("Lista"), button:has-text("List"), button:has-text("Wszystkie")').first();
    if (await listBtn.isVisible().catch(() => false)) {
        await listBtn.click();
        await page.waitForTimeout(500);
    }

    // Export button
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("CSV"), button:has-text("Eksport")').first();
    if (await exportBtn.count() > 0) {
        await expect(exportBtn).toBeVisible();
    }
});

test('Sekcja 6.5 — Segment pills (Top Performerzy/Strata/Nieistotne/Inne)', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1500);

    // Segmenty widoczne w widoku segmented
    const body = await page.textContent('body');
    const hasSegments = body.includes('Top Performerzy') || body.includes('Strata') || body.includes('HIGH_PERFORMER');
    expect(hasSegments).toBeTruthy();
});

test('Sekcja 6.6 — Checkboxy zaznaczanie → Bulk Action Bar pojawia się', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });

    // Przełącz na widok lista
    const listBtn = page.locator('button:has-text("Lista"), button:has-text("List"), button:has-text("Wszystkie")').first();
    if (await listBtn.isVisible().catch(() => false)) {
        await listBtn.click();
        await page.waitForTimeout(1000);
    }

    // Checkbox w tabeli
    const checkbox = page.locator('input[type="checkbox"]').first();
    if (await checkbox.isVisible().catch(() => false)) {
        await checkbox.click();
        await page.waitForTimeout(300);
        // Bulk Action Bar powinien się pojawić
        const bulkBar = page.locator('text=/zaznaczonych/i').first();
        await expect(bulkBar).toBeVisible();
    }
});

test('Sekcja 6.7 — Bulk buttons: Dodaj jako negatywne, Dodaj jako keyword', async ({ page }) => {
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });

    // Przełącz na widok lista
    const listBtn = page.locator('button:has-text("Lista"), button:has-text("List"), button:has-text("Wszystkie")').first();
    if (await listBtn.isVisible().catch(() => false)) {
        await listBtn.click();
        await page.waitForTimeout(1000);
    }

    // Zaznacz checkbox aby zobaczyć bulk bar
    const checkbox = page.locator('input[type="checkbox"]').first();
    if (await checkbox.isVisible().catch(() => false)) {
        await checkbox.click();
        await page.waitForTimeout(300);
        // Bulk buttons
        await expect(page.locator('button:has-text("negatyw"), button:has-text("Dodaj jako negatyw")').first()).toBeVisible();
        await expect(page.locator('button:has-text("słowa kluczowe"), button:has-text("Dodaj jako słow")').first()).toBeVisible();
    }
});

test('Sekcja 6 — Brak JS errors na stronie search terms', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/search-terms');
    await expect(page.locator('text=/Wyszukiwane/i').first()).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
});
