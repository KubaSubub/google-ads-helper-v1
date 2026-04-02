import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    KeyRound, Search, Monitor, MapPin, Clock,
    Filter, X, ArrowDownUp,
} from 'lucide-react'
import {
    getCampaigns, getCampaignKPIs, getCampaignMetrics, updateCampaign,
    getDeviceBreakdown, getGeoBreakdown, getBudgetPacing,
    getUnifiedTimeline, getCampaignsSummary,
} from '../../api'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import EmptyState from '../../components/EmptyState'
import { LoadingSpinner, ErrorMessage } from '../../components/UI'
import { BudgetPacingModule } from '../../components/modules'
import DarkSelect from '../../components/DarkSelect'
import CampaignKpiRow from './components/CampaignKpiRow'
import CampaignTrendExplorer from './components/CampaignTrendExplorer'

// ─── Constants ────────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
    ENABLED: { dot: '#4ADE80', color: '#4ADE80', label: 'Aktywna' },
    PAUSED: { dot: '#FBBF24', color: '#FBBF24', label: 'Wstrzymana' },
    REMOVED: { dot: '#F87171', color: '#F87171', label: 'Usunięta' },
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
    HIGH: { color: '#F87171', bg: 'rgba(248,113,113,0.12)' },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)' },
    LOW: { color: '#4ADE80', bg: 'rgba(74,222,128,0.12)' },
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
                <Clock size={14} style={{ color: '#4F8EF7' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                    Historia zmian ({entries.length})
                </span>
            </div>
            <div style={{ maxHeight: 360, overflowY: 'auto' }}>
                {entries.map((entry, i) => {
                    const isHelper = entry.source === 'helper'
                    const borderColor = isHelper ? '#4F8EF7' : 'rgba(255,255,255,0.12)'
                    const ts = entry.timestamp || entry.executed_at || entry.change_date_time
                    const op = entry.operation || entry.action_type
                    const beforeAfter = formatBeforeAfter(entry)

                    return (
                        <div key={entry.action_log_id || entry.change_event_id || i} style={{
                            display: 'flex', gap: 10, paddingLeft: 12, paddingBottom: 10, marginBottom: 10,
                            borderLeft: `2px solid ${borderColor}`,
                            borderBottom: i < entries.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                        }}>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div className="flex items-center gap-2" style={{ marginBottom: 3 }}>
                                    <span style={{
                                        fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                        background: isHelper ? 'rgba(79,142,247,0.15)' : 'rgba(251,191,36,0.15)',
                                        color: isHelper ? '#4F8EF7' : '#FBBF24',
                                    }}>
                                        {isHelper ? 'HELPER' : 'ZEWN.'}
                                    </span>
                                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                                        {ts ? formatTimestamp(ts) : ''}
                                    </span>
                                </div>
                                <div style={{ fontSize: 12, color: '#F0F0F0', fontWeight: 500, marginBottom: 2 }}>
                                    {getOperationLabel(op)}
                                </div>
                                {entry.entity_name && (
                                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 2 }}>
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
    const [metrics, setMetrics] = useState([])
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
    const [budgetPacing, setBudgetPacing] = useState(null)
    const [actionTimeline, setActionTimeline] = useState([])
    const [loadingSecondary, setLoadingSecondary] = useState(false)
    const [roleDraft, setRoleDraft] = useState('')
    const [savingRole, setSavingRole] = useState(false)

    useEffect(() => {
        if (selectedClientId) loadCampaigns()
    }, [selectedClientId, campaignParams, allParams])

    async function loadCampaigns() {
        setLoading(true)
        try {
            const [data, summaryData] = await Promise.all([
                getCampaigns(selectedClientId, campaignParams),
                getCampaignsSummary(selectedClientId, allParams).catch(() => ({ campaigns: {} })),
            ])
            const items = data.items || []
            setCampaigns(items)
            setCampSummary(summaryData?.campaigns || {})
            if (items.length > 0) selectCampaign(items[0])
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const selectCampaign = useCallback(async (campaign) => {
        setSelected(campaign)
        setKpis(null)
        setMetrics([])
        setDeviceData(null)
        setGeoData(null)
        setBudgetPacing(null)
        setActionTimeline([])

        try {
            const [kpiData, metricData] = await Promise.all([
                getCampaignKPIs(campaign.id, null, dateParams).catch(() => null),
                getCampaignMetrics(campaign.id, filters.dateFrom, filters.dateTo).catch(() => []),
            ])
            setKpis(kpiData)
            setMetrics(metricData)
        } catch (err) {
            console.error('Failed to load campaign details:', err)
        }

        // Secondary data (non-blocking)
        setLoadingSecondary(true)
        Promise.all([
            getDeviceBreakdown(selectedClientId, { ...allParams, campaign_id: campaign.id }).catch(() => null),
            getGeoBreakdown(selectedClientId, { ...allParams, campaign_id: campaign.id }).catch(() => null),
            getBudgetPacing(selectedClientId, campaignParams).catch(() => null),
            getUnifiedTimeline(selectedClientId, { limit: 200 }).catch(() => ({ entries: [] })),
        ]).then(([dev, geo, bp, timeline]) => {
            setDeviceData(dev)
            setGeoData(geo)
            const thisCampPacing = bp?.campaigns?.find(c => c.campaign_id === campaign.id)
            setBudgetPacing(thisCampPacing)
            const filtered = (timeline?.entries || []).filter(e => e.campaign_name === campaign.name)
            setActionTimeline(filtered)
            setLoadingSecondary(false)
        })
    }, [selectedClientId, allParams, dateParams, campaignParams])

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
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Kampanie
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {filteredCampaigns.length} z {campaigns.length} kampanii
                    </p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
                {/* Campaign list */}
                <div className="v2-card" style={{ padding: 6, maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
                    {/* Sort & Filter toolbar */}
                    <div style={{ padding: '6px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 4 }}>
                        <div className="flex items-center gap-2" style={{ marginBottom: showFilter ? 8 : 0 }}>
                            <select
                                value={sortBy}
                                onChange={e => setSortBy(e.target.value)}
                                style={{
                                    flex: 1, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: 6, padding: '4px 6px', fontSize: 10, color: '#F0F0F0', cursor: 'pointer',
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
                                    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: 6, padding: '4px 6px', cursor: 'pointer', color: '#F0F0F0', fontSize: 10,
                                }}
                            >
                                {sortDir === 'desc' ? '↓' : '↑'}
                            </button>
                            <button
                                onClick={() => setShowFilter(v => !v)}
                                title="Filtruj po metryce"
                                style={{
                                    background: showFilter ? 'rgba(79,142,247,0.15)' : 'rgba(255,255,255,0.06)',
                                    border: `1px solid ${showFilter ? 'rgba(79,142,247,0.3)' : 'rgba(255,255,255,0.1)'}`,
                                    borderRadius: 6, padding: '4px 6px', cursor: 'pointer',
                                    color: showFilter ? '#4F8EF7' : '#F0F0F0',
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
                                        flex: 1, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 6, padding: '4px 6px', fontSize: 10, color: '#F0F0F0', cursor: 'pointer',
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
                                        width: 36, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 6, padding: '4px 4px', fontSize: 10, color: '#F0F0F0', cursor: 'pointer',
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
                                        width: 52, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: 6, padding: '4px 6px', fontSize: 10, color: '#F0F0F0',
                                    }}
                                />
                                {metricFilter.field && (
                                    <button
                                        onClick={() => setMetricFilter({ field: null, op: 'gte', value: '' })}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.35)', padding: 0 }}
                                    >
                                        <X size={11} />
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {filteredCampaigns.length === 0 ? (
                        <div style={{ padding: '24px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
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
                                    border: `1px solid ${active ? 'rgba(79,142,247,0.3)' : 'transparent'}`,
                                    cursor: 'pointer', display: 'block', marginBottom: 2,
                                    borderLeft: active ? '2px solid #4F8EF7' : '2px solid transparent',
                                }}
                                className={active ? '' : 'hover:bg-white/[0.04]'}
                            >
                                <div className="flex items-center justify-between gap-2" style={{ marginBottom: 4 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {c.name}
                                    </span>
                                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: sCfg.dot, flexShrink: 0 }} />
                                </div>
                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', display: 'flex', gap: 6 }}>
                                    <span>{TYPE_LABELS[c.campaign_type] ?? c.campaign_type}</span>
                                    <span>·</span>
                                    <span>{c.budget_usd?.toFixed(0)} zł/d</span>
                                </div>
                                {cm && (
                                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', display: 'flex', gap: 8, marginTop: 4 }}>
                                        <span>{cm.cost_usd?.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł</span>
                                        <span>{cm.conversions?.toFixed(1)} conv</span>
                                        <span style={{ color: (cm.roas ?? 0) >= 3 ? '#4ADE80' : (cm.roas ?? 0) >= 1 ? '#FBBF24' : '#F87171' }}>
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
                            <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0' }}>{selected.name}</span>
                                {(() => {
                                    const sCfg = STATUS_CONFIG[selected.status] || { color: '#666', label: selected.status }
                                    return <span style={{ fontSize: 11, color: sCfg.color }}>● {sCfg.label}</span>
                                })()}
                                {selected.bidding_strategy && (
                                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginLeft: 4 }}>
                                        {selected.bidding_strategy}
                                        {selected.target_cpa_micros ? ` · CPA ${(selected.target_cpa_micros / 1000000).toFixed(2)} zł` : ''}
                                        {selected.target_roas ? ` · ROAS ${selected.target_roas}` : ''}
                                    </span>
                                )}
                            </div>
                            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                                <button
                                    onClick={() => navigate(`/keywords?campaign_id=${selected.id}&campaign_name=${encodeURIComponent(selected.name)}`)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 5,
                                        padding: '6px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                        background: 'rgba(79,142,247,0.1)', border: '1px solid rgba(79,142,247,0.25)',
                                        color: '#4F8EF7', cursor: 'pointer',
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
                                        color: '#7B5CE0', cursor: 'pointer',
                                    }}
                                >
                                    <Search size={12} /> Wyszukiwane frazy
                                </button>
                            </div>

                            <div className="v2-card" style={{ padding: '14px 18px', marginBottom: 16 }}>
                                <div className="flex items-center justify-between flex-wrap" style={{ gap: 10, marginBottom: 12 }}>
                                    <div>
                                        <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                                            Rola kampanii
                                        </div>
                                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
                                            Auto-klasyfikacja jest deterministyczna. Manual override blokuje nadpisanie przez sync.
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: 'rgba(79,142,247,0.12)', color: '#4F8EF7' }}>
                                            {ROLE_SOURCE_LABELS[selected.role_source] || selected.role_source || 'Auto'}
                                        </span>
                                        <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: (PROTECTION_CONFIG[selected.protection_level] || PROTECTION_CONFIG.HIGH).bg, color: (PROTECTION_CONFIG[selected.protection_level] || PROTECTION_CONFIG.HIGH).color }}>
                                            Protection {selected.protection_level || 'HIGH'}
                                        </span>
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)' }}>
                                            Confidence {selected.role_confidence != null ? `${Math.round(selected.role_confidence * 100)}%` : '—'}
                                        </span>
                                    </div>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 220px auto auto', gap: 10, alignItems: 'end' }}>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>
                                            Auto: <span style={{ color: '#F0F0F0' }}>{ROLE_LABELS[selected.campaign_role_auto] || selected.campaign_role_auto || 'Unknown'}</span>
                                        </div>
                                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>
                                            Final: <span style={{ color: '#F0F0F0' }}>{ROLE_LABELS[selected.campaign_role_final] || selected.campaign_role_final || 'Unknown'}</span>
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
                                            background: '#4F8EF7',
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
                                            border: '1px solid rgba(255,255,255,0.12)',
                                            background: 'transparent',
                                            color: 'rgba(255,255,255,0.6)',
                                            cursor: savingRole || selected.role_source !== 'MANUAL' ? 'not-allowed' : 'pointer',
                                            opacity: savingRole || selected.role_source !== 'MANUAL' ? 0.5 : 1,
                                            fontSize: 12,
                                            fontWeight: 500,
                                        }}
                                    >
                                        Reset to auto
                                    </button>
                                </div>
                            </div>

                            {/* 1. KPI Tiles (ALL metrics) */}
                            <CampaignKpiRow kpis={kpis} campaignType={selected.campaign_type} />

                            {/* 2. Trend Explorer */}
                            <CampaignTrendExplorer
                                metrics={metrics}
                                actionEvents={actionTimeline}
                                campaignType={selected.campaign_type}
                            />

                            {/* 3. Budget Pacing */}
                            <BudgetPacingModule
                                campaigns={budgetPacing ? [budgetPacing] : []}
                                title="Pacing budżetu"
                            />

                            {/* 4. Device + Geo Breakdown */}
                            {(deviceData?.devices?.length > 0 || geoData?.cities?.length > 0) && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                                    {/* Device */}
                                    {deviceData?.devices?.length > 0 && (
                                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                                            <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                                                <Monitor size={14} style={{ color: '#4F8EF7' }} />
                                                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>Urządzenia</span>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                                {deviceData.devices.map(d => {
                                                    const color = d.device === 'MOBILE' ? '#4F8EF7' : d.device === 'DESKTOP' ? '#7B5CE0' : '#FBBF24'
                                                    return (
                                                        <div key={d.device}>
                                                            <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                                                                <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0' }}>{d.device}</span>
                                                                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{d.share_clicks_pct}% kliknięć</span>
                                                            </div>
                                                            <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                                                                <div style={{ height: '100%', borderRadius: 2, background: color, width: `${d.share_clicks_pct}%`, transition: 'width 0.3s' }} />
                                                            </div>
                                                            <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                                                                <span>CTR {d.ctr}% · CPC {d.cpc?.toFixed(2)} zł</span>
                                                                <span>ROAS {d.roas}×</span>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Geo */}
                                    {geoData?.cities?.length > 0 && (
                                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                                            <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                                                <MapPin size={14} style={{ color: '#7B5CE0' }} />
                                                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>Top miasta</span>
                                            </div>
                                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                                <thead>
                                                    <tr>
                                                        {['Miasto', 'Kliknięcia', 'Koszt', 'ROAS'].map(h => (
                                                            <th key={h} style={{
                                                                padding: '4px 6px', fontSize: 10, fontWeight: 500,
                                                                color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
                                                                letterSpacing: '0.08em', textAlign: h === 'Miasto' ? 'left' : 'right',
                                                            }}>{h}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {geoData.cities.slice(0, 8).map(c => (
                                                        <tr key={c.city} style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                                                            <td style={{ padding: '6px', fontSize: 12, color: '#F0F0F0' }}>{c.city}</td>
                                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.clicks}</td>
                                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)', textAlign: 'right' }}>{c.cost_usd?.toFixed(0)} zł</td>
                                                            <td style={{ padding: '6px', fontSize: 12, fontFamily: 'monospace', textAlign: 'right', color: c.roas >= 3 ? '#4ADE80' : c.roas >= 1 ? '#FBBF24' : '#F87171' }}>{c.roas?.toFixed(2)}×</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* 5. Action History Timeline */}
                            <ActionHistoryTimeline entries={actionTimeline} />

                            {/* Loading secondary */}
                            {loadingSecondary && (
                                <div style={{ textAlign: 'center', padding: '12px 0', fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                    Ładowanie dodatkowych danych…
                                </div>
                            )}
                        </>
                    ) : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>
                            Wybierz kampanię z listy
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
