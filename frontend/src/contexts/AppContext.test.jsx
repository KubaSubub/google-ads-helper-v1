import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppProvider, useApp } from './AppContext'

const mockGetAuthStatus = vi.fn()
const mockGetClients = vi.fn()

vi.mock('../api', () => ({
    getAuthStatus: (...args) => mockGetAuthStatus(...args),
    getClients: (...args) => mockGetClients(...args),
}))

function renderApp() {
    return renderHook(() => useApp(), { wrapper: AppProvider })
}

describe('AppContext', () => {
    beforeEach(() => {
        vi.useFakeTimers({ shouldAdvanceTime: true })
        vi.clearAllMocks()
        localStorage.clear()
        mockGetAuthStatus.mockResolvedValue({
            authenticated: true,
            configured: true,
            ready: true,
            reason: '',
            missing: [],
            missing_credentials: [],
        })
        mockGetClients.mockResolvedValue({ items: [
            { id: 1, name: 'Client A' },
            { id: 2, name: 'Client B' },
        ] })
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    // --- initialization ---

    it('calls checkAuth on mount and sets authStatus', async () => {
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.isAuthenticated).toBe(true)
            expect(result.current.authStatus.ready).toBe(true)
            expect(result.current.authChecking).toBe(false)
        })
        expect(mockGetAuthStatus).toHaveBeenCalledWith(true)
    })

    // --- refreshClients normalization ---

    it('normalizes { items: [...] } response to array', async () => {
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.clients).toHaveLength(2)
            expect(result.current.clients[0].name).toBe('Client A')
        })
    })

    it('normalizes plain array response', async () => {
        mockGetClients.mockResolvedValue([{ id: 3, name: 'Direct' }])
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.clients).toHaveLength(1)
            expect(result.current.clients[0].name).toBe('Direct')
        })
    })

    it('returns empty array on getClients error', async () => {
        mockGetClients.mockRejectedValue(new Error('Network'))
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.clientsLoading).toBe(false)
            expect(result.current.clients).toEqual([])
        })
    })

    // --- checkAuth polling ---

    it('breaks polling on client error (status < 500)', async () => {
        mockGetAuthStatus.mockRejectedValue({ status: 401 })
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.authChecking).toBe(false)
            expect(result.current.isAuthenticated).toBe(false)
        })
        // Should have been called only once — broke immediately
        expect(mockGetAuthStatus).toHaveBeenCalledTimes(1)
    })

    // --- auth:unauthorized event ---

    it('resets state on auth:unauthorized event', async () => {
        const { result } = renderApp()

        await waitFor(() => {
            expect(result.current.isAuthenticated).toBe(true)
        })

        act(() => {
            window.dispatchEvent(new Event('auth:unauthorized'))
        })

        expect(result.current.isAuthenticated).toBe(false)
        expect(result.current.clients).toEqual([])
        expect(result.current.clientsLoading).toBe(false)
    })

    // --- showToast ---

    it('sets and auto-clears toast', async () => {
        const { result } = renderApp()

        await waitFor(() => expect(result.current.authChecking).toBe(false))

        act(() => result.current.showToast('Done', 'success', 1000))

        expect(result.current.toast).toMatchObject({
            message: 'Done',
            type: 'success',
        })

        act(() => vi.advanceTimersByTime(1100))

        expect(result.current.toast).toBeNull()
    })

    it('hideToast clears toast immediately', async () => {
        const { result } = renderApp()

        await waitFor(() => expect(result.current.authChecking).toBe(false))

        act(() => result.current.showToast('Msg'))
        expect(result.current.toast).not.toBeNull()

        act(() => result.current.hideToast())
        expect(result.current.toast).toBeNull()
    })

    // --- selectedClientId persistence ---

    it('persists selectedClientId to localStorage', async () => {
        const { result } = renderApp()

        await waitFor(() => expect(result.current.authChecking).toBe(false))

        act(() => result.current.setSelectedClientId(5))

        expect(localStorage.getItem('selectedClientId')).toBe('5')
    })

    it('restores selectedClientId from localStorage', async () => {
        localStorage.setItem('selectedClientId', '7')
        const { result } = renderApp()

        await waitFor(() => expect(result.current.authChecking).toBe(false))

        expect(result.current.selectedClientId).toBe(7)
    })

    // --- does not fetch clients when not ready ---

    it('does not call getClients when auth is not ready', async () => {
        mockGetAuthStatus.mockResolvedValue({
            authenticated: false,
            configured: false,
            ready: false,
            reason: 'missing config',
            missing: ['developer_token'],
            missing_credentials: [],
        })

        const { result } = renderApp()

        await waitFor(() => expect(result.current.authChecking).toBe(false))

        expect(mockGetClients).not.toHaveBeenCalled()
        expect(result.current.clients).toEqual([])
    })

    // --- useApp outside provider ---

    it('throws when used outside AppProvider', () => {
        expect(() => {
            renderHook(() => useApp())
        }).toThrow('useApp must be inside AppProvider')
    })
})
