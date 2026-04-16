/**
 * Canonical filter params builder — for imperative calls (e.g. inside event handlers)
 * where a hook isn't appropriate. Produces the same shape as `useFilteredQuery`
 * injects internally.
 *
 * Usage:
 *   const params = buildFilterParams({ allParams, selectedClientId, overrides: { page: 1 } })
 *   await api.get('/campaigns/', { params })
 */
export function buildFilterParams({ allParams, selectedClientId, overrides = {} }) {
    return {
        client_id: selectedClientId,
        ...(allParams || {}),
        ...overrides,
    }
}
