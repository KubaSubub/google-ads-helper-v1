import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

// We test the interceptors by importing the configured api instance
// and verifying behavior via axios adapter mocking

let api
let getAuthStatus

describe('api.js interceptors', () => {
    let dispatchSpy

    beforeEach(async () => {
        vi.resetModules()
        dispatchSpy = vi.spyOn(window, 'dispatchEvent')

        const mod = await import('./api')
        api = mod.default
        getAuthStatus = mod.getAuthStatus
    })

    afterEach(() => {
        dispatchSpy.mockRestore()
    })

    it('unwraps successful response to response.data', async () => {
        const adapter = vi.fn().mockResolvedValue({
            status: 200,
            data: { items: [1, 2, 3] },
            headers: {},
            config: {},
        })
        api.defaults.adapter = adapter

        const result = await api.get('/test')
        expect(result).toEqual({ items: [1, 2, 3] })
    })

    it('dispatches auth:unauthorized event on 401', async () => {
        const adapter = vi.fn().mockRejectedValue({
            response: { status: 401, data: { detail: 'Unauthorized' } },
            message: 'Request failed',
            config: { headers: {} },
        })
        api.defaults.adapter = adapter

        await expect(api.get('/protected')).rejects.toMatchObject({
            message: 'Unauthorized',
            status: 401,
        })

        expect(dispatchSpy).toHaveBeenCalledWith(expect.any(CustomEvent))
        const event = dispatchSpy.mock.calls.find(
            (call) => call[0].type === 'auth:unauthorized'
        )
        expect(event).toBeTruthy()
    })

    it('does NOT dispatch auth:unauthorized on 404', async () => {
        const adapter = vi.fn().mockRejectedValue({
            response: { status: 404, data: { detail: 'Not Found' } },
            message: 'Request failed',
            config: { headers: {} },
        })
        api.defaults.adapter = adapter

        await expect(api.get('/missing')).rejects.toMatchObject({
            message: 'Not Found',
            status: 404,
        })

        const authEvents = dispatchSpy.mock.calls.filter(
            (call) => call[0]?.type === 'auth:unauthorized'
        )
        expect(authEvents).toHaveLength(0)
    })

    it('uses error.response.data.detail as message', async () => {
        const adapter = vi.fn().mockRejectedValue({
            response: { status: 500, data: { detail: 'Blad serwera' } },
            message: 'Internal Server Error',
            config: { headers: {} },
        })
        api.defaults.adapter = adapter

        await expect(api.get('/fail')).rejects.toMatchObject({
            message: 'Blad serwera',
        })
    })

    it('falls back to error.message when no response', async () => {
        const adapter = vi.fn().mockRejectedValue({
            message: 'Network Error',
            config: { headers: {} },
        })
        api.defaults.adapter = adapter

        await expect(api.get('/timeout')).rejects.toMatchObject({
            message: 'Network Error',
            status: undefined,
        })
    })
})
