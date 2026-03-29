import { test, expect } from '@playwright/test';
import path from 'path';

/**
 * Visual Audit — screenshot every page against LIVE backend.
 * Requires: backend on :8000, frontend on :5173, seeded DB.
 *
 * Modes:
 *   npx playwright test e2e/visual-audit.spec.js --reporter=list
 *     → First run: creates baseline snapshots in e2e/visual-audit.spec.js-snapshots/
 *     → Next runs: compares with baseline, fails if diff > 5%
 *
 *   npx playwright test e2e/visual-audit.spec.js --update-snapshots
 *     → Updates baseline snapshots (after intentional UI changes)
 *
 * Manual screenshots also saved to: frontend/e2e-screenshots/ (for audit reports)
 */

const BASE = 'http://localhost:5173';
const SCREENSHOT_DIR = path.resolve('e2e-screenshots');
const CLIENT_ID = '1'; // Demo Meble

const PAGES = [
    { name: 'dashboard',            path: '/',                    title: 'Pulpit' },
    { name: 'daily-audit',          path: '/daily-audit',         title: 'Poranny' },
    { name: 'campaigns',            path: '/campaigns',           title: 'Kampanie' },
    { name: 'keywords',             path: '/keywords',            title: 'Słowa' },
    { name: 'search-terms',         path: '/search-terms',        title: 'Wyszukiwane' },
    { name: 'recommendations',      path: '/recommendations',     title: 'Rekomendacje' },
    { name: 'action-history',       path: '/action-history',      title: 'Historia' },
    { name: 'alerts',               path: '/alerts',              title: 'Monitoring' },
    { name: 'agent',                path: '/agent',               title: 'Asystent' },
    { name: 'reports',              path: '/reports',             title: 'Raporty' },
    { name: 'audit-center',          path: '/audit-center',        title: 'Centrum' },
    { name: 'forecast',             path: '/forecast',            title: 'Prognoza' },
    { name: 'semantic',             path: '/semantic',            title: 'Inteligencja' },
    { name: 'quality-score',        path: '/quality-score',       title: 'Wynik' },
    { name: 'settings',             path: '/settings',            title: 'Ustawienia' },
];

test.describe('Visual Audit — all pages', () => {
    test.beforeEach(async ({ page }) => {
        await page.addInitScript((cid) => {
            localStorage.setItem('selectedClientId', cid);
        }, CLIENT_ID);
    });

    for (const pg of PAGES) {
        test(`${pg.name} — renders and matches baseline`, async ({ page }) => {
            const errors = [];
            page.on('pageerror', err => errors.push(err.message));

            await page.goto(`${BASE}${pg.path}`, { waitUntil: 'networkidle', timeout: 30000 });

            // Wait for loading spinners to disappear
            try {
                await page.waitForSelector('.animate-spin', { state: 'hidden', timeout: 10000 });
            } catch {
                // No spinner found or already gone
            }

            // Extra wait for async data
            await page.waitForTimeout(2000);

            // Manual screenshot for audit reports
            await page.screenshot({
                path: path.join(SCREENSHOT_DIR, `${pg.name}.png`),
                fullPage: true,
            });

            // Verify no JS errors
            expect(errors, `JS errors on ${pg.name}`).toEqual([]);

            // Verify page has meaningful content (not blank)
            const bodyText = await page.textContent('body');
            expect(bodyText.length, `${pg.name} body should have content`).toBeGreaterThan(50);

            // Visual regression — compare with baseline snapshot
            // First run creates baseline, subsequent runs compare (diff threshold 5%)
            await expect(page).toHaveScreenshot(`${pg.name}.png`, {
                fullPage: true,
                maxDiffPixelRatio: 0.05,
                threshold: 0.3,
            });
        });
    }
});
