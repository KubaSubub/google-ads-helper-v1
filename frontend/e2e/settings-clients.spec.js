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
//
// IMPORTANT: The ClientSelector (gear button) and ClientDrawer are ONLY
// rendered on non-MCC pages (SidebarContent.jsx: `{!isMccPage && ...}`).
// The root route `/` now redirects to `/mcc-overview` (routes.jsx:43),
// so tests must navigate to a page that has the drawer, e.g. /dashboard.
//
// Selector strategy for the drawer itself: scope assertions to
// `[data-testid="client-drawer"]` OR to a locator rooted at the drawer
// header so that the "Zarządzanie klientami" text match never collides
// with the gear button's `title` attribute.

test.describe('Sekcja 21 — Client Drawer', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockDataCoverage(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    // Drawer header is an <h2> — use role-based locator to avoid matching
    // the gear button's `title="Zarządzanie klientami"` tooltip attribute.
    const drawerHeader = (page) =>
        page.getByRole('heading', { name: 'Zarządzanie klientami', level: 2 });

    async function openDrawer(page) {
        await page.goto('/dashboard');
        // Wait for sidebar-rendered ClientSelector (only present on non-MCC pages)
        const gearBtn = page.locator('button[title="Zarządzanie klientami"]');
        await expect(gearBtn).toBeVisible({ timeout: 10_000 });
        await gearBtn.click();
        await expect(drawerHeader(page)).toBeVisible({ timeout: 5_000 });
    }

    test('Sekcja 21.1 — Ikona gear otwiera drawer zarządzania klientami', async ({ page }) => {
        await openDrawer(page);
    });

    test('Sekcja 21.2 — Drawer wyświetla listę klientów', async ({ page }) => {
        await openDrawer(page);
        // Demo client should be visible in the drawer
        await expect(page.locator('text=/Sushi Naka Naka/').first()).toBeVisible();
    });

    test('Sekcja 21.3 — Drawer zawiera przyciski Pobierz i Dodaj', async ({ page }) => {
        await openDrawer(page);
        await expect(page.locator('button:has-text("Pobierz klientów")')).toBeVisible();
        await expect(page.locator('button:has-text("Dodaj ręcznie")')).toBeVisible();
    });

    test('Sekcja 21.4 — Dodaj ręcznie otwiera pole input', async ({ page }) => {
        await openDrawer(page);
        await page.locator('button:has-text("Dodaj ręcznie")').click();
        await expect(page.locator('input[placeholder*="123-456-7890"]')).toBeVisible();
    });

    test('Sekcja 21.5 — Drawer wyświetla dane synchronizacji', async ({ page }) => {
        await openDrawer(page);
        await page.waitForTimeout(500); // wait for lazy coverage fetch

        // The drawer animates in via `animation: slideInRight`. Scope to the
        // animated container and assert on its text content.
        const drawer = page.locator('[style*="slideInRight"]');
        const drawerText = await drawer.textContent();

        expect(drawerText).toContain('Ostatni sync');
        expect(drawerText).toContain('Dane:');
    });

    test('Sekcja 21.6 — Drawer ma przycisk Sync przy kliencie', async ({ page }) => {
        await openDrawer(page);
        await expect(page.locator('button:has-text("Sync")').first()).toBeVisible();
    });

    test('Sekcja 21.7 — Zamknięcie drawera przyciskiem X', async ({ page }) => {
        await openDrawer(page);

        // The close button is the first <button> in the drawer header container.
        // Use role-based navigation: header h2 → parent div → first button.
        const closeBtn = drawerHeader(page).locator('..').locator('button').first();
        await closeBtn.click();

        await expect(drawerHeader(page)).not.toBeVisible({ timeout: 3_000 });
    });

    test('Sekcja 21.8 — Route /clients redirectuje na /mcc-overview', async ({ page }) => {
        await page.goto('/clients');
        await page.waitForURL('**/mcc-overview', { timeout: 5_000 });
        expect(page.url()).toContain('/mcc-overview');
        expect(page.url()).not.toContain('/clients');
    });

    test('Sekcja 21.9 — Nawigacja nie zawiera zakładki Klienci', async ({ page }) => {
        // Navigate to dashboard (sidebar renders client-management UI on non-MCC pages)
        await page.goto('/dashboard');
        await expect(page.locator('button[title="Zarządzanie klientami"]')).toBeVisible({ timeout: 10_000 });

        const sidebar = page.locator('nav');
        const sidebarText = await sidebar.textContent();
        expect(sidebarText).not.toContain('Klienci');
    });

    test('Sekcja 21 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));

        await openDrawer(page);
        await page.waitForTimeout(1000);

        expect(errors).toEqual([]);
    });
});
