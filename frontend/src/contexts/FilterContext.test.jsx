import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { FilterProvider, useFilter } from './FilterContext'

function renderFilter() {
    return renderHook(() => useFilter(), { wrapper: FilterProvider })
}

describe('FilterContext', () => {
    beforeEach(() => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-03-16'))
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    // --- defaults ---

    it('initializes with 30-day period and matching date range', () => {
        const { result } = renderFilter()

        expect(result.current.filters.period).toBe(30)
        expect(result.current.filters.campaignType).toBe('ALL')
        expect(result.current.filters.status).toBe('ALL')
        expect(result.current.filters.dateTo).toBe('2026-03-16')
        expect(result.current.filters.dateFrom).toBe('2026-02-14')
        expect(result.current.days).toBe(30)
    })

    // --- period changes auto-update dates ---

    it('updates dateFrom/dateTo when period changes to 7', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('period', 7))

        expect(result.current.filters.period).toBe(7)
        expect(result.current.filters.dateFrom).toBe('2026-03-09')
        expect(result.current.filters.dateTo).toBe('2026-03-16')
        expect(result.current.days).toBe(7)
    })

    it('updates dateFrom/dateTo when period changes to 90', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('period', 90))

        expect(result.current.filters.period).toBe(90)
        expect(result.current.filters.dateFrom).toBe('2025-12-16')
        expect(result.current.filters.dateTo).toBe('2026-03-16')
        expect(result.current.days).toBe(90)
    })

    // --- manual date clears period ---

    it('clears period when dateFrom is set manually', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('dateFrom', '2026-01-01'))

        expect(result.current.filters.period).toBeNull()
        expect(result.current.filters.dateFrom).toBe('2026-01-01')
    })

    it('clears period when dateTo is set manually', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('dateTo', '2026-02-01'))

        expect(result.current.filters.period).toBeNull()
        expect(result.current.filters.dateTo).toBe('2026-02-01')
    })

    // --- days computed value ---

    it('computes days from custom date range when period is null', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('dateFrom', '2026-03-01'))
        // period is now null, dateTo remains 2026-03-16 => 15 days

        expect(result.current.filters.period).toBeNull()
        expect(result.current.days).toBe(15)
    })

    it('returns minimum 1 day when dateFrom equals dateTo', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('dateFrom', '2026-03-16'))
        // dateFrom = dateTo = 2026-03-16 => 0 diff, clamped to 1

        expect(result.current.days).toBe(1)
    })

    // --- non-date filters ---

    it('sets campaignType without affecting dates or period', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('campaignType', 'SEARCH'))

        expect(result.current.filters.campaignType).toBe('SEARCH')
        expect(result.current.filters.period).toBe(30)
    })

    it('sets status without affecting dates or period', () => {
        const { result } = renderFilter()

        act(() => result.current.setFilter('status', 'ENABLED'))

        expect(result.current.filters.status).toBe('ENABLED')
        expect(result.current.filters.period).toBe(30)
    })

    // --- resetFilters ---

    it('resets all filters to defaults', () => {
        const { result } = renderFilter()

        act(() => {
            result.current.setFilter('campaignType', 'SEARCH')
            result.current.setFilter('dateFrom', '2026-01-01')
        })

        act(() => result.current.resetFilters())

        expect(result.current.filters.campaignType).toBe('ALL')
        expect(result.current.filters.period).toBe(30)
        expect(result.current.filters.dateFrom).toBe('2026-02-14')
    })

    // --- useFilter outside provider ---

    it('throws when used outside FilterProvider', () => {
        expect(() => {
            renderHook(() => useFilter())
        }).toThrow('useFilter must be inside FilterProvider')
    })
})
