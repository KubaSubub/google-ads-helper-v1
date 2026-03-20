/**
 * Shared helpers for Playwright E2E tests.
 *
 * mockAuthAndClient() intercepts all /api calls needed for the app to boot
 * past the Login screen and render the authenticated shell with a DEMO client.
 */

/** Minimal mock data for a DEMO client */
const DEMO_CLIENT = {
    id: 3,
    name: 'Sushi Naka Naka',
    google_customer_id: '123-456-7890',
    is_demo: true,
    status: 'ACTIVE',
};

/** Mock auth + client API responses so the app renders the main layout. */
export async function mockAuthAndClient(page) {
    // Auth status — ready
    await page.route('**/api/v1/auth/status*', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                authenticated: true,
                configured: true,
                ready: true,
                reason: '',
                missing: [],
                missing_credentials: [],
            }),
        }),
    );

    // Client list
    await page.route('**/api/v1/clients/*', (route) => {
        if (route.request().method() === 'GET') {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ items: [DEMO_CLIENT], total: 1 }),
            });
        }
        return route.fallback();
    });

    await page.route('**/api/v1/clients/', (route) => {
        if (route.request().method() === 'GET') {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ items: [DEMO_CLIENT], total: 1 }),
            });
        }
        return route.fallback();
    });
}

/** Catch-all: return empty arrays/objects for unhandled API calls so pages don't break. */
export async function mockEmptyApi(page) {
    await page.route('**/api/v1/**', (route) => {
        const url = route.request().url();

        // SSE endpoints — let them fail gracefully
        if (url.includes('/agent/') || url.includes('/reports/generate')) {
            return route.abort();
        }

        // Campaigns endpoint — some pages expect {items: []}
        if (url.includes('/campaigns')) {
            return route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ items: [], total: 0 }),
            });
        }

        return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ items: [], total: 0, data: [], alerts: [] }),
        });
    });
}

export { DEMO_CLIENT };
