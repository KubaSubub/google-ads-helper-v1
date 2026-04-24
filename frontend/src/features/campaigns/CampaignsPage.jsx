import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    KeyRound, Search, Monitor, MapPin, Clock, Trophy, Pause, Play,
    Filter, X, ArrowDownUp, Pencil, ChevronDown, ChevronUp, Layers,
} from 'lucide-react'
import {
    getCampaigns, getCampaignKPIs, updateCampaign,
    getDeviceBreakdown, getGeoBreakdown, getBudgetPacing,
    getUnifiedTimeline, getCampaignsSummary, getAuctionInsights,
    updateCampaignBudget, updateCampaignStatus, updateBiddingTarget,
    getCampaignAdGroups,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import { C, T, S, R, B, PILL, TOOLTIP_STYLE, CAMPAIGN_STATUS, CHANNEL_COLORS, TRANSITION, FONT } from '../../constants/designTokens'
import EmptyState from '../../components/EmptyState'
import { LoadingSpinner, ErrorMessage } from '../../components/UI'
import { BudgetPacingModule } from '../../components/modules'
import DarkSelect from '../../components/DarkSelect'
import CampaignKpiRow from './components/CampaignKpiRow'
import TrendExplorer from '../../components/TrendExplorer'
import AuctionInsightsTable from '../../components/AuctionInsightsTable'

// ─── Constants ────────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
    ENABLED: { dot: CAMPAIGN_STATUS.ENABLED.dot, color: CAMPAIGN_STATUS.ENABLED.dot, label: CAMPAIGN_STATUS.ENABLED.label },
    PAUSED: { dot: CAMPAIGN_STATUS.PAUSED.dot, color: CAMPAIGN_STATUS.PAUSED.dot, label: CAMPAIGN_STATUS.PAUSED.label },
    REMOVED: { dot: CAMPAIGN_STATUS.REMOVED.dot, color: CAMPAIGN_STATUS.REMOVED.dot, label: CAMPAIGN_STATUS.REMOVED.label },
}

const TYPE_LABELS = {
    SEARCH: 'Search', PERFORMANCE_MAX: 'PMax',
    DISPLAY: 'Display', SHOPPING: 'Shopping', VIDEO: 'Video',
}

const ROLE_LABELS = {
    BRAND: 'Brand',
    GENERIC: 'Generic',
    PROSPECTING: 'Prospecting',
    REMARKETING: 'Remarketing',
    PMAX: 'PMax',
    LOCAL: 'Local',
    UNKNOWN: 'Unknown',
}

const ROLE_OPTIONS = ['BRAND', 'GENERIC', 'PROSPECTING', 'REMARKETING', 'PMAX', 'LOCAL', 'UNKNOWN']

const PROTECTION_CONFIG = {
    HIGH: { color: C.danger, bg: C.dangerBg },
    MEDIUM: { color: C.warning, bg: C.warningBg },
    LOW: { color: C.success, bg: C.successBg },
}

const PROTECTION_TOOLTIPS = {
    HIGH: 'Poziom HIGH: automatyzacja nie zmienia bidów/budżetów/statusów bez potwierdzenia użytkownika. Zalecane dla kampanii Brand i PMax.',
    MEDIUM: 'Poziom MEDIUM: drobne korekty bidów ±20% dozwolone automatycznie, większe zmiany wymagają potwierdzenia.',
    LOW: 'Poziom LOW: pełna automatyzacja. Bidy, budżety i negatives mogą być zmieniane bez interakcji użytkownika.',
}

const ROLE_SOURCE_LABELS = {
    AUTO: 'Auto',
    MANUAL: 'Manual',
}

const OPERATION_LABELS = {
    UPDATE_BID: 'Zmiana stawki',
    PAUSE_KEYWORD: 'Wstrzymanie słowa kluczowego',
    ENABLE_KEYWORD: 'Włączenie słowa kluczowego',
    ADD_KEYWORD: 'Dodanie słowa kluczowego',
    ADD_NEGATIVE: 'Dodanie wykluczenia',
    PAUSE_AD: 'Wstrzymanie reklamy',
    INCREASE_BUDGET: 'Zwiększenie budżetu',
    DECREASE_BUDGET: 'Zmniejszenie budżetu',
    PAUSE_CAMPAIGN: 'Wstrzymanie kampanii',
    ENABLE_CAMPAIGN: 'Włączenie kampanii',
    UPDATE_STATUS: 'Zmiana statusu',
    UPDATE_BUDGET: 'Zmiana budżetu',
    CREATE: 'Utworzenie',
    REMOVE: 'Usunięcie',
}

function getOperationLabel(op) {
    if (!op) return 'Zmiana'
    return OPERATION_LABELS[op] || op.replace(/_/g, ' ').toLowerCase().replace(/^\w/, c => c.toUpperCase())
}

function formatTimestamp(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatBeforeAfter(entry) {
    const parts = []
    try {
        const oldVal = entry.old_value_json ? (typeof entry.old_value_json === 'string' ? JSON.parse(entry.old_value_json) : entry.old_value_json) : null
        const newVal = entry.new_value_json ? (typeof entry.new_value_json === 'string' ? JSON.parse(entry.new_value_json) : entry.new_value_json) : null

        if (!oldVal && !newVal) return null

        if (oldVal?.bid_micros !== undefined || newVal?.bid_micros !== undefined) {
            const oldBid = oldVal?.bid_micros != null ? (oldVal.bid_micros / 1_000_000).toFixed(2) : '—'
            const newBid = newVal?.bid_micros != null ? (newVal.bid_micros / 1_000_000).toFixed(2) : '—'
            parts.push(`Stawka: ${oldBid} → ${newBid} zł`)
        }
        if (oldVal?.budget_micros !== undefined || newVal?.budget_micros !== undefined) {
            const oldB = oldVal?.budget_micros != null ? (oldVal.budget_micros / 1_000_000).toFixed(0) : '—'
            const newB = newVal?.budget_micros != null ? (newVal.budget_micros / 1_000_000).toFixed(0) : '—'
            parts.push(`Budżet: ${oldB} → ${newB} zł`)
        }
        if (oldVal?.status !== undefined || newVal?.status !== undefined) {
            const statusPl = { ENABLED: 'Aktywny', PAUSED: 'Wstrzymany', REMOVED: 'Usunięty' }
            const oldS = statusPl[oldVal?.status] || oldVal?.status || '—'
            const newS = statusPl[newVal?.status] || newVal?.status || '—'
            parts.push(`Status: ${oldS} → ${newS}`)
        }
        if (oldVal?.match_type !== undefined || newVal?.match_type !== undefined) {
            parts.push(`Typ: ${oldVal?.match_type || '—'} → ${newVal?.match_type || '—'}`)
        }

        if (parts.length === 0) {
            const allKeys = new Set([...Object.keys(oldVal || {}), ...Object.keys(newVal || {})])
            for (const key of allKeys) {
                const o = oldVal?.[key]
                const n = newVal?.[key]
                if (o !== n && o !== undefined && n !== undefined) {
                    const oStr = typeof o === 'number' && key.includes('micros') ? (o / 1_000_000).toFixed(2) : String(o)
                    const nStr = typeof n === 'number' && key.includes('micros') ? (n / 1_000_000).toFixed(2) : String(n)
                    parts.push(`${key}: ${oStr} → ${nStr}`)
                    if (parts.length >= 3) break
                }
            }
        }
    } catch {
        return null
    }
    return parts.length > 0 ? parts : null
}

// ─── Action History Timeline (local sub-component) ────────────────────────────
function ActionHistoryTimeline({ entries }) {
    if (!entries?.length) return null

    return (
        <div className="v2-card" style={{ padding: '16px 20px' }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                <Clock size={14} style={{ color: C.accentBlue }} />
                <span style={{ ...T.sectionTitle, fontSize: 13 }}>
                    Historia zmian ({entries.length})
                </span>
            </div>
            <div style={{ maxHeight: 360, overflowY: 'auto' }}>
                {entries.map((entry, i) => {
                    const isHelper = entry.source === 'helper'
                    const borderColor = isHelper ? C.accentBlue : C.w12
                    const ts = entry.timestamp || entry.executed_at || entry.change_date_time
                    const op = entry.operation || entry.action_type
                    const beforeAfter = formatBeforeAfter(entry)

                    return (
                        <div key={entry.action_log_id || entry.change_event_id || i} style={{
                            display: 'flex', gap: 10, paddingLeft: 12, paddingBottom: 10, marginBottom: 10,
                            borderLeft: `2px solid ${borderColor}`,
                            borderBottom: i < entries.length - 1 ? `1px solid ${C.w04}` : 'none',
                        }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div className="flex items-center gap-2" style={{ marginBottom: 3 }}>
                                    <span style={{
                                        fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                        background: isHelper ? C.accentBlueBg : C.warningBg,
                                        color: isHelper ? C.accentBlue : C.warning,
                                    }}>
                                        {isHelper ? 'HELPER' : 'ZEWN.'}
                                    </span>
                                    <span style={{ fontSize: 10, color: C.w40, fontFamily: FONT.mono }}>
                                        {ts ? formatTimestamp(ts) : ''}
                                    </span>
                                </div>
                                <div style={{ fontSize: 12, color: C.textPrimary, fontWeight: 500, marginBottom: 2 }}>
                                    {getOperationLabel(op)}
                                </div>
                                {entry.entity_name && (
                                    <div style={{ fontSize: 11, color: C.textPlaceholder, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 2 }}>
                                        {entry.entity_name}
                                    </div>
                                )}
                                {beforeAfter && (
                                    <div style={{
                                        marginTop: 3, padding: '4px 8px', borderRadius: 4,
                                        background: 'rgba(167,139,250,0.06)', border: '1px solid rgba(167,139,250,0.12)',
                                    }}>
                                        {beforeAfter.map((line, j) => (
                                            <div key={j} style={{ fontSize: 10, color: '#A78BFA', fontFamily: 'monospace' }}>
                                                {line}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

// ─── Main Orchestrator ────────────────────────────────────────────────────────
export default function CampaignsPage() {
    const navigate = useNavigate()
    const { selectedClientId, showToast } = useApp()
    const { filters, allParams, dateParams, campaignParams } = useFilter()

    const [campaigns, setCampaigns] = useState([])
    const [selected, setSelected] = useState(null)
    const [kpis, setKpis] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // Campaign list sorting & filtering
    const [campSummary, setCampSummary] = useState({})
    const [sortBy, setSortBy] = useState('cost_usd')
    const [sortDir, setSortDir] = useState('desc')
    const [metricFilter, setMetricFilter] = useState({ field: null, op: 'gte', value: '' })
    const [showFilter, setShowFilter] = useState(false)

    // Secondary data
    const [deviceData, setDeviceData] = useState(null)
    const [geoData, setGeoData] = useState(null)
    const [auctionData, setAuctionData] = useState(null)
    const [budgetPacing, setBudgetPacing] = useState(null)
    const [pacingAll, setPacingAll] = useState(null)
    const [actionTimeline, setActionTimeline] = useState([])
    const [loadingSecondary, setLoadingSecondary] = useState(false)
    const [roleDraft, setRoleDraft] = useState('')
    const [savingRole, setSavingRole] = useState(false)

    // Mutations state
    const [busyAction, setBusyAction] = useState(null) // 'status' | 'budget' | 'bidding'
    const [budgetModalOpen, setBudgetModalOpen] = useState(false)
    const [budgetDraft, setBudgetDraft] = useState('')
    const [biddingModalOpen, setBiddingModalOpen] = useState(false)
    const [biddingDraft, setBiddingDraft] = useState('')
    const [showRoleCard, setShowRoleCard] = useState(() => localStorage.getItem('campaignShowRole') !== 'false')

    // Ad groups
    const [adGroups, setAdGroups] = useState([])
    const [loadingAdGroups, setLoadingAdGroups] = useState(false)

    useEffect(() => {
        localStorage.setItem('campaignShowRole', showRoleCard ? 'true' : 'false')
    }, [showRoleCard])

    useEffect(() => {
        if (selectedClientId) loadCampaigns()
    }, [selectedClientId, campaignParams, allParams])

    async function loadCampaigns() {
        setLoading(true)
        try {
            const [data, summaryData, pacingData] = await Promise.all([
                getCampaigns(selectedClientId, campaignParams),
                getCampaignsSummary(selectedClientId, allParams).catch(() => ({ campaigns: {} })),
                getBudgetPacing(selectedClientId, campaignParams).catch(() => null),
            ])
            const items = data.items || []
            setCampaigns(items)
            setCampSummary(summaryData?.campaigns || {})
            setPacingAll(pacingData)
            if (items.length > 0) selectCampaign(items[0], pacingData)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const selectCampaign = useCallback(async (campaign, pacingOverride = null) => {
        setSelected(campaign)
        setKpis(null)
        setDeviceData(null)
        setGeoData(null)
        setAuctionData(null)
        setBudgetPacing(null)
        setActionTimeline([])

        try {
            const kpiData = await getCampaignKPIs(campaign.id, null, dateParams).catch(() => null)
            setKpis(kpiData)
        } catch (err) {
            console.error('Failed to load campaign details:', err)
        }

        // Pacing from cached pacingAll (loaded once in loadCampaigns per client)
        const pacingSource = pacingOverride || pacingAll
        const thisCampPacing = pacingSource?.campaigns?.find(c => c.campaign_id === campaign.id)
        setBudgetPacing(thisCampPacing)

        // Secondary data (non-blocking)
        setLoadingSecondary(true)
        Promise.all([
            getDeviceBreakdown(selectedClientId, { ...allParams, campaign_id: campaign.id }).catch(() => null),
            getGeoBreakdown(selectedClientId, { ...allParams, campaign_id: campaign.id }).catch(() => null),
            getUnifiedTimeline(selectedClientId, { limit: 200 }).catch(() => ({ entries: [] })),
            getAuctionInsights(selectedClientId, { ...allParams, campaign_id: campaign.id }).catch(() => null),
        ]).then(([dev, geo, timeline, auction]) => {
            setDeviceData(dev)
            setGeoData(geo)
            setAuctionData(Array.isArray(auction) ? auction : [])
            const filtered = (timeline?.entries || []).filter(e => e.campaign_id === campaign.id || e.campaign_name === campaign.name)
            setActionTimeline(filtered)
            setLoadingSecondary(false)
        })
    }, [selectedClientId, allParams, dateParams, pacingAll])

    // Re-fetch on date change
    useEffect(() => {
        if (selected && selectedClientId) selectCampaign(selected)
    }, [allParams])

    useEffect(() => {
        if (!selected) {
            setRoleDraft('')
            return
        }
        setRoleDraft(selected.role_source === 'MANUAL' ? (selected.campaign_role_final || selected.campaign_role_auto || '') : '')
    }, [selected])

    function mergeCampaignState(updatedCampaign) {
        setCampaigns(prev => prev.map(c => (c.id === updatedCampaign.id ? { ...c, ...updatedCampaign } : c)))
        setSelected(prev => (prev && prev.id === updatedCampaign.id ? { ...prev, ...updatedCampaign } : prev))
    }

    async function handleRoleSave() {
        if (!selected || !roleDraft) return
        setSavingRole(true)
        try {
            const updated = await updateCampaign(selected.id, { campaign_role_final: roleDraft })
            mergeCampaignState(updated)
            showToast('Rola kampanii zapisana', 'success')
        } catch (err) {
            showToast('Blad zapisu roli: ' + err.message, 'error')
        } finally {
            setSavingRole(false)
        }
    }

    async function handleRoleReset() {
        if (!selected) return
        setSavingRole(true)
        try {
            const updated = await updateCampaign(selected.id, { campaign_role_final: null })
            mergeCampaignState(updated)
            setRoleDraft('')
            showToast('Przywrocono klasyfikacje auto', 'info')
        } catch (err) {
            showToast('Blad resetu roli: ' + err.message, 'error')
        } finally {
            setSavingRole(false)
        }
    }

    async function handleToggleStatus() {
        if (!selected) return
        const newStatus = selected.status === 'ENABLED' ? 'PAUSED' : 'ENABLED'
        const actionLabel = newStatus === 'PAUSED' ? 'Wstrzymac' : 'Wznowic'
        const estimate = campSummary[String(selected.id)]
        const dailyClicks = estimate?.clicks && filters.days ? Math.round(estimate.clicks / filters.days) : null
        const confirmMsg = `${actionLabel} kampanie "${selected.name}"?${dailyClicks ? `\n\nSredni dzienny ruch: ~${dailyClicks} kliknięć.` : ''}`
        if (!window.confirm(confirmMsg)) return
        setBusyAction('status')
        try {
            const result = await updateCampaignStatus(selected.id, newStatus)
            mergeCampaignState({ id: selected.id, status: result.new_status })
            showToast(
                result.api_synced
                    ? `Kampania ${newStatus === 'PAUSED' ? 'wstrzymana' : 'wznowiona'} (API + LOCAL)`
                    : `Kampania ${newStatus === 'PAUSED' ? 'wstrzymana' : 'wznowiona'} (LOCAL, pending sync)`,
                'success',
            )
        } catch (err) {
            showToast('Blad zmiany statusu: ' + err.message, 'error')
        } finally {
            setBusyAction(null)
        }
    }

    function openBudgetModal() {
        if (!selected) return
        const currentBudgetZl = ((selected.budget_micros || 0) / 1_000_000).toFixed(2)
        setBudgetDraft(currentBudgetZl)
        setBudgetModalOpen(true)
    }

    async function handleSaveBudget() {
        if (!selected) return
        const budgetZl = parseFloat(budgetDraft)
        if (isNaN(budgetZl) || budgetZl <= 0) {
            showToast('Wprowadz dodatnia kwote budzetu', 'error')
            return
        }
        const newMicros = Math.round(budgetZl * 1_000_000)
        const oldMicros = selected.budget_micros || 0
        const changePct = oldMicros ? Math.abs((newMicros - oldMicros) / oldMicros * 100) : 0
        if (changePct > 30) {
            if (!window.confirm(`Zmiana budzetu o ${changePct.toFixed(0)}% (>30%) — kontynuowac?`)) return
        }
        setBusyAction('budget')
        try {
            const result = await updateCampaignBudget(selected.id, newMicros)
            mergeCampaignState({ id: selected.id, budget_micros: result.new_budget_micros, budget_usd: result.new_budget_micros / 1_000_000 })
            showToast(result.api_synced ? 'Budzet zapisany (API + LOCAL)' : 'Budzet zapisany (LOCAL, pending sync)', 'success')
            setBudgetModalOpen(false)
        } catch (err) {
            showToast('Blad zapisu budzetu: ' + err.message, 'error')
        } finally {
            setBusyAction(null)
        }
    }

    function openBiddingModal() {
        if (!selected) return
        const field = selected.target_cpa_micros ? 'target_cpa_micros' : selected.target_roas ? 'target_roas' : 'target_cpa_micros'
        const current = field === 'target_cpa_micros'
            ? ((selected.target_cpa_micros || 0) / 1_000_000).toFixed(2)
            : (selected.target_roas || 0).toFixed(2)
        setBiddingDraft(current)
        setBiddingModalOpen(true)
    }

    async function handleSaveBidding() {
        if (!selected) return
        const val = parseFloat(biddingDraft)
        if (isNaN(val) || val <= 0) {
            showToast('Wprowadz poprawna wartosc', 'error')
            return
        }
        const field = selected.target_cpa_micros ? 'target_cpa_micros' : selected.target_roas ? 'target_roas' : 'target_cpa_micros'
        const apiVal = field === 'target_cpa_micros' ? Math.round(val * 1_000_000) : val
        setBusyAction('bidding')
        try {
            const result = await updateBiddingTarget(selected.id, field, apiVal)
            const update = field === 'target_cpa_micros'
                ? { id: selected.id, target_cpa_micros: result.new_value }
                : { id: selected.id, target_roas: result.new_value }
            mergeCampaignState(update)
            showToast(result.api_synced ? 'Cel licytacji zapisany (API + LOCAL)' : 'Cel licytacji zapisany (LOCAL, pending sync)', 'success')
            setBiddingModalOpen(false)
        } catch (err) {
            showToast('Blad zapisu celu licytacji: ' + err.message, 'error')
        } finally {
            setBusyAction(null)
        }
    }

    // Load ad groups when campaign selected or date changes
    useEffect(() => {
        if (!selected) {
            setAdGroups([])
            return
        }
        setLoadingAdGroups(true)
        const params = {}
        if (dateParams?.date_from) params.date_from = dateParams.date_from
        if (dateParams?.date_to) params.date_to = dateParams.date_to
        getCampaignAdGroups(selected.id, params)
            .then(data => setAdGroups(data?.items || []))
            .catch(() => setAdGroups([]))
            .finally(() => setLoadingAdGroups(false))
    }, [selected?.id, dateParams?.date_from, dateParams?.date_to])

    // Campaigns filtered by backend (type/status) + in-memory name/label/metric filter + sort
    const filteredCampaigns = useMemo(() => {
        let result = campaigns.filter(c => {
            if (filters.campaignName && !c.name?.toLowerCase().includes(filters.campaignName.toLowerCase())) return false
            if (filters.campaignLabel !== 'ALL' && !(c.labels || []).includes(filters.campaignLabel)) return false
            // Metric filter
            if (metricFilter.field && metricFilter.value !== '') {
                const m = campSummary[String(c.id)]
                const val = m?.[metricFilter.field] ?? 0
                const threshold = parseFloat(metricFilter.value)
                if (isNaN(threshold)) return true
                if (metricFilter.op === 'gte' && val < threshold) return false
                if (metricFilter.op === 'lte' && val > threshold) return false
            }
            return true
        })
        // Sort by metric
        if (sortBy) {
            result = [...result].sort((a, b) => {
                const mA = campSummary[String(a.id)]
                const mB = campSummary[String(b.id)]
                const vA = sortBy === 'budget' ? (a.budget_usd ?? 0) : (mA?.[sortBy] ?? 0)
                const vB = sortBy === 'budget' ? (b.budget_usd ?? 0) : (mB?.[sortBy] ?? 0)
                return sortDir === 'desc' ? vB - vA : vA - vB
            })
        }
        return result
    }, [campaigns, filters.campaignName, filters.campaignLabel, campSummary, sortBy, sortDir, metricFilter])

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (loading) return <LoadingSpinner />
    if (error) return <ErrorMessage message={error} onRetry={loadCampaigns} />

    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ ...T.pageTitle }}>
                        Kampanie
                    </h1>
                    <p style={{ ...T.pageSubtitle }}>
                        {filteredCampaigns.length} z {campaigns.length} kampanii
                    </p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
                {/* Campaign list */}
                <div className="v2-card" style={{ padding: 6, maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
                    {/* Sort & Filter toolbar */}
                    <div style={{ padding: '6px 8px', borderBottom: `1px solid ${C.w06}`, marginBottom: 4 }}>
                        <div className="flex items-center gap-2" style={{ marginBottom: showFilter ? 8 : 0 }}>
                            <select
                                value={sortBy}
                                onChange={e => setSortBy(e.target.value)}
                                style={{
                                    flex: 1, background: C.w06, border: `1px solid ${C.w10}`,
                                    borderRadius: R.sm, padding: '4px 6px', fontSize: 10, color: C.textPrimary, cursor: 'pointer',
                                }}
                            >
                                <option value="cost_usd">Koszt</option>
                                <option value="conversions">Konwersje</option>
                                <option value="roas">ROAS</option>
                                <option value="clicks">Kliknięcia</option>
                                <option value="ctr">CTR</option>
                                <option value="budget">Budżet</option>
                            </select>
                            <button
                                onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
                                title={sortDir === 'desc' ? 'Malejąco' : 'Rosnąco'}
                                style={{
                                    background: C.w06, border: `1px solid ${C.w10}`,
                                    borderRadius: R.sm, padding: '4px 6px', cursor: 'pointer', color: C.textPrimary, fontSize: 10,
                                }}
                            >
                                {sortDir === 'desc' ? '↓' : '↑'}
                            </button>
                            <button
                                onClick={() => setShowFilter(v => !v)}
                                title="Filtruj po metryce"
                                style={{
                                    background: showFilter ? C.accentBlueBg : C.w06,
                                    border: `1px solid ${showFilter ? C.infoBorder : C.w10}`,
                                    borderRadius: R.sm, padding: '4px 6px', cursor: 'pointer',
                                    color: showFilter ? C.accentBlue : C.textPrimary,
                                }}
                            >
                                <Filter size={11} />
                            </button>
                        </div>
                        {showFilter && (
                            <div className="flex items-center gap-2">
                                <select
                                    value={metricFilter.field || ''}
                                    onChange={e => setMetricFilter(f => ({ ...f, field: e.target.value || null }))}
                                    style={{
                                        flex: 1, background: C.w06, border: `1px solid ${C.w10}`,
                                        borderRadius: R.sm, padding: '4px 6px', fontSize: 10, color: C.textPrimary, cursor: 'pointer',
                                    }}
                                >
                                    <option value="">— metryka —</option>
                                    <option value="cost_usd">Koszt</option>
                                    <option value="conversions">Konwersje</option>
                                    <option value="roas">ROAS</option>
                                    <option value="clicks">Kliknięcia</option>
                                    <option value="ctr">CTR</option>
                                </select>
                                <select
                                    value={metricFilter.op}
                                    onChange={e => setMetricFilter(f => ({ ...f, op: e.target.value }))}
                                    style={{
                                        width: 36, background: C.w06, border: `1px solid ${C.w10}`,
                                        borderRadius: R.sm, padding: '4px 4px', fontSize: 10, color: C.textPrimary, cursor: 'pointer',
                                    }}
                                >
                                    <option value="gte">≥</option>
                                    <option value="lte">≤</option>
                                </select>
                                <input
                                    type="number"
                                    value={metricFilter.value}
                                    onChange={e => setMetricFilter(f => ({ ...f, value: e.target.value }))}
                                    placeholder="0"
                                    style={{
                                        width: 52, background: C.w06, border: `1px solid ${C.w10}`,
                                        borderRadius: R.sm, padding: '4px 6px', fontSize: 10, color: C.textPrimary,
                                    }}
                                />
                                {metricFilter.field && (
                                    <button
                                        onClick={() => setMetricFilter({ field: null, op: 'gte', value: '' })}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.textMuted, padding: 0 }}
                                    >
                                        <X size={11} />
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {filteredCampaigns.length === 0 ? (
                        <div style={{ padding: '24px 12px', textAlign: 'center', fontSize: 12, color: C.textDim }}>
                            Brak kampanii
                        </div>
                    ) : filteredCampaigns.map(c => {
                        const active = selected?.id === c.id
                        const sCfg = STATUS_CONFIG[c.status] || { dot: '#666', color: '#666', label: c.status }
                        const cm = campSummary[String(c.id)]
                        return (
                            <button
                                key={c.id}
                                onClick={() => selectCampaign(c)}
                                style={{
                                    width: '100%', textAlign: 'left',
                                    padding: '10px 12px', borderRadius: 8,
                                    background: active ? 'rgba(79,142,247,0.12)' : 'transparent',
                                    border: `1px solid ${active ? C.infoBorder : 'transparent'}`,
                                    cursor: 'pointer', display: 'block', marginBottom: 2,
                                    borderLeft: active ? '2px solid #4F8EF7' : '2px solid transparent',
                                }}
                                className={active ? '' : 'hover:bg-white/[0.04]'}
                            >
                                <div className="flex items-center justify-between gap-2" style={{ marginBottom: 4 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {c.name}
                                    </span>
                                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: sCfg.dot, flexShrink: 0 }} />
                                </div>
                                <div style={{ fontSize: 11, color: C.textMuted, display: 'flex', gap: 6 }}>
                                    <span>{TYPE_LABELS[c.campaign_type] ?? c.campaign_type}</span>
                                    <span>·</span>
                                    <span>{c.budget_usd?.toFixed(0)} zł/d</span>
                                </div>
                                {cm && (
                                    <div style={{ fontSize: 10, color: C.w40, display: 'flex', gap: 8, marginTop: 4 }}>
                                        <span>{cm.cost_usd?.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł</span>
                                        <span>{cm.conversions?.toFixed(1)} conv</span>
                                        <span style={{ color: (cm.roas ?? 0) >= 3 ? C.success : (cm.roas ?? 0) >= 1 ? C.warning : C.danger }}>
                                            {cm.roas?.toFixed(1)}× ROAS
                                        </span>
                                    </div>
                                )}
                            </button>
                        )
                    })}
                </div>

                {/* Campaign detail - scrollable */}
                <div style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto', paddingRight: 4 }}>
                    {selected ? (
                        <>
                            {/* Header */}
                            <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>{selected.name}</span>
                                {(() => {
                                    const sCfg = STATUS_CONFIG[selected.status] || { color: '#666', label: selected.status }
                                    return <span style={{ fontSize: 11, color: sCfg.color }}>● {sCfg.label}</span>
                                })()}
                                {selected.bidding_strategy && (
                                    <span style={{ fontSize: 10, color: C.w25, marginLeft: 4 }}>
                                        {selected.bidding_strategy}
                                    </span>
                                )}
                                {/* Target CPA/ROAS z pencil */}
                                {(selected.target_cpa_micros || selected.target_roas) && (
                                    <button
                                        onClick={openBiddingModal}
                                        disabled={busyAction === 'bidding'}
                                        title="Edytuj cel licytacji"
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: 4,
                                            fontSize: 10, color: C.w40, background: 'transparent',
                                            border: `1px solid ${C.w10}`, borderRadius: 6, padding: '2px 6px',
                                            cursor: busyAction === 'bidding' ? 'wait' : 'pointer',
                                        }}
                                    >
                                        {selected.target_cpa_micros ? `CPA ${(selected.target_cpa_micros / 1_000_000).toFixed(2)} zł` : `ROAS ${selected.target_roas?.toFixed(2)}×`}
                                        <Pencil size={9} />
                                    </button>
                                )}
                                {/* Budget with pencil */}
                                <button
                                    onClick={openBudgetModal}
                                    disabled={busyAction === 'budget'}
                                    title="Edytuj budzet dzienny"
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 4,
                                        fontSize: 10, color: C.w40, background: 'transparent',
                                        border: `1px solid ${C.w10}`, borderRadius: 6, padding: '2px 6px',
                                        cursor: busyAction === 'budget' ? 'wait' : 'pointer',
                                    }}
                                >
                                    Budzet {((selected.budget_micros || 0) / 1_000_000).toFixed(0)} zł/d
                                    <Pencil size={9} />
                                </button>
                                {/* Pause / Enable button */}
                                <button
                                    onClick={handleToggleStatus}
                                    disabled={busyAction === 'status' || selected.status === 'REMOVED'}
                                    title={selected.status === 'ENABLED' ? 'Wstrzymaj kampanie' : 'Wznow kampanie'}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 4,
                                        fontSize: 11, fontWeight: 500,
                                        color: selected.status === 'ENABLED' ? C.warning : C.success,
                                        background: selected.status === 'ENABLED' ? C.warningBg : C.successBg,
                                        border: `1px solid ${selected.status === 'ENABLED' ? C.warning : C.success}40`,
                                        borderRadius: 8, padding: '4px 10px',
                                        cursor: busyAction === 'status' ? 'wait' : 'pointer',
                                        marginLeft: 'auto',
                                        opacity: busyAction === 'status' ? 0.5 : 1,
                                    }}
                                >
                                    {selected.status === 'ENABLED' ? <Pause size={11} /> : <Play size={11} />}
                                    {selected.status === 'ENABLED' ? 'Wstrzymaj' : 'Wznow'}
                                </button>
                            </div>
                            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                                <button
                                    onClick={() => navigate(`/keywords?campaign_id=${selected.id}&campaign_name=${encodeURIComponent(selected.name)}`)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 5,
                                        padding: '6px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                        background: C.infoBg, border: '1px solid rgba(79,142,247,0.25)',
                                        color: C.accentBlue, cursor: 'pointer',
                                    }}
                                >
                                    <KeyRound size={12} /> Słowa kluczowe
                                </button>
                                <button
                                    onClick={() => navigate(`/search-terms?campaign_id=${selected.id}&campaign_name=${encodeURIComponent(selected.name)}`)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 5,
                                        padding: '6px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                        background: 'rgba(123,92,224,0.1)', border: '1px solid rgba(123,92,224,0.25)',
                                        color: C.accentPurple, cursor: 'pointer',
                                    }}
                                >
                                    <Search size={12} /> Wyszukiwane frazy
                                </button>
                            </div>

                            <div className="v2-card" style={{ padding: showRoleCard ? '14px 18px' : '8px 14px', marginBottom: 16 }}>
                                <div className="flex items-center justify-between flex-wrap" style={{ gap: 10, marginBottom: showRoleCard ? 12 : 0 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                            Rola kampanii
                                        </div>
                                        {!showRoleCard && (
                                            <span style={{ fontSize: 11, color: C.w60 }}>
                                                {ROLE_LABELS[selected.campaign_role_final] || ROLE_LABELS[selected.campaign_role_auto] || 'Unknown'}
                                                {' · '}
                                                <span style={{ color: (PROTECTION_CONFIG[selected.protection_level] || PROTECTION_CONFIG.HIGH).color }}>
                                                    Protection {selected.protection_level || 'HIGH'}
                                                </span>
                                                {selected.role_confidence != null && (
                                                    <span style={{ color: C.w40 }}>{' · '}Confidence {Math.round(selected.role_confidence * 100)}%</span>
                                                )}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {showRoleCard && (
                                            <>
                                                <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: 'rgba(79,142,247,0.12)', color: C.accentBlue }}>
                                                    {ROLE_SOURCE_LABELS[selected.role_source] || selected.role_source || 'Auto'}
                                                </span>
                                                <span
                                                    title={PROTECTION_TOOLTIPS[selected.protection_level] || PROTECTION_TOOLTIPS.HIGH}
                                                    style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: (PROTECTION_CONFIG[selected.protection_level] || PROTECTION_CONFIG.HIGH).bg, color: (PROTECTION_CONFIG[selected.protection_level] || PROTECTION_CONFIG.HIGH).color, cursor: 'help' }}
                                                >
                                                    Protection {selected.protection_level || 'HIGH'}
                                                </span>
                                                <span style={{ fontSize: 10, color: C.textPlaceholder }}>
                                                    Confidence {selected.role_confidence != null ? `${Math.round(selected.role_confidence * 100)}%` : '—'}
                                                </span>
                                            </>
                                        )}
                                        <button
                                            onClick={() => setShowRoleCard(v => !v)}
                                            title={showRoleCard ? 'Zwin sekcje roli' : 'Rozwin sekcje roli'}
                                            style={{
                                                background: 'transparent', border: `1px solid ${C.w10}`,
                                                borderRadius: 6, padding: '3px 6px', cursor: 'pointer', color: C.w40,
                                                display: 'flex', alignItems: 'center',
                                            }}
                                        >
                                            {showRoleCard ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                        </button>
                                    </div>
                                </div>
                                {showRoleCard && (
                                <div style={{ fontSize: 11, color: C.w40, marginBottom: 10 }}>
                                    Auto-klasyfikacja jest deterministyczna. Manual override blokuje nadpisanie przez sync.
                                </div>
                                )}
                                {showRoleCard && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 220px auto auto', gap: 10, alignItems: 'end' }}>
                                    <div>
                                        <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 4 }}>
                                            Auto: <span style={{ color: C.textPrimary }}>{ROLE_LABELS[selected.campaign_role_auto] || selected.campaign_role_auto || 'Unknown'}</span>
                                        </div>
                                        <div style={{ fontSize: 11, color: C.textMuted }}>
                                            Final: <span style={{ color: C.textPrimary }}>{ROLE_LABELS[selected.campaign_role_final] || selected.campaign_role_final || 'Unknown'}</span>
                                        </div>
                                    </div>
                                    <DarkSelect
                                        value={roleDraft}
                                        onChange={(v) => setRoleDraft(v)}
                                        disabled={savingRole}
                                        options={[
                                            { value: '', label: 'Use auto classification' },
                                            ...ROLE_OPTIONS.map(role => ({ value: role, label: ROLE_LABELS[role] })),
                                        ]}
                                        placeholder="Use auto classification"
                                        style={{ minWidth: 200 }}
                                    />
                                    <button
                                        onClick={handleRoleSave}
                                        disabled={savingRole || !roleDraft}
                                        style={{
                                            height: 36,
                                            padding: '0 14px',
                                            borderRadius: 8,
                                            border: 'none',
                                            background: C.accentBlue,
                                            color: 'white',
                                            cursor: savingRole || !roleDraft ? 'not-allowed' : 'pointer',
                                            opacity: savingRole || !roleDraft ? 0.5 : 1,
                                            fontSize: 12,
                                            fontWeight: 600,
                                        }}
                                    >
                                        Save override
                                    </button>
                                    <button
                                        onClick={handleRoleReset}
                                        disabled={savingRole || selected.role_source !== 'MANUAL'}
                                        style={{
                                            height: 36,
                                            padding: '0 14px',
                                            borderRadius: 8,
                                            border: B.hover,
                                            background: 'transparent',
                                            color: C.w60,
                                            cursor: savingRole || selected.role_source !== 'MANUAL' ? 'not-allowed' : 'pointer',
                                            opacity: savingRole || selected.role_source !== 'MANUAL' ? 0.5 : 1,
                                            fontSize: 12,
                                            fontWeight: 500,
                                        }}
                                    >
                                        Reset to auto
                                    </button>
                                </div>
                                )}
                            </div>

                            {/* 1. KPI Tiles (ALL metrics) */}
                            <CampaignKpiRow kpis={kpis} campaignType={selected.campaign_type} />

                            {/* 1b. Ad Groups table */}
                            <div className="v2-card" style={{ padding: '14px 18px', marginBottom: 16 }}>
                                <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
                                    <div className="flex items-center gap-2">
                                        <Layers size={14} style={{ color: C.accentPurple }} />
                                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                            Grupy reklam ({adGroups.length})
                                        </span>
                                    </div>
                                </div>
                                {loadingAdGroups ? (
                                    <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>Ładowanie…</div>
                                ) : adGroups.length === 0 ? (
                                    <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>Brak grup reklam (lub brak metryk w zakresie dat)</div>
                                ) : (
                                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr>
                                                {['Nazwa', 'Status', 'Kliknięcia', 'Koszt', 'Konw.', 'CPA', 'ROAS'].map(h => (
                                                    <th key={h} style={{
                                                        padding: '4px 6px', fontSize: 10, fontWeight: 500,
                                                        color: C.textMuted, textTransform: 'uppercase',
                                                        letterSpacing: '0.08em', textAlign: h === 'Nazwa' || h === 'Status' ? 'left' : 'right',
                                                    }}>{h}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {adGroups.map(ag => {
                                                const sCfg = STATUS_CONFIG[ag.status] || { color: '#666', label: ag.status }
                                                return (
                                                    <tr
                                                        key={ag.id}
                                                        onClick={() => navigate(`/keywords?campaign_id=${selected.id}&ad_group_id=${ag.id}&campaign_name=${encodeURIComponent(selected.name)}`)}
                                                        style={{ borderTop: `1px solid ${C.w04}`, cursor: 'pointer' }}
                                                        className="hover:bg-white/[0.03]"
                                                    >
                                                        <td style={{ padding: '8px 6px', fontSize: 12, color: C.textPrimary }}>{ag.name}</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 11, color: sCfg.color }}>● {sCfg.label}</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{ag.clicks.toLocaleString('pl-PL')}</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{ag.cost.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{ag.conversions.toFixed(1)}</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{ag.cpa ? `${ag.cpa.toFixed(2)} zł` : '—'}</td>
                                                        <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: ag.roas >= 3 ? C.success : ag.roas >= 1 ? C.warning : C.danger }}>{ag.roas.toFixed(2)}×</td>
                                                    </tr>
                                                )
                                            })}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {/* 2. Trend Explorer — unified component scoped to this campaign */}
                            <div style={{ marginBottom: 16 }}>
                                <TrendExplorer
                                    campaignIds={[selected.id]}
                                    campaignType={selected.campaign_type}
                                    campaignName={selected.name}
                                />
                            </div>

                            {/* 3. Budget Pacing */}
                            <BudgetPacingModule
                                campaigns={budgetPacing ? [budgetPacing] : []}
                                title="Pacing budżetu"
                            />

                            {/* 4. Device + Geo Breakdown — zawsze renderowane (empty-state gdy brak danych) */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                                {/* Device */}
                                <div className="v2-card" style={{ padding: '16px 20px' }}>
                                    <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                                        <Monitor size={14} style={{ color: C.accentBlue }} />
                                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>Urządzenia</span>
                                    </div>
                                    {loadingSecondary && !deviceData ? (
                                        <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>
                                            Ładowanie…
                                        </div>
                                    ) : !deviceData?.devices?.length ? (
                                        <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>
                                            Brak danych urządzeń w wybranym okresie
                                        </div>
                                    ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                            {deviceData.devices.map(d => {
                                                const color = d.device === 'MOBILE' ? C.accentBlue : d.device === 'DESKTOP' ? C.accentPurple : C.warning
                                                return (
                                                    <div key={d.device}>
                                                        <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                                                            <span style={{ fontSize: 12, fontWeight: 500, color: C.textPrimary }}>{d.device}</span>
                                                            <span style={{ fontSize: 11, color: C.w40 }}>{d.share_clicks_pct}% kliknięć</span>
                                                        </div>
                                                        <div style={{ height: 4, borderRadius: 2, background: C.w06 }}>
                                                            <div style={{ height: '100%', borderRadius: 2, background: color, width: `${d.share_clicks_pct}%`, transition: 'width 0.3s' }} />
                                                        </div>
                                                        <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: C.textMuted }}>
                                                            <span>CTR {d.ctr}% · CPC {d.cpc?.toFixed(2)} zł</span>
                                                            <span>ROAS {d.roas}×</span>
                                                        </div>
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}
                                </div>

                                {/* Geo */}
                                <div className="v2-card" style={{ padding: '16px 20px' }}>
                                    <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                                        <MapPin size={14} style={{ color: C.accentPurple }} />
                                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>Top miasta</span>
                                    </div>
                                    {loadingSecondary && !geoData ? (
                                        <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>
                                            Ładowanie…
                                        </div>
                                    ) : !geoData?.cities?.length ? (
                                        <div style={{ fontSize: 11, color: C.w30, padding: '12px 0', textAlign: 'center' }}>
                                            Brak danych geograficznych w wybranym okresie
                                        </div>
                                    ) : (
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr>
                                                    {['Miasto', 'Kliknięcia', 'Koszt', 'ROAS'].map(h => (
                                                        <th key={h} style={{
                                                            padding: '4px 6px', fontSize: 10, fontWeight: 500,
                                                            color: C.textMuted, textTransform: 'uppercase',
                                                            letterSpacing: '0.08em', textAlign: h === 'Miasto' ? 'left' : 'right',
                                                        }}>{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {geoData.cities.slice(0, 8).map(c => (
                                                    <tr key={c.city} style={{ borderTop: `1px solid ${C.w04}` }}>
                                                        <td style={{ padding: '6px', fontSize: 12, color: C.textPrimary }}>{c.city}</td>
                                                        <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{c.clicks}</td>
                                                        <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: C.w60, textAlign: 'right' }}>{c.cost_usd?.toFixed(0)} zł</td>
                                                        <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: c.roas >= 3 ? C.success : c.roas >= 1 ? C.warning : C.danger }}>{c.roas?.toFixed(2)}×</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>
                            </div>

                            {/* 5. Auction Insights (konkurencja dla tej kampanii) */}
                            {auctionData && auctionData.length > 0 && (
                                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                                    <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                                        <Trophy size={14} style={{ color: C.accentBlue }} />
                                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                            Auction Insights — konkurencja
                                        </span>
                                    </div>
                                    <AuctionInsightsTable rows={auctionData} compact={true} limit={8} />
                                </div>
                            )}

                            {/* 6. Action History Timeline */}
                            <ActionHistoryTimeline entries={actionTimeline} />

                            {/* Loading secondary */}
                            {loadingSecondary && (
                                <div style={{ textAlign: 'center', padding: '12px 0', fontSize: 11, color: C.w30 }}>
                                    Ładowanie dodatkowych danych…
                                </div>
                            )}
                        </>
                    ) : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: C.w30, fontSize: 13 }}>
                            Wybierz kampanię z listy
                        </div>
                    )}
                </div>
            </div>

            {/* Budget edit modal */}
            {budgetModalOpen && selected && (
                <div
                    onClick={() => setBudgetModalOpen(false)}
                    style={{
                        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
                    }}
                >
                    <div
                        onClick={e => e.stopPropagation()}
                        className="v2-card"
                        style={{ padding: 24, minWidth: 360, maxWidth: 440 }}
                    >
                        <h3 style={{ fontSize: 16, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne', marginBottom: 12 }}>
                            Edytuj budzet dzienny
                        </h3>
                        <div style={{ fontSize: 11, color: C.w40, marginBottom: 16 }}>
                            Kampania: <span style={{ color: C.textPrimary }}>{selected.name}</span>
                        </div>
                        <label style={{ display: 'block', fontSize: 11, color: C.w60, marginBottom: 6 }}>Budzet dzienny (zł)</label>
                        <input
                            type="number"
                            step="0.01"
                            min="1"
                            value={budgetDraft}
                            onChange={e => setBudgetDraft(e.target.value)}
                            autoFocus
                            style={{
                                width: '100%', background: C.w06, border: `1px solid ${C.w10}`,
                                borderRadius: 8, padding: '8px 10px', fontSize: 13, color: C.textPrimary, marginBottom: 12,
                            }}
                        />
                        <div className="flex items-center gap-2" style={{ marginBottom: 16 }}>
                            {[10, 20, 50].map(pct => {
                                const oldZl = (selected.budget_micros || 0) / 1_000_000
                                const newZl = oldZl * (1 + pct / 100)
                                return (
                                    <button
                                        key={pct}
                                        onClick={() => setBudgetDraft(newZl.toFixed(2))}
                                        style={{
                                            background: C.infoBg, border: `1px solid ${C.infoBorder}`,
                                            borderRadius: 6, padding: '4px 10px', fontSize: 11,
                                            color: C.accentBlue, cursor: 'pointer',
                                        }}
                                    >
                                        +{pct}%
                                    </button>
                                )
                            })}
                        </div>
                        <div className="flex items-center justify-end gap-2">
                            <button
                                onClick={() => setBudgetModalOpen(false)}
                                style={{ background: 'transparent', border: `1px solid ${C.w10}`, borderRadius: 8, padding: '6px 14px', fontSize: 12, color: C.w60, cursor: 'pointer' }}
                            >
                                Anuluj
                            </button>
                            <button
                                onClick={handleSaveBudget}
                                disabled={busyAction === 'budget'}
                                style={{
                                    background: C.accentBlue, border: 'none', borderRadius: 8,
                                    padding: '6px 14px', fontSize: 12, fontWeight: 600, color: 'white',
                                    cursor: busyAction === 'budget' ? 'wait' : 'pointer',
                                    opacity: busyAction === 'budget' ? 0.5 : 1,
                                }}
                            >
                                Zapisz
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bidding target edit modal */}
            {biddingModalOpen && selected && (
                <div
                    onClick={() => setBiddingModalOpen(false)}
                    style={{
                        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
                    }}
                >
                    <div
                        onClick={e => e.stopPropagation()}
                        className="v2-card"
                        style={{ padding: 24, minWidth: 360, maxWidth: 440 }}
                    >
                        <h3 style={{ fontSize: 16, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne', marginBottom: 12 }}>
                            Edytuj cel licytacji
                        </h3>
                        <div style={{ fontSize: 11, color: C.w40, marginBottom: 16 }}>
                            Kampania: <span style={{ color: C.textPrimary }}>{selected.name}</span>
                            {' · '}Strategia: <span style={{ color: C.textPrimary }}>{selected.bidding_strategy}</span>
                        </div>
                        <label style={{ display: 'block', fontSize: 11, color: C.w60, marginBottom: 6 }}>
                            {selected.target_cpa_micros ? 'Target CPA (zł)' : selected.target_roas ? 'Target ROAS (×)' : 'Target CPA (zł)'}
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={biddingDraft}
                            onChange={e => setBiddingDraft(e.target.value)}
                            autoFocus
                            style={{
                                width: '100%', background: C.w06, border: `1px solid ${C.w10}`,
                                borderRadius: 8, padding: '8px 10px', fontSize: 13, color: C.textPrimary, marginBottom: 16,
                            }}
                        />
                        <div className="flex items-center justify-end gap-2">
                            <button
                                onClick={() => setBiddingModalOpen(false)}
                                style={{ background: 'transparent', border: `1px solid ${C.w10}`, borderRadius: 8, padding: '6px 14px', fontSize: 12, color: C.w60, cursor: 'pointer' }}
                            >
                                Anuluj
                            </button>
                            <button
                                onClick={handleSaveBidding}
                                disabled={busyAction === 'bidding'}
                                style={{
                                    background: C.accentBlue, border: 'none', borderRadius: 8,
                                    padding: '6px 14px', fontSize: 12, fontWeight: 600, color: 'white',
                                    cursor: busyAction === 'bidding' ? 'wait' : 'pointer',
                                    opacity: busyAction === 'bidding' ? 0.5 : 1,
                                }}
                            >
                                Zapisz
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
