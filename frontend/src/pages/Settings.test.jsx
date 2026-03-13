import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Settings from './Settings'

const mockApiPost = vi.fn()
const mockGetClient = vi.fn()
const mockUpdateClient = vi.fn()
const mockShowToast = vi.fn()
const mockRefreshClients = vi.fn()

vi.mock('../api', () => ({
    __esModule: true,
    default: {
        post: (...args) => mockApiPost(...args),
    },
    getClient: (...args) => mockGetClient(...args),
    updateClient: (...args) => mockUpdateClient(...args),
}))

vi.mock('../contexts/AppContext', () => ({
    useApp: () => ({
        selectedClientId: 1,
        showToast: mockShowToast,
        refreshClients: mockRefreshClients,
    }),
}))

function buildClient() {
    return {
        id: 1,
        name: 'Reset Client',
        industry: 'Food',
        website: 'https://example.com',
        google_customer_id: '123-456-7890',
        notes: '',
        target_audience: '',
        usp: '',
        competitors: [],
        business_rules: {},
    }
}

describe('Settings hard reset', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockGetClient.mockResolvedValue(buildClient())
        mockUpdateClient.mockResolvedValue(buildClient())
        mockApiPost.mockResolvedValue({
            success: true,
            message: "Dane lokalne klienta 'Reset Client' zostaly wyczyszczone.",
        })
    })

    it('keeps the hard reset button disabled until the exact client name is entered', async () => {
        render(<Settings />)

        expect(await screen.findByDisplayValue('Reset Client')).toBeInTheDocument()
        const resetButton = screen.getByRole('button', { name: 'Twardy reset danych klienta' })
        expect(resetButton).toBeDisabled()

        fireEvent.change(screen.getByPlaceholderText('Reset Client'), { target: { value: 'Reset' } })
        expect(resetButton).toBeDisabled()
    })

    it('calls the hard reset endpoint and refreshes client data after confirmation', async () => {
        render(<Settings />)

        expect(await screen.findByDisplayValue('Reset Client')).toBeInTheDocument()
        fireEvent.change(screen.getByPlaceholderText('Reset Client'), { target: { value: 'Reset Client' } })
        fireEvent.click(screen.getByRole('button', { name: 'Twardy reset danych klienta' }))

        await waitFor(() => {
            expect(mockApiPost).toHaveBeenCalledWith('/clients/1/hard-reset')
        })
        expect(mockRefreshClients).toHaveBeenCalled()
        expect(mockShowToast).toHaveBeenCalledWith(expect.stringContaining('wyczyszczone'), 'success')
        expect(mockGetClient).toHaveBeenCalledTimes(2)
    })
    it('shows a restart hint when the backend returns 404 for hard reset', async () => {
        mockApiPost.mockRejectedValueOnce({ message: 'Not Found', status: 404 })

        render(<Settings />)

        expect(await screen.findByDisplayValue('Reset Client')).toBeInTheDocument()
        fireEvent.change(screen.getByPlaceholderText('Reset Client'), { target: { value: 'Reset Client' } })
        fireEvent.click(screen.getByRole('button', { name: 'Twardy reset danych klienta' }))

        await waitFor(() => {
            expect(mockShowToast).toHaveBeenCalledWith(
                'Endpoint resetu nie jest dostepny. Zrestartuj backend lub cala aplikacje.',
                'error'
            )
        })
    })
})

