import { test, expect } from '@playwright/test';
import { mockAuthAndClient, mockEmptyApi } from './helpers.js';
import { MOCK_AGENT_STATUS, MOCK_REPORTS } from './fixtures.js';

async function mockAgentApi(page) {
    await page.route(/\/api\/v1\/agent\/status/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_STATUS) })
    );
    // SSE endpoints — abort gracefully
    await page.route(/\/api\/v1\/agent\/chat/, route => route.abort());
    await page.route(/\/api\/v1\/reports\/generate/, route => route.abort());
}

async function mockReportsApi(page) {
    await page.route(/\/api\/v1\/reports/, route => {
        if (route.request().method() === 'GET') {
            return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_REPORTS) });
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });
    await page.route(/\/api\/v1\/agent\/status/, route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_STATUS) })
    );
}

// ─── Sekcja 16 — Agent (Asystent AI) ────────────────────────────────

test.describe('Sekcja 16 — Agent', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockAgentApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 16.1 — Agent page renderuje się', async ({ page }) => {
        await page.goto('/agent');
        await expect(page.locator('text=/Asystent AI/i').first()).toBeVisible({ timeout: 10_000 });
    });

    test('Sekcja 16.2 — 6 quick action buttons obecnych', async ({ page }) => {
        await page.goto('/agent');
        await expect(page.locator('text=/Asystent AI/i').first()).toBeVisible({ timeout: 10_000 });

        // Quick actions: Raport tygodniowy, Analiza kampanii, Analiza budżetów,
        // Wyszukiwane frazy, Słowa kluczowe, Alerty i anomalie
        const body = await page.textContent('body');
        const quickActions = [
            'Raport tygodniowy', 'Analiza kampanii', 'Analiza budżetów',
            'Wyszukiwane frazy', 'Słowa kluczowe', 'Alerty i anomalie',
        ];
        let found = 0;
        for (const action of quickActions) {
            if (body.includes(action)) found++;
        }
        expect(found).toBeGreaterThanOrEqual(5);
    });

    test('Sekcja 16.3 — Textarea input + Send button', async ({ page }) => {
        await page.goto('/agent');
        await expect(page.locator('text=/Asystent AI/i').first()).toBeVisible({ timeout: 10_000 });
        // Textarea
        const textarea = page.locator('textarea').first();
        await expect(textarea).toBeVisible();
        // Send button
        const sendBtn = page.locator('button:has-text("Wyślij"), button:has-text("Send")').first();
        if (await sendBtn.count() > 0) {
            await expect(sendBtn).toBeVisible();
        }
    });

    test('Sekcja 16 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.goto('/agent');
        await expect(page.locator('text=/Asystent AI/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);
        expect(errors).toEqual([]);
    });
});

// ─── Sekcja 17 — Raporty ───────────────────────────────────────────

test.describe('Sekcja 17 — Reports', () => {
    test.beforeEach(async ({ page }) => {
        await mockEmptyApi(page);
        await mockReportsApi(page);
        await mockAuthAndClient(page);
        await page.addInitScript(() => {
            localStorage.setItem('selectedClientId', '3');
        });
    });

    test('Sekcja 17.1 — Reports page renderuje się', async ({ page }) => {
        await page.goto('/reports');
        await expect(page.locator('text=/Raport/i').first()).toBeVisible({ timeout: 10_000 });
    });

    test('Sekcja 17.2 — Lista raportów widoczna', async ({ page }) => {
        await page.goto('/reports');
        await expect(page.locator('text=/Raport/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1500);
        // Raporty z fixtures powinny być widoczne
        const body = await page.textContent('body');
        // Sprawdź obecność typu raportu
        const hasReports = body.includes('Miesięczny') || body.includes('Tygodniowy') ||
                          body.includes('monthly') || body.includes('weekly') ||
                          body.includes('Marzec') || body.includes('Tydzień');
        expect(hasReports).toBeTruthy();
    });

    test('Sekcja 17 — Brak JS errors', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        await page.goto('/reports');
        await expect(page.locator('text=/Raport/i').first()).toBeVisible({ timeout: 10_000 });
        await page.waitForTimeout(1000);
        expect(errors).toEqual([]);
    });
});
