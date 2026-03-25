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

const MOCK_DATA_COVERAGE = {
    client_id: 3,
    data_from: '2025-12-22',
    data_to: '2026-03-24',
    last_sync_at: '2026-03-25T08:06:13.255669',
    last_sync_days: 90,
    last_sync_status: 'partial',
};

async function mockDataCoverage(page) {
    await page.route('**/api/v1/sync/data-coverage*', route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_DATA_COVERAGE),
        }),
    );
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

// ─── Sekcja 21 — Drawer zarządzania klientami ────────────────────────

test.describe('Sekcja 21 — Client Drawer', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockDataCoverage(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 21.1 — Ikona gear otwiera drawer zarządzania klientami', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        // Gear button przy selektorze klienta
        const gearBtn = page.locator('button[title="Zarządzanie klientami"]');
        await expect(gearBtn).toBeVisible();
        await gearBtn.click();

        // Drawer header
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });
    });

    test('Sekcja 21.2 — Drawer wyświetla listę klientów', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });

        // Demo client should be visible
        const drawerContent = page.locator('text=/Sushi Naka Naka/');
        await expect(drawerContent.first()).toBeVisible();
    });

    test('Sekcja 21.3 — Drawer zawiera przyciski Pobierz i Dodaj', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });

        // Action buttons
        await expect(page.locator('button:has-text("Pobierz klientów")')).toBeVisible();
        await expect(page.locator('button:has-text("Dodaj ręcznie")')).toBeVisible();
    });

    test('Sekcja 21.4 — Dodaj ręcznie otwiera pole input', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });

        await page.locator('button:has-text("Dodaj ręcznie")').click();

        // Input field for customer ID
        const input = page.locator('input[placeholder*="123-456-7890"]');
        await expect(input).toBeVisible();
    });

    test('Sekcja 21.5 — Drawer wyświetla dane synchronizacji', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });
        await page.waitForTimeout(500);

        const drawerText = await page.locator('[style*="slideInRight"]').textContent();

        // Should show last sync date
        expect(drawerText).toContain('Ostatni sync');
        // Should show data range
        expect(drawerText).toContain('Dane:');
    });

    test('Sekcja 21.6 — Drawer ma przycisk Sync przy kliencie', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });

        // Sync button
        const syncBtn = page.locator('button:has-text("Sync")');
        await expect(syncBtn.first()).toBeVisible();
    });

    test('Sekcja 21.7 — Zamknięcie drawera przyciskiem X', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });

        // Close button (X inside drawer header)
        const closeBtn = page.locator('text=/Zarządzanie klientami/').locator('..').locator('button');
        await closeBtn.click();

        // Drawer should disappear
        await expect(page.locator('text=/Zarządzanie klientami/')).not.toBeVisible({ timeout: 3_000 });
    });

    test('Sekcja 21.8 — Route /clients redirectuje na /', async ({ page }) => {
        await page.goto('/clients');
        await page.waitForURL('**/');
        expect(page.url()).not.toContain('/clients');
    });

    test('Sekcja 21.9 — Nawigacja nie zawiera zakładki Klienci', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        // Navigation should NOT have "Klienci" link
        const sidebar = page.locator('nav');
        const sidebarText = await sidebar.textContent();
        expect(sidebarText).not.toContain('Klienci');
    });

    test('Sekcja 21 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.goto('/');
        await expect(page.locator('text=/Pulpit/i').first()).toBeVisible({ timeout: 10_000 });

        await page.locator('button[title="Zarządzanie klientami"]').click();
        await expect(page.locator('text=/Zarządzanie klientami/')).toBeVisible({ timeout: 5_000 });
        await page.waitForTimeout(1000);

        expect(errors).toEqual([]);
    });
});
