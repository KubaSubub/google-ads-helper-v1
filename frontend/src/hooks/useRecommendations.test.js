import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGetRecommendations = vi.fn()
const mockGetRecommendationsSummary = vi.fn()
const mockApplyRecommendation = vi.fn()
const mockDismissRecommendation = vi.fn()

vi.mock('../api', () => ({
    getRecommendations: (...args) => mockGetRecommendations(...args),
    getRecommendationsSummary: (...args) => mockGetRecommendationsSummary(...args),
    applyRecommendation: (...args) => mockApplyRecommendation(...args),
    dismissRecommendation: (...args) => mockDismissRecommendation(...args),
}))

import { useRecommendations } from './useRecommendations'

const MOCK_RECS = {
    recommendations: [
        { id: 1, type: 'IS_BUDGET_ALERT', priority: 'HIGH' },
        { id: 2, type: 'REALLOCATE_BUDGET', priority: 'MEDIUM' },
    ],
}
const MOCK_SUMMARY = { total: 2, high_priority: 1, medium: 1 }

describe('useRecommendations', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockGetRecommendations.mockResolvedValue(MOCK_RECS)
        mockGetRecommendationsSummary.mockResolvedValue(MOCK_SUMMARY)
        mockApplyRecommendation.mockResolvedValue({ success: true })
        mockDismissRecommendation.mockResolvedValue({})
    })

    it('fetches recommendations on mount with default params', async () => {
        const { result } = renderHook(() => useRecommendations(1))

        await waitFor(() => {
            expect(result.current.loading).toBe(false)
        })

        expect(mockGetRecommendations).toHaveBeenCalledWith(1, { status: 'pending' })
        expect(mockGetRecommendationsSummary).toHaveBeenCalledWith(1, { status: 'pending' })
        expect(result.current.recommendations).toHaveLength(2)
        expect(result.current.summary.total).toBe(2)
    })

    it('does not fetch when clientId is null', async () => {
        const { result } = renderHook(() => useRecommendations(null))

        // Give it a tick
        await new Promise((r) => setTimeout(r, 50))

        expect(mockGetRecommendations).not.toHaveBeenCalled()
        expect(result.current.recommendations).toEqual([])
    })

    it('updateFilters merges with previous params and refetches', async () => {
        const { result } = renderHook(() => useRecommendations(1))

        await waitFor(() => expect(result.current.loading).toBe(false))
        mockGetRecommendations.mockClear()
        mockGetRecommendationsSummary.mockClear()

        act(() => result.current.updateFilters({ priority: 'HIGH' }))

        await waitFor(() => {
            expect(mockGetRecommendations).toHaveBeenCalledWith(
                1,
                expect.objectContaining({ status: 'pending', priority: 'HIGH' })
            )
        })
    })

    it('apply calls applyRecommendation with correct args', async () => {
        const { result } = renderHook(() => useRecommendations(1))

        await waitFor(() => expect(result.current.loading).toBe(false))

        const response = await result.current.apply(42, true)

        expect(mockApplyRecommendation).toHaveBeenCalledWith(42, 1, true)
        expect(response).toEqual({ success: true })
    })

    it('dismiss calls dismissRecommendation and refetches', async () => {
        const { result } = renderHook(() => useRecommendations(1))

        await waitFor(() => expect(result.current.loading).toBe(false))
        mockGetRecommendations.mockClear()

        await act(async () => {
            await result.current.dismiss(7)
        })

        expect(mockDismissRecommendation).toHaveBeenCalledWith(7, 1)
        // Should refetch after dismiss
        expect(mockGetRecommendations).toHaveBeenCalled()
    })

    it('handles fetch error gracefully', async () => {
        mockGetRecommendations.mockRejectedValueOnce(new Error('Network'))

        const { result } = renderHook(() => useRecommendations(1))

        await waitFor(() => expect(result.current.loading).toBe(false))

        // Should not crash, recommendations stay empty
        expect(result.current.recommendations).toEqual([])
    })
})
