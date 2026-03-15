import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Keywords from './Keywords'

const mockGetKeywords = vi.fn()
const mockShowToast = vi.fn()

vi.mock('../api', () => ({
    getKeywords: (...args) => mockGetKeywords(...args),
}))

vi.mock('../contexts/AppContext', () => ({
    useApp: () => ({
        selectedClientId: 1,
        showToast: mockShowToast,
    }),
}))

vi.mock('../contexts/FilterContext', () => ({
    useFilter: () => ({
        filters: {
            campaignType: 'ALL',
            status: 'ALL',
            dateFrom: '2026-02-01',
            dateTo: '2026-03-01',
        },
        setFilter: vi.fn(),
    }),
}))

vi.mock('../components/MetricTooltip', () => ({
    MetricTooltip: ({ children }) => <>{children}</>,
}))

function buildKeyword(overrides = {}) {
    return {
        id: 1,
        ad_group_id: 11,
        campaign_id: 101,
        campaign_name: 'Kampania testowa',
        ad_group_name: 'Grupa reklam A',
        google_keyword_id: 'kw-1',
        text: 'active keyword',
        match_type: 'EXACT',
        status: 'ENABLED',
        serving_status: 'LOW_SEARCH_VOLUME',
        clicks: 50,
        impressions: 500,
        cost: 80,
        conversions: 6,
        ctr: 10,
        avg_cpc: 1.6,
        quality_score: 7,
        roas: 3.4,
        search_impression_share: 0.52,
        ...overrides,
    }
}

function renderPage() {
    return render(
        <MemoryRouter initialEntries={['/keywords']}>
            <Keywords />
        </MemoryRouter>
    )
}

describe('Keywords page', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockGetKeywords.mockImplementation(async (params) => {
            const enabledKeyword = buildKeyword()
            const removedKeyword = buildKeyword({
                id: 2,
                google_keyword_id: 'kw-2',
                text: 'removed keyword',
                status: 'REMOVED',
                serving_status: null,
                conversions: 0,
                clicks: 5,
                cost: 10,
            })

            if (params.include_removed) {
                return {
                    items: [enabledKeyword, removedKeyword],
                    total: 2,
                    page: 1,
                    page_size: 50,
                    total_pages: 1,
                }
            }

            return {
                items: [enabledKeyword],
                total: 1,
                page: 1,
                page_size: 50,
                total_pages: 1,
            }
        })
    })

    it('renders campaign context, real keyword status, serving badge, and readable action tooltip', async () => {
        renderPage()

        expect(await screen.findByText('active keyword')).toBeInTheDocument()
        expect(mockGetKeywords).toHaveBeenCalledWith(expect.objectContaining({
            client_id: 1,
            include_removed: false,
        }))
        expect(screen.getByText('Kampania testowa')).toBeInTheDocument()
        expect(screen.getByText('Grupa reklam A')).toBeInTheDocument()
        expect(screen.getByText('Aktywna')).toBeInTheDocument()
        expect(screen.getByText('Malo zapytan')).toBeInTheDocument()

        const actionButton = screen.getByRole('button', { name: 'Podnies' })
        expect(actionButton).toHaveAttribute('title', expect.stringContaining('wspolczynnik konwersji'))
        expect(screen.queryByText('removed keyword')).not.toBeInTheDocument()
    })

    it('shows removed keywords only after enabling the local toggle', async () => {
        renderPage()

        expect(await screen.findByText('active keyword')).toBeInTheDocument()
        fireEvent.click(screen.getByRole('checkbox', { name: /Pokaz usuniete/i }))

        expect(await screen.findByText('removed keyword')).toBeInTheDocument()
        await waitFor(() => {
            expect(mockGetKeywords).toHaveBeenLastCalledWith(expect.objectContaining({
                client_id: 1,
                include_removed: true,
            }))
        })
        expect(screen.getByText(/Usuni/)).toBeInTheDocument()
    })
})
