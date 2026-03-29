import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_CAMPAIGNS } from './fixtures.js';

// ─── Sekcja 27 — Edge Cases ────────────────────────────────────────

test.describe('Sekcja 27 — Edge Cases: Empty state', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    const PAGES = [
        { path: '/',                  heading: 'Pulpit' },
        { path: '/daily-audit',       heading: 'Codzienny Audyt' },
        { path: '/campaigns',         heading: 'Kampanie' },
        { path: '/keywords',          heading: 'kluczowe' },
        { path: '/search-terms',      heading: 'Wyszukiwane' },
        { path: '/recommendations',   heading: 'Rekomendacje' },
        { path: '/action-history',    heading: 'Historia' },
        { path: '/alerts',            heading: 'Monitoring' },
        { path: '/audit-center',         heading: 'Centrum' },
        { path: '/quality-score',     heading: 'Wynik' },
        { path: '/semantic',          heading: 'Inteligencja' },
        { path: '/clients',           heading: 'Klienci' },
        { path: '/settings',          heading: 'Ustawienia' },
    ];

    for (const { path, heading } of PAGES) {
        test(`Sekcja 27.1 — Empty state: ${path} nie crashuje`, async ({ page }) => {
            const errors = [];
            page.on('pageerror', (err) => errors.push(err.message));
            await page.goto(path);
            await expect(
                page.locator(`text=/${heading}/i`).first()
            ).toBeVisible({ timeout: 10_000 });
            await page.waitForTimeout(500);
            expect(errors).toEqual([]);
        });
    }
});

test.describe('Sekcja 27 — Edge Cases: Polish characters', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 27.2 — Polskie znaki wyświetlają się poprawnie (nie mojibake)', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });
        const body = await page.textContent('body');
        // Sprawdź że nie ma mojibake (broken UTF-8)
        expect(body).not.toContain('Ä');
        expect(body).not.toContain('Ĺ');
        expect(body).not.toContain('Ã³');
        // Sprawdź że polskie znaki renderują się poprawnie
        // Sidebar labels powinny zawierać polskie znaki
        const hasPolish = body.includes('Słowa kluczowe') || body.includes('Wyszukiwane') ||
                         body.includes('Codzienny') || body.includes('Klienci');
        expect(hasPolish).toBeTruthy();
    });

    test('Sekcja 27.2b — Polskie znaki: ą ę ó ś ź ż ć ń ł obecne w UI', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('nav')).toBeVisible({ timeout: 10_000 });
        const body = await page.textContent('body');
        // Sidebar ma "Słowa kluczowe" (ł), "Wyszukiwane" (ó nie, ale ź), etc.
        // Sprawdź kilka polskich znaków
        expect(body).toMatch(/[ąęóśźżćńł]/);
    });
});

test.describe('Sekcja 27 — Edge Cases: No undefined/NaN', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        // Mock z danymi żeby sprawdzić formatowanie
        await page.route(/\/api\/v1\/campaigns/, route =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMPAIGNS) })
        );
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    const CRITICAL_PAGES = [
        { path: '/',            heading: 'Pulpit' },
        { path: '/campaigns',   heading: 'Kampanie' },
        { path: '/keywords',    heading: 'kluczowe' },
    ];

    for (const { path, heading } of CRITICAL_PAGES) {
        test(`Sekcja 27.3 — Brak "undefined"/"NaN" na ${path}`, async ({ page }) => {
            await page.goto(path);
            await expect(
                page.locator(`text=/${heading}/i`).first()
            ).toBeVisible({ timeout: 10_000 });
            await page.waitForTimeout(1500);
            const body = await page.textContent('body');
            expect(body).not.toContain('undefined');
            expect(body).not.toContain('NaN');
        });
    }
});

test.describe('Sekcja 27 — Edge Cases: Responsive', () => {
    test('Sekcja 27.4 — Responsywność: sidebar na małym viewport', async ({ page }) => {
        // Ustawienie małego viewportu (mobilny)
        await page.setViewportSize({ width: 375, height: 812 });

        await mockEmptyApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });

        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await page.goto('/');
        await page.waitForTimeout(2000);
        // Brak crashy na małym viewport
        expect(errors).toEqual([]);
    });
});

test.describe('Sekcja 27 — Edge Cases: Long campaign names', () => {
    test('Sekcja 27.5 — Długie nazwy kampanii nie łamią layoutu', async ({ page }) => {
        const longNameCampaigns = {
            items: [
                {
                    ...MOCK_CAMPAIGNS.items[0],
                    name: 'Bardzo Długa Nazwa Kampanii Która Ma Więcej Niż Sto Znaków I Powinna Się Poprawnie Wyświetlać Bez Łamania Układu Strony W Tabeli Kampanii',
                },
            ],
            total: 1,
        };

        await mockEmptyApi(page);
        await page.route(/\/api\/v1\/campaigns/, route =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(longNameCampaigns) })
        );
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });

        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await page.goto('/campaigns');
        await expect(page.locator('text=/Kampanie/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);

        // Brak JS errors
        expect(errors).toEqual([]);
        // Długa nazwa jest renderowana
        await expect(page.locator('text=/Bardzo Długa Nazwa/').first()).toBeVisible();
    });
});
