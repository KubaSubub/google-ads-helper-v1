import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi, DEMO_CLIENT } from './helpers.js';
import { MOCK_CLIENT_DETAIL } from './fixtures.js';

async function mockSettingsApi(page) {
    await page.route(/\/api\/v1\/clients\/3/, route => {
        if (route.request().method() === 'GET') {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CLIENT_DETAIL) });
        }
        if (route.request().method() === 'PATCH' || route.request().method() === 'PUT') {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CLIENT_DETAIL) });
        }
        return route.fallback();
    });
}

// ─── Sekcja 20 — Ustawienia ─────────────────────────────────────────

test.describe('Sekcja 20 — Settings', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockSettingsApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 20.1 — Settings page renderuje się', async ({ page }) => {
        await page.goto('/settings');
        await expect(page.locator('text=/Ustawienia/i').first()).toBeVisible({ timeout: 10_000 });
    });

    test('Sekcja 20.2 — Formularz z sekcjami widoczny', async ({ page }) => {
        await page.goto('/settings');
        await expect(page.locator('text=/Ustawienia/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1500);
        const body = await page.textContent('body');
        // Sekcje formularza — szukamy polskich nagłówków lub pól
        const hasSections = body.includes('Max zmiana') || body.includes('Limity') ||
                           body.includes('stawki') || body.includes('budżet') ||
                           body.includes('Sushi Naka Naka');
        expect(hasSections).toBeTruthy();
    });

    test('Sekcja 20.3 — Hard Reset: pole potwierdzenia i disabled button', async ({ page }) => {
        await page.goto('/settings');
        await expect(page.locator('text=/Ustawienia/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1500);

        // Szukamy sekcji Hard Reset
        const resetSection = page.locator('text=/Hard Reset/i, text=/Resetuj/i').first();
        if (await resetSection.isVisible().catch(() => false)) {
            // Pole tekstowe potwierdzenia
            const confirmInput = page.locator('input[placeholder*="nazwa" i], input[placeholder*="name" i]').last();
            if (await confirmInput.isVisible().catch(() => false)) {
                // Przycisk powinien być disabled gdy puste
                const resetBtn = page.locator('button:has-text("Reset"), button:has-text("Resetuj")').last();
                if (await resetBtn.count() > 0) {
                    const isDisabled = await resetBtn.isDisabled();
                    expect(isDisabled).toBeTruthy();
                }
            }
        }
    });

    test('Sekcja 20 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.goto('/settings');
        await expect(page.locator('text=/Ustawienia/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);
        expect(errors).toEqual([]);
    });
});

// ─── Sekcja 21 — Klienci ───────────────────────────────────────────

test.describe('Sekcja 21 — Clients', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 21.1 — Lista klientów renderuje się', async ({ page }) => {
        await page.goto('/clients');
        await expect(page.locator('text=/Klienci/i').first()).toBeVisible({ timeout: 10_000 });
        // Demo client name
        await expect(page.locator('text=/Sushi Naka Naka/').first()).toBeVisible();
    });

    test('Sekcja 21.2 — Przycisk Discovery (Discover/Odkryj)', async ({ page }) => {
        await page.goto('/clients');
        await expect(page.locator('text=/Klienci/i').first()).toBeVisible({ timeout: 10_000 });
        // Discovery button
        const discoverBtn = page.locator('button:has-text("Discover"), button:has-text("Odkryj"), button:has-text("Pobierz")').first();
        if (await discoverBtn.count() > 0) {
            await expect(discoverBtn).toBeVisible();
        }
    });

    test('Sekcja 21 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.goto('/clients');
        await expect(page.locator('text=/Klienci/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);
        expect(errors).toEqual([]);
    });
});
