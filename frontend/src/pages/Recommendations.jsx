import { useEffect, useMemo, useState } from 'react'
import {
    CheckCircle2,
    Download,
    Loader2,
    Play,
    RefreshCw,
    ShieldAlert,
    TrendingDown,
    TrendingUp,
    XCircle,
    Zap,
} from 'lucide-react'

import ConfirmationModal from '../components/ConfirmationModal'
import EmptyState from '../components/EmptyState'
import { LoadingSpinner } from '../components/UI'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import { useRecommendations } from '../hooks/useRecommendations'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const TYPE_CONFIG = {
    PAUSE_KEYWORD: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Wstrzymaj słowo' },
    UPDATE_BID: { icon: TrendingUp, color: C.success, bg: C.successBg, label: 'Zmień stawkę' },
    ADD_KEYWORD: { icon: TrendingUp, color: C.accentBlue, bg: C.infoBg, label: 'Dodaj słowo' },
    ADD_NEGATIVE: { icon: TrendingDown, color: C.danger, bg: C.dangerBg, label: 'Dodaj wykluczenie' },
    PAUSE_AD: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Wstrzymaj reklamę' },
    INCREASE_BUDGET: { icon: TrendingUp, color: C.success, bg: C.successBg, label: 'Zwiększ budżet' },
    REALLOCATE_BUDGET: { icon: Zap, color: C.warning, bg: C.warningBg, label: 'Przesuń budżet' },
    // v1.1 rules (R8-R13)
    QS_ALERT: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Quality Score' },
    IS_BUDGET_ALERT: { icon: TrendingUp, color: C.accentBlue, bg: C.infoBg, label: 'Impression Share — Budżet' },
    IS_RANK_ALERT: { icon: TrendingDown, color: C.warning, bg: C.warningBg, label: 'Impression Share — Ad Rank' },
    LOW_CTR_KEYWORD: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Niski CTR' },
    WASTED_SPEND_ALERT: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Przepalony Budżet' },
    PMAX_CANNIBALIZATION: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'PMax Kanibalizacja' },
    // v1.2 rules (R15-R18)
    DEVICE_ANOMALY: { icon: TrendingDown, color: C.warning, bg: C.warningBg, label: 'Anomalia Urządzeń' },
    GEO_ANOMALY: { icon: TrendingDown, color: C.warning, bg: C.warningBg, label: 'Anomalia Lokalizacji' },
    BUDGET_PACING: { icon: Zap, color: C.warning, bg: C.warningBg, label: 'Tempo Budżetu' },
    NGRAM_NEGATIVE: { icon: TrendingDown, color: C.danger, bg: C.dangerBg, label: 'N-gram do Wykluczenia' },
    // v2.0 GAP rules
    AD_GROUP_HEALTH: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Zdrowie grupy reklam' },
    SINGLE_AD_ALERT: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Tylko 1 reklama' },
    OVERSIZED_AD_GROUP: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Za dużo keywords' },
    ZERO_CONV_AD_GROUP: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Brak konwersji w grupie' },
    DISAPPROVED_AD_ALERT: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Odrzucona reklama' },
    SMART_BIDDING_DATA_STARVATION: { icon: Zap, color: C.danger, bg: C.dangerBg, label: 'Smart Bidding — niski wolumen' },
    ECPC_DEPRECATION: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'ECPC wycofane' },
    SCALING_OPPORTUNITY: { icon: TrendingUp, color: C.success, bg: C.successBg, label: 'Okazja do skalowania' },
    // v2.0 GAP rules (Phase B+C)
    TARGET_DEVIATION_ALERT: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Odchylenie od celu' },
    LEARNING_PERIOD_ALERT: { icon: Zap, color: C.warning, bg: C.warningBg, label: 'Okres nauki' },
    CONVERSION_QUALITY_ALERT: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Jakość konwersji' },
    DEMOGRAPHIC_ANOMALY: { icon: TrendingDown, color: C.warning, bg: C.warningBg, label: 'Anomalia demograficzna' },
    // v2.1 Phase D (R28-R31)
    PMAX_CHANNEL_IMBALANCE: { icon: Zap, color: C.warning, bg: C.warningBg, label: 'Nierównowaga kanałów PMax' },
    ASSET_GROUP_AD_STRENGTH: { icon: ShieldAlert, color: C.danger, bg: C.dangerBg, label: 'Siła reklam grupy zasobów' },
    AUDIENCE_PERFORMANCE_ANOMALY: { icon: TrendingDown, color: C.danger, bg: C.dangerBg, label: 'Anomalia odbiorców' },
    MISSING_EXTENSIONS_ALERT: { icon: ShieldAlert, color: C.warning, bg: C.warningBg, label: 'Brakujące rozszerzenia' },
}

const PRIORITY_CONFIG = {
    HIGH: { color: C.danger, bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.25)', label: 'HIGH' },
    MEDIUM: { color: C.warning, bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.25)', label: 'MEDIUM' },
    LOW: { color: C.textPlaceholder, bg: C.w06, border: C.w12, label: 'LOW' },
}

const SOURCE_LABELS = {
    PLAYBOOK_RULES: 'Playbook',
    GOOGLE_ADS_API: 'Google Ads',
    HYBRID: 'Hybrid',
    ANALYTICS: 'Analytics',
}

const ENTITY_TYPE_LABELS = {
    keyword: 'Keyword',
    search_term: 'Search term',
    ad: 'Ad',
    ad_group: 'Ad Group',
    campaign: 'Campaign',
    segment: 'Segment',
    client: 'Konto',
}

const CAMPAIGN_ROLE_LABELS = {
    BRAND: 'Brand',
    GENERIC: 'Generic',
    PROSPECTING: 'Prospecting',
    REMARKETING: 'Remarketing',
    PMAX: 'PMax',
    LOCAL: 'Local',
    UNKNOWN: 'Unknown',
}

const OUTCOME_CONFIG = {
    ACTION: { label: 'Action', color: C.success, bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.25)' },
    INSIGHT_ONLY: { label: 'Insight only', color: C.warning, bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.25)' },
    BLOCKED_BY_CONTEXT: { label: 'Blocked', color: C.danger, bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.25)' },
}

const REASON_COPY = {
    ROLE_MISMATCH: 'Campaign roles are not comparable for budget transfer.',
    DONOR_PROTECTED_HIGH: 'Donor campaign is protected at a high level.',
    DONOR_PROTECTED_MEDIUM: 'Donor campaign is medium-protected, so this stays insight-only.',
    DESTINATION_NO_HEADROOM: 'Destination campaign does not show enough budget headroom.',
    ROAS_ONLY_SIGNAL: 'The signal relies mainly on ROAS without stronger scale confirmation.',
    UNKNOWN_ROLE: 'At least one campaign role is still unknown.',
    INSUFFICIENT_DATA: 'There is not enough stable data to support an action.',
    SAME_ROLE_COMPARISON: 'Both campaigns have the same role, so comparison is allowed.',
    DESTINATION_HAS_HEADROOM: 'Destination campaign still has room to scale.',
    DONOR_LOW_PROTECTION: 'Donor campaign is not protected by context rules.',
    HEALTHY_BUDGET_HEADROOM: 'The campaign is budget-constrained and still looks healthy.',
    BUDGET_SHIFT_REDUCES_DONOR_COVERAGE: 'Moving budget can reduce donor coverage or future demand capture.',
    MORE_SPEND_WITHOUT_GUARANTEED_INCREMENTALITY: 'More spend does not guarantee incremental conversions.',
    MANUAL_REVIEW_REQUIRED: 'Manual review is required before making this budget change.',
    MONITOR_AFTER_REALLOCATION: 'Monitor both campaigns after the budget move.',
    MONITOR_BUDGET_AFTER_CHANGE: 'Monitor impression share and efficiency after the budget change.',
    REVIEW_CONTEXT_BEFORE_SCALING: 'Review context before increasing spend.',
    MANUAL_BUDGET_REVIEW: 'Review campaign roles, headroom, and business goals first.',
    SET_ROLE_OVERRIDE: 'Set the correct campaign role override if classification is wrong.',
    REVIEW_BIDS_FIRST: 'Review bids or conversion quality before scaling budget.',
}

function humanizeCode(code) {
    if (!code) return 'Unknown'
    return String(code)
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, char => char.toUpperCase())
}

function describeCode(code) {
    return REASON_COPY[code] || humanizeCode(code)
}

function normalizeReasonEntries(entries) {
    if (!Array.isArray(entries)) return []
    return entries
        .map(entry => (typeof entry === 'string' ? { code: entry } : entry))
        .filter(entry => entry && entry.code)
}

function mergeReasonEntries(...groups) {
    const seen = new Set()
    return groups
        .flatMap(group => normalizeReasonEntries(group))
        .filter(entry => {
            if (seen.has(entry.code)) return false
            seen.add(entry.code)
            return true
        })
}

function formatImpact(rec) {
    if (rec.estimated_impact) return rec.estimated_impact
    if (!rec.impact_micros) return null
    return `Impact ~ ${(rec.impact_micros / 1_000_000).toFixed(2)}`
}

function formatExpires(value) {
    if (!value) return 'No expiry'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'No expiry'
    return date.toLocaleString('pl-PL')
}

function MetricPills({ metadata }) {
    if (!metadata || Object.keys(metadata).length === 0) return null

    const pills = []
    if (metadata.spend != null) pills.push({ label: 'Spend', value: Number(metadata.spend).toFixed(2) })
    if (metadata.cost != null && metadata.spend == null) pills.push({ label: 'Cost', value: Number(metadata.cost).toFixed(2) })
    if (metadata.clicks != null) pills.push({ label: 'Clicks', value: metadata.clicks })
    if (metadata.impressions != null) pills.push({ label: 'Impr', value: Number(metadata.impressions).toLocaleString('pl-PL') })
    if (metadata.conversions != null) pills.push({ label: 'Conv', value: Number(metadata.conversions).toFixed(1) })
    if (metadata.ctr != null) pills.push({ label: 'CTR', value: `${Number(metadata.ctr).toFixed(2)}%` })
    if (metadata.cvr != null) {
        const cvr = Number(metadata.cvr)
        pills.push({
            label: 'CVR',
            value: `${cvr.toFixed(1)}%`,
            title: cvr > 100 ? 'CVR > 100% often means modeled or duplicated conversions.' : undefined,
        })
    }
    if (metadata.match_type) pills.push({ label: 'Match', value: metadata.match_type })
    if (metadata.negative_level) pills.push({ label: 'Level', value: metadata.negative_level })

    if (!pills.length) return null

    return (
        <div className="flex items-center gap-1.5 flex-wrap" style={{ marginBottom: 10 }}>
            {pills.map((pill, index) => (
                <span
                    key={`${pill.label}-${index}`}
                    title={pill.title}
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: 10,
                        padding: '2px 7px',
                        borderRadius: 6,
                        background: C.w04,
                        border: `1px solid ${C.w08}`,
                        color: C.w60,
                    }}
                >
                    <span style={{ color: C.w30 }}>{pill.label}:</span>
                    <span style={{ fontWeight: 600, fontFamily: 'monospace', color: C.textPrimary }}>{pill.value}</span>
                </span>
            ))}
        </div>
    )
}

function PriorityPill({ priority }) {
    const cfg = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.LOW
    return (
        <span
            style={{
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 999,
                background: cfg.bg,
                color: cfg.color,
                border: `1px solid ${cfg.border}`,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
            }}
        >
            {cfg.label}
        </span>
    )
}

function TypePill({ actionType }) {
    const cfg = TYPE_CONFIG[actionType] || { icon: Zap, color: C.textPlaceholder, bg: C.w06, label: humanizeCode(actionType || 'REVIEW') }
    const Icon = cfg.icon
    return (
        <span
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 10,
                fontWeight: 500,
                padding: '2px 8px 2px 6px',
                borderRadius: 999,
                background: cfg.bg,
                color: cfg.color,
            }}
        >
            <Icon size={10} />
            {cfg.label}
        </span>
    )
}

function OutcomePill({ outcome }) {
    const cfg = OUTCOME_CONFIG[outcome] || OUTCOME_CONFIG.INSIGHT_ONLY
    return (
        <span
            style={{
                fontSize: 10,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 999,
                background: cfg.bg,
                color: cfg.color,
                border: `1px solid ${cfg.border}`,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
            }}
        >
            {cfg.label}
        </span>
    )
}

function ExplanationList({ title, items, color = 'rgba(255,255,255,0.72)' }) {
    if (!items.length) return null
    return (
        <div>
            <div style={{ fontSize: 10, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                {title}
            </div>
            <div style={{ display: 'grid', gap: 4 }}>
                {items.map((item, index) => (
                    <div key={`${item.code}-${index}`} style={{ fontSize: 11, color, lineHeight: 1.45 }}>
                        {describeCode(item.code)}
                    </div>
                ))}
            </div>
        </div>
    )
}

function ContextPanel({ rec }) {
    const context = rec.context || {}
    const chips = []

    if (context.primary_campaign_role) {
        chips.push({ label: 'Primary role', value: CAMPAIGN_ROLE_LABELS[context.primary_campaign_role] || context.primary_campaign_role })
    }
    if (context.counterparty_campaign_role) {
        chips.push({ label: 'Counterparty role', value: CAMPAIGN_ROLE_LABELS[context.counterparty_campaign_role] || context.counterparty_campaign_role })
    }
    if (context.protection_level) {
        chips.push({ label: 'Protection', value: context.protection_level })
    }
    if (context.donor_protection_level) {
        chips.push({ label: 'Donor protection', value: context.donor_protection_level })
    }
    if (context.comparable !== undefined) {
        chips.push({ label: 'Comparable', value: context.comparable ? 'Yes' : 'No' })
    }
    if (context.can_scale !== undefined) {
        chips.push({ label: 'Can scale', value: context.can_scale ? 'Yes' : 'No' })
    }
    if (context.destination_headroom !== undefined) {
        chips.push({ label: 'Headroom', value: context.destination_headroom ? 'Yes' : 'No' })
    }

    if (!chips.length) return null

    return (
        <div className="flex items-center gap-1.5 flex-wrap" style={{ marginBottom: 10 }}>
            {chips.map((chip, index) => (
                <span
                    key={`${chip.label}-${index}`}
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: 10,
                        padding: '2px 7px',
                        borderRadius: 6,
                        background: C.w04,
                        border: `1px solid ${C.w08}`,
                        color: C.w60,
                    }}
                >
                    <span style={{ color: C.w30 }}>{chip.label}:</span>
                    <span style={{ fontWeight: 600, color: C.textPrimary }}>{chip.value}</span>
                </span>
            ))}
        </div>
    )
}

function ExplanationPanel({ rec }) {
    const whyAllowed = mergeReasonEntries(rec.why_allowed)
    const whyBlocked = mergeReasonEntries(rec.why_blocked, rec.blocked_reasons, rec.downgrade_reasons)
    const tradeoffs = mergeReasonEntries(rec.tradeoffs)
    const riskNote = rec.risk_note?.code ? describeCode(rec.risk_note.code) : null
    const nextBestAction = rec.next_best_action?.code ? describeCode(rec.next_best_action.code) : null

    if (!whyAllowed.length && !whyBlocked.length && !tradeoffs.length && !riskNote && !nextBestAction) {
        return null
    }

    return (
        <div
            style={{
                display: 'grid',
                gap: 8,
                padding: '10px 12px',
                borderRadius: 10,
                background: C.w03,
                border: `1px solid ${C.w08}`,
                marginBottom: 12,
            }}
        >
            <ExplanationList title="Allowed because" items={whyAllowed} color="#4ADE80" />
            <ExplanationList title={rec.context_outcome === 'ACTION' ? 'Context checks' : 'Blocked or downgraded because'} items={whyBlocked} color={rec.context_outcome === 'BLOCKED_BY_CONTEXT' ? C.danger : C.warning} />
            <ExplanationList title="Trade-offs" items={tradeoffs} />
            {riskNote && (
                <div>
                    <div style={{ fontSize: 10, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                        Risk note
                    </div>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.72)', lineHeight: 1.45 }}>{riskNote}</div>
                </div>
            )}
            {nextBestAction && (
                <div>
                    <div style={{ fontSize: 10, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                        Next best action
                    </div>
                    <div style={{ fontSize: 11, color: C.textPrimary, lineHeight: 1.45 }}>{nextBestAction}</div>
                </div>
            )}
        </div>
    )
}

function MetaRow({ rec }) {
    return (
        <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 10 }}>
            <OutcomePill outcome={rec.context_outcome} />
            <span style={{ fontSize: 10, color: C.textMuted }}>{SOURCE_LABELS[rec.source] || rec.source}</span>
            <span style={{ fontSize: 10, color: rec.executable ? C.success : C.warning }}>
                {rec.executable ? 'Executable' : 'Alert'}
            </span>
            <span style={{ fontSize: 10, color: C.textMuted }}>
                Confidence {(Number(rec.confidence_score || 0) * 100).toFixed(0)}%
            </span>
            <span style={{ fontSize: 10, color: C.textMuted }}>
                Risk {(Number(rec.risk_score || 0) * 100).toFixed(0)}%
            </span>
            <span style={{ fontSize: 10, color: C.textMuted }}>
                Expires {formatExpires(rec.expires_at)}
            </span>
        </div>
    )
}

function RecommendationCard({ rec, onApply, onDismiss, isApplying, selected, onToggle }) {
    const actionType = rec.action_payload?.action_type || rec.suggested_action || rec.type
    const impact = formatImpact(rec)
    const entityTypeLabel = ENTITY_TYPE_LABELS[rec.entity_type] || rec.entity_type || ''

    return (
        <div className="v2-card" style={{ padding: '16px 18px', border: selected ? '1px solid rgba(79,142,247,0.35)' : undefined }}>
            <div className="flex items-start gap-3">
                <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => onToggle(rec.id)}
                    style={{ marginTop: 4, accentColor: C.accentBlue, cursor: 'pointer', flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 8 }}>
                        <PriorityPill priority={rec.priority} />
                        <TypePill actionType={actionType} />
                        <span style={{ fontSize: 10, color: C.textMuted }}>{entityTypeLabel}</span>
                    </div>

                    <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary, marginBottom: 2 }}>
                        {rec.entity_name || 'Recommendation'}
                    </div>
                    {rec.campaign_name && (
                        <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 8 }}>
                            Campaign: {rec.campaign_name}
                        </div>
                    )}

                    <MetaRow rec={rec} />
                    <MetricPills metadata={rec.metadata} />

                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', lineHeight: 1.5, marginBottom: 6 }}>
                        {rec.reason}
                    </p>
                    {rec.recommended_action && (
                        <p style={{ fontSize: 11, color: C.textPlaceholder, marginBottom: 6 }}>
                            Recommended: {rec.recommended_action}
                        </p>
                    )}
                    {impact && (
                        <p style={{ fontSize: 11, color: C.success, marginBottom: 12 }}>
                            {impact}
                        </p>
                    )}

                    <ContextPanel rec={rec} />
                    <ExplanationPanel rec={rec} />

                    <div className="flex items-center gap-2 flex-wrap">
                        <button
                            onClick={() => onApply(rec)}
                            disabled={isApplying || !rec.executable}
                            title={!rec.executable ? 'This card is an alert and has no apply action.' : undefined}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 6,
                                padding: '6px 14px',
                                borderRadius: 7,
                                fontSize: 12,
                                fontWeight: 500,
                                background: rec.executable ? C.accentBlue : C.w08,
                                color: rec.executable ? 'white' : C.w40,
                                cursor: rec.executable ? 'pointer' : 'not-allowed',
                                border: 'none',
                                opacity: isApplying ? 0.6 : 1,
                            }}
                        >
                            {isApplying
                                ? <><Loader2 size={12} className="animate-spin" /> Wykonuję...</>
                                : <><Play size={12} style={{ fill: rec.executable ? 'white' : 'transparent' }} /> {rec.executable ? 'Zastosuj' : 'Ręczna weryfikacja'}</>
                            }
                        </button>
                        <button
                            onClick={() => onDismiss(rec)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 6,
                                padding: '6px 12px',
                                borderRadius: 7,
                                fontSize: 12,
                                background: 'transparent',
                                color: C.textPlaceholder,
                                cursor: 'pointer',
                                border: B.medium,
                            }}
                        >
                            <XCircle size={12} /> Odrzuć
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function Section({ title, count, items, onApply, onDismiss, applyingId, selectedIds, onToggle }) {
    if (!items.length) return null
    return (
        <div style={{ marginBottom: 18 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
                <h2 style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.65)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    {title}
                </h2>
                <span style={{ fontSize: 11, color: C.textMuted }}>{count}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: 12 }}>
                {items.map((rec, index) => (
                    <RecommendationCard
                        key={rec.id ?? `rec-${index}`}
                        rec={rec}
                        onApply={onApply}
                        onDismiss={onDismiss}
                        isApplying={applyingId === rec.id}
                        selected={selectedIds.has(rec.id)}
                        onToggle={onToggle}
                    />
                ))}
            </div>
        </div>
    )
}

export default function Recommendations() {
    const { selectedClientId, showToast } = useApp()
    const { days } = useFilter()
    const { recommendations, summary, loading, updateFilters, refetch, apply, dismiss } = useRecommendations(selectedClientId, { days })

    const [filterPriority, setFilterPriority] = useState('ALL')
    const [filterSource, setFilterSource] = useState('ALL')
    const [filterExecution, setFilterExecution] = useState('ALL')
    const [filterCategory, setFilterCategory] = useState('ALL')
    const [applyingId, setApplyingId] = useState(null)
    const [confirmModal, setConfirmModal] = useState(null)
    const [dryRunData, setDryRunData] = useState(null)
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [bulkApplying, setBulkApplying] = useState(false)

    useEffect(() => {
        updateFilters({
            status: 'pending',
            priority: filterPriority !== 'ALL' ? filterPriority : undefined,
            source: filterSource !== 'ALL' ? filterSource : undefined,
            executable: filterExecution === 'ALL' ? undefined : filterExecution === 'EXECUTABLE',
            category: filterCategory !== 'ALL' ? filterCategory : undefined,
        })
    }, [filterCategory, filterExecution, filterPriority, filterSource, updateFilters])

    const executableItems = useMemo(
        () => (recommendations || []).filter(rec => rec.executable),
        [recommendations]
    )
    const alertItems = useMemo(
        () => (recommendations || []).filter(rec => !rec.executable),
        [recommendations]
    )
    const selectableIds = useMemo(
        () => new Set((recommendations || []).filter(rec => rec.executable).map(rec => rec.id)),
        [recommendations]
    )

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (loading) return <LoadingSpinner />

    async function handleApply(rec) {
        if (!rec.executable) {
            showToast('Ta rekomendacja jest alertem i wymaga ręcznej weryfikacji.', 'info')
            return
        }
        setApplyingId(rec.id)
        try {
            const preview = await apply(rec.id, true)
            setDryRunData(preview)
            setConfirmModal(rec)
        } catch (err) {
            showToast('Błąd podglądu: ' + err.message, 'error')
        } finally {
            setApplyingId(null)
        }
    }

    async function handleConfirm() {
        if (!confirmModal) return
        setApplyingId(confirmModal.id)
        try {
            await apply(confirmModal.id, false)
            showToast('Akcja wykonana — zobacz zakładkę Historia zmian', 'success')

            setConfirmModal(null)
            setDryRunData(null)
            setSelectedIds(new Set())
            await refetch()
        } catch (err) {
            showToast('Błąd wykonania: ' + err.message, 'error')
        } finally {
            setApplyingId(null)
        }
    }

    async function handleDismiss(rec) {
        try {
            await dismiss(rec.id)
            setSelectedIds(prev => {
                const next = new Set(prev)
                next.delete(rec.id)
                return next
            })
            showToast('Rekomendacja odrzucona', 'info')
        } catch (err) {
            showToast('Błąd: ' + err.message, 'error')
        }
    }

    function toggleSelect(id) {
        if (!selectableIds.has(id)) return
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    function selectAllExecutable() {
        const executableIds = recommendations.filter(rec => rec.executable).map(rec => rec.id)
        if (selectedIds.size === executableIds.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(executableIds))
        }
    }

    async function handleBulkApply() {
        const executableTargets = recommendations.filter(rec => rec.executable && selectedIds.has(rec.id))
        if (!executableTargets.length) return
        setBulkApplying(true)
        let success = 0
        let failed = 0
        for (const rec of executableTargets) {
            try {
                await apply(rec.id, false)
                success += 1
            } catch {
                failed += 1
            }
        }
        setBulkApplying(false)
        setSelectedIds(new Set())
        await refetch()
        showToast(`Wykonano ${success} akcji${failed ? `, błędów: ${failed}` : ''}`, success ? 'success' : 'error')
    }

    async function handleBulkDismiss() {
        const targets = recommendations.filter(rec => selectedIds.has(rec.id))
        if (!targets.length) return
        setBulkApplying(true)
        for (const rec of targets) {
            try {
                await dismiss(rec.id)
            } catch {
                // noop
            }
        }
        setBulkApplying(false)
        setSelectedIds(new Set())
        await refetch()
        showToast('Zaznaczone rekomendacje odrzucone', 'info')
    }

    const sourceOptions = ['ALL', 'PLAYBOOK_RULES', 'ANALYTICS', 'GOOGLE_ADS_API', 'HYBRID']

    return (
        <div style={{ maxWidth: 1140 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Rekomendacje
                    </h1>
                    <p style={{ fontSize: 12, color: C.textMuted, marginTop: 3 }}>
                        {(summary && summary.total) || (recommendations && recommendations.length) || 0} aktywnych rekomendacji
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            const params = new URLSearchParams({ client_id: selectedClientId, format: 'xlsx' })
                            window.location.href = `/api/v1/export/recommendations?${params.toString()}`
                        }}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 5,
                            padding: '6px 12px', borderRadius: 7, fontSize: 11,
                            background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)',
                            color: C.success, cursor: 'pointer',
                        }}
                    >
                        <Download size={11} /> Eksport
                    </button>
                    <button
                        onClick={() => refetch()}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '6px 14px', borderRadius: 7, fontSize: 12,
                            background: C.w05, border: B.medium,
                            color: C.w60, cursor: 'pointer',
                        }}
                    >
                        <RefreshCw size={12} /> Odśwież
                    </button>
                </div>
            </div>

            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Łącznie</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>{summary?.total || 0}</span>
                    </div>
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Do wykonania</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: C.success, fontFamily: 'Syne' }}>{summary?.executable_total || 0}</span>
                    </div>
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Pilne</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: C.danger, fontFamily: 'Syne' }}>{summary?.high_priority || 0}</span>
                    </div>
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Akcje</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: C.success, fontFamily: 'Syne' }}>{summary?.by_context_outcome?.ACTION || 0}</span>
                    </div>
                    <div className="v2-card" style={{ padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Zablokowane</span>
                        <span style={{ fontSize: 18, fontWeight: 700, color: C.warning, fontFamily: 'Syne' }}>{summary?.by_context_outcome?.BLOCKED_BY_CONTEXT || 0}</span>
                    </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(priority => (
                        <button
                            key={priority}
                            onClick={() => setFilterPriority(priority)}
                            style={{
                                padding: '4px 12px',
                                borderRadius: 999,
                                fontSize: 11,
                                border: `1px solid ${filterPriority === priority ? C.accentBlue : C.w10}`,
                                background: filterPriority === priority ? C.accentBlueBg : 'transparent',
                                color: filterPriority === priority ? C.textPrimary : C.textPlaceholder,
                                cursor: 'pointer',
                            }}
                        >
                            {priority}
                        </button>
                    ))}
                    {sourceOptions.map(source => (
                        <button
                            key={source}
                            onClick={() => setFilterSource(source)}
                            style={{
                                padding: '4px 12px',
                                borderRadius: 999,
                                fontSize: 11,
                                border: `1px solid ${filterSource === source ? 'rgba(74,222,128,0.35)' : C.w10}`,
                                background: filterSource === source ? 'rgba(74,222,128,0.12)' : 'transparent',
                                color: filterSource === source ? C.success : C.textPlaceholder,
                                cursor: 'pointer',
                            }}
                        >
                            {source === 'ALL' ? 'Wszystkie źródła' : SOURCE_LABELS[source] || source}
                        </button>
                    ))}
                    {['ALL', 'EXECUTABLE', 'ALERTS'].map(mode => (
                        <button
                            key={mode}
                            onClick={() => setFilterExecution(mode)}
                            style={{
                                padding: '4px 12px',
                                borderRadius: 999,
                                fontSize: 11,
                                border: `1px solid ${filterExecution === mode ? 'rgba(251,191,36,0.35)' : C.w10}`,
                                background: filterExecution === mode ? 'rgba(251,191,36,0.12)' : 'transparent',
                                color: filterExecution === mode ? C.warning : C.textPlaceholder,
                                cursor: 'pointer',
                            }}
                        >
                            {mode}
                        </button>
                    ))}
                    {[{ key: 'ALL', label: 'Wszystkie' }, { key: 'RECOMMENDATION', label: 'Rekomendacje' }, { key: 'ALERT', label: 'Alerty' }].map(cat => (
                        <button
                            key={cat.key}
                            onClick={() => setFilterCategory(cat.key)}
                            style={{
                                padding: '4px 12px',
                                borderRadius: 999,
                                fontSize: 11,
                                border: `1px solid ${filterCategory === cat.key ? 'rgba(123,92,224,0.35)' : C.w10}`,
                                background: filterCategory === cat.key ? 'rgba(123,92,224,0.12)' : 'transparent',
                                color: filterCategory === cat.key ? C.accentPurple : C.textPlaceholder,
                                cursor: 'pointer',
                            }}
                        >
                            {cat.label}
                        </button>
                    ))}
                </div>
            </div>

            {(recommendations || []).length > 0 && (
                <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 14 }}>
                    <button
                        onClick={selectAllExecutable}
                        style={{
                            padding: '5px 12px', borderRadius: 7, fontSize: 11,
                            background: C.w04, border: B.medium,
                            color: C.w50, cursor: 'pointer',
                        }}
                    >
                        {selectedIds.size === executableItems.length ? 'Odznacz wykonalne' : 'Zaznacz wykonalne'}
                    </button>
                    {selectedIds.size > 0 && (
                        <>
                            <span style={{ fontSize: 11, color: C.w40 }}>{selectedIds.size} selected</span>
                            <button
                                onClick={handleBulkApply}
                                disabled={bulkApplying}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '5px 14px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                                    background: C.accentBlue, color: 'white', border: 'none', cursor: 'pointer',
                                    opacity: bulkApplying ? 0.6 : 1,
                                }}
                            >
                                {bulkApplying ? <><Loader2 size={12} className="animate-spin" /> Running...</> : <><Play size={12} style={{ fill: 'white' }} /> Apply selected</>}
                            </button>
                            <button
                                onClick={handleBulkDismiss}
                                disabled={bulkApplying}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '5px 12px', borderRadius: 7, fontSize: 11,
                                    background: 'transparent', border: B.medium,
                                    color: C.textPlaceholder, cursor: 'pointer',
                                }}
                            >
                                <XCircle size={11} /> Dismiss selected
                            </button>
                        </>
                    )}
                </div>
            )}

            {!(recommendations || []).length ? (
                <div style={{ padding: '48px 0', textAlign: 'center' }}>
                    <CheckCircle2 size={40} style={{ color: C.success, margin: '0 auto 12px' }} />
                    <div style={{ fontSize: 15, fontWeight: 500, color: C.textPrimary, marginBottom: 4 }}>Nothing to do</div>
                    <div style={{ fontSize: 13, color: C.w40 }}>No active recommendations match the current filters.</div>
                </div>
            ) : (
                <>
                    <Section
                        title="Executable"
                        count={executableItems.length}
                        items={executableItems}
                        onApply={handleApply}
                        onDismiss={handleDismiss}
                        applyingId={applyingId}
                        selectedIds={selectedIds}
                        onToggle={toggleSelect}
                    />
                    <Section
                        title="Alerts"
                        count={alertItems.length}
                        items={alertItems}
                        onApply={handleApply}
                        onDismiss={handleDismiss}
                        applyingId={applyingId}
                        selectedIds={selectedIds}
                        onToggle={toggleSelect}
                    />
                </>
            )}

            <ConfirmationModal
                isOpen={!!confirmModal}
                onClose={() => { setConfirmModal(null); setDryRunData(null) }}
                onConfirm={handleConfirm}
                title="Confirm action"
                actionType={dryRunData?.action?.action_type || confirmModal?.action_payload?.action_type || confirmModal?.suggested_action}
                entity={confirmModal?.entity_name}
                reason={confirmModal?.reason}
                beforeState={dryRunData?.before_state}
                afterState={dryRunData?.after_state}
                isLoading={!!applyingId}
            />
        </div>
    )
}

