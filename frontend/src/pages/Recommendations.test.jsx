import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FilterProvider } from '../contexts/FilterContext'
import Recommendations from './Recommendations'

const mockShowToast = vi.fn()
const mockUpdateFilters = vi.fn()
const mockRefetch = vi.fn()
const mockApply = vi.fn()
const mockDismiss = vi.fn()
const mockUseRecommendations = vi.fn()

vi.mock('../contexts/AppContext', () => ({
    useApp: () => ({
        selectedClientId: 1,
        showToast: mockShowToast,
    }),
}))

vi.mock('../hooks/useRecommendations', () => ({
    useRecommendations: (...args) => mockUseRecommendations(...args),
}))

function buildRecommendation(overrides = {}) {
    return {
        id: 1,
        type: 'IS_BUDGET_ALERT',
        priority: 'HIGH',
        entity_type: 'campaign',
        entity_id: 101,
        entity_name: 'Generic Search Scale',
        campaign_name: 'Generic Search Scale',
        reason: 'Budget-lost impression share shows safe scale headroom.',
        recommended_action: 'Increase budget by 20%',
        estimated_impact: 'Potentially recover 35% more impressions',
        source: 'PLAYBOOK_RULES',
        executable: true,
        confidence_score: 0.81,
        risk_score: 0.21,
        expires_at: '2026-03-20T10:00:00Z',
        context_outcome: 'ACTION',
        action_payload: {
            action_type: 'INCREASE_BUDGET',
            executable: true,
        },
        metadata: {
            lost_is_pct: 35,
            roas: 4.0,
        },
        context: {
            primary_campaign_role: 'GENERIC',
            protection_level: 'LOW',
            can_scale: true,
            destination_headroom: true,
        },
        why_allowed: [{ code: 'HEALTHY_BUDGET_HEADROOM' }],
        why_blocked: [],
        tradeoffs: [{ code: 'MORE_SPEND_WITHOUT_GUARANTEED_INCREMENTALITY' }],
        risk_note: { code: 'MONITOR_BUDGET_AFTER_CHANGE' },
        next_best_action: { code: 'MONITOR_BUDGET_AFTER_CHANGE' },
        blocked_reasons: [],
        downgrade_reasons: [],
        ...overrides,
    }
}

describe('Recommendations page', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockUseRecommendations.mockReturnValue({
            recommendations: [
                buildRecommendation(),
                buildRecommendation({
                    id: 2,
                    type: 'REALLOCATE_BUDGET',
                    entity_id: 102,
                    entity_name: 'Budget Review',
                    campaign_name: 'Remarketing -> Prospecting',
                    reason: 'Budget move needs more context.',
                    recommended_action: 'Review bids before scaling budget',
                    estimated_impact: 'Insight only until context confirms safe scale',
                    executable: false,
                    context_outcome: 'INSIGHT_ONLY',
                    action_payload: {
                        action_type: 'REALLOCATE_BUDGET',
                        executable: false,
                    },
                    context: {
                        primary_campaign_role: 'PROSPECTING',
                        counterparty_campaign_role: 'PROSPECTING',
                        protection_level: 'LOW',
                        donor_protection_level: 'MEDIUM',
                        can_scale: false,
                        comparable: true,
                        destination_headroom: false,
                    },
                    why_allowed: [],
                    why_blocked: [{ code: 'ROAS_ONLY_SIGNAL' }],
                    tradeoffs: [{ code: 'BUDGET_SHIFT_REDUCES_DONOR_COVERAGE' }],
                    risk_note: { code: 'MANUAL_REVIEW_REQUIRED' },
                    next_best_action: { code: 'REVIEW_BIDS_FIRST' },
                    blocked_reasons: [],
                    downgrade_reasons: ['ROAS_ONLY_SIGNAL'],
                }),
                buildRecommendation({
                    id: 3,
                    type: 'REALLOCATE_BUDGET',
                    entity_id: 103,
                    entity_name: 'Blocked Transfer',
                    campaign_name: 'PMax -> Brand',
                    reason: 'Brand and PMax are not comparable for transfer.',
                    recommended_action: 'Review campaign role override first',
                    estimated_impact: 'Context blocked',
                    executable: false,
                    context_outcome: 'BLOCKED_BY_CONTEXT',
                    action_payload: {
                        action_type: 'REALLOCATE_BUDGET',
                        executable: false,
                    },
                    context: {
                        primary_campaign_role: 'BRAND',
                        counterparty_campaign_role: 'PMAX',
                        protection_level: 'HIGH',
                        donor_protection_level: 'MEDIUM',
                        can_scale: false,
                        comparable: false,
                        destination_headroom: false,
                    },
                    why_allowed: [],
                    why_blocked: [{ code: 'ROLE_MISMATCH' }],
                    tradeoffs: [{ code: 'BUDGET_SHIFT_REDUCES_DONOR_COVERAGE' }],
                    risk_note: { code: 'MANUAL_REVIEW_REQUIRED' },
                    next_best_action: { code: 'SET_ROLE_OVERRIDE' },
                    blocked_reasons: ['ROLE_MISMATCH'],
                    downgrade_reasons: [],
                }),
            ],
            summary: {
                total: 3,
                executable_total: 1,
                high_priority: 1,
                by_context_outcome: {
                    ACTION: 1,
                    INSIGHT_ONLY: 1,
                    BLOCKED_BY_CONTEXT: 1,
                },
            },
            loading: false,
            updateFilters: mockUpdateFilters,
            refetch: mockRefetch,
            apply: mockApply,
            dismiss: mockDismiss,
        })
    })

    it('renders context outcomes, grouped sections, and explanation copy from reason codes', () => {
        render(<FilterProvider><Recommendations /></FilterProvider>)

        expect(screen.getByRole('heading', { name: 'Executable' })).toBeInTheDocument()
        expect(screen.getByRole('heading', { name: 'Alerts' })).toBeInTheDocument()
        expect(screen.getByText('The campaign is budget-constrained and still looks healthy.')).toBeInTheDocument()
        expect(screen.getByText('More spend does not guarantee incremental conversions.')).toBeInTheDocument()
        expect(screen.getByText('Campaign roles are not comparable for budget transfer.')).toBeInTheDocument()
        expect(screen.getByText('Set the correct campaign role override if classification is wrong.')).toBeInTheDocument()
        expect(screen.getByText('The signal relies mainly on ROAS without stronger scale confirmation.')).toBeInTheDocument()
        expect(screen.getByText('Review bids or conversion quality before scaling budget.')).toBeInTheDocument()
        expect(screen.getByText('Brand')).toBeInTheDocument()
        expect(screen.getByText('PMax')).toBeInTheDocument()
    })

    it('keeps apply active only for executable cards and disables manual review cards', () => {
        render(<FilterProvider><Recommendations /></FilterProvider>)

        expect(screen.getByRole('button', { name: /zastosuj/i })).toBeEnabled()
        const manualReviewButtons = screen.getAllByRole('button', { name: /ręczna weryfikacja/i })
        expect(manualReviewButtons).toHaveLength(2)
        manualReviewButtons.forEach(button => expect(button).toBeDisabled())
    })

    it('initializes recommendation filters with pending status and current UI selections', () => {
        render(<FilterProvider><Recommendations /></FilterProvider>)

        expect(mockUpdateFilters).toHaveBeenCalledWith({
            status: 'pending',
            priority: undefined,
            source: undefined,
            executable: undefined,
        })
    })
})
