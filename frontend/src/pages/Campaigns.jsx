import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
    ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
    MousePointerClick, DollarSign, Target, TrendingUp, TrendingDown,
    KeyRound, Search, BarChart3, Plus, X, Monitor, MapPin, Clock,
    Eye, Percent, ArrowUpRight, Crosshair, Wallet, Activity, ArrowDownUp, Filter,
} from 'lucide-react'
import {
    getCampaigns, getCampaignKPIs, getCampaignMetrics, updateCampaign,
    getDeviceBreakdown, getGeoBreakdown, getBudgetPacing,
    getImpressionShare, getUnifiedTimeline, getCampaignsSummary,
} from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import EmptyState from '../components/EmptyState'
import { LoadingSpinner, ErrorMessage } from '../components/UI'
import DarkSelect from '../components/DarkSelect'

// ─── Constants ───────────────────────────────────────────────────────────────
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
const METRIC_COLORS = ['#4F8EF7', '#7B5CE0', '#4ADE80', '#FBBF24', '#F87171']

const METRIC_OPTIONS = [
    { key: 'cost', label: 'Koszt (zł)', unit: 'PLN' },
    { key: 'clicks', label: 'Kliknięcia', unit: '' },
    { key: 'impressions', label: 'Wyświetlenia', unit: '' },
    { key: 'conversions', label: 'Konwersje', unit: '' },
    { key: 'conversion_value', label: 'Wartość konw.', unit: 'PLN' },
    { key: 'ctr', label: 'CTR (%)', unit: '%', tooltip: 'Click-Through Rate' },
    { key: 'avg_cpc', label: 'CPC (avg)', unit: 'PLN', tooltip: 'Średni koszt kliknięcia' },
    { key: 'roas', label: 'ROAS', unit: '', tooltip: 'Return On Ad Spend' },
    { key: 'conversion_rate', label: 'CVR (%)', unit: '%', tooltip: 'Conversion Rate' },
    { key: 'search_impression_share', label: 'Impression Share', unit: '%', searchOnly: true },
    { key: 'search_top_impression_share', label: 'Top IS', unit: '%', searchOnly: true },
    { key: 'search_abs_top_impression_share', label: 'Abs Top IS', unit: '%', searchOnly: true },
    { key: 'search_budget_lost_is', label: 'Budget Lost IS', unit: '%', searchOnly: true },
    { key: 'search_rank_lost_is', label: 'Rank Lost IS', unit: '%', searchOnly: true },
    { key: 'search_click_share', label: 'Click Share', unit: '%', searchOnly: true },
    { key: 'abs_top_impression_pct', label: 'Abs Top %', unit: '%' },
    { key: 'top_impression_pct', label: 'Top Impr %', unit: '%' },
]

// Polish labels for action operations
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

// ─── Helpers ─────────────────────────────────────────────────────────────────
function pearsonCorrelation(x, y) {
    const n = x.length
    if (n < 2) return null
    const meanX = x.reduce((a, b) => a + b, 0) / n
    const meanY = y.reduce((a, b) => a + b, 0) / n
    const num = x.reduce((sum, xi, i) => sum + (xi - meanX) * (y[i] - meanY), 0)
    const denX = Math.sqrt(x.reduce((sum, xi) => sum + (xi - meanX) ** 2, 0))
    const denY = Math.sqrt(y.reduce((sum, yi) => sum + (yi - meanY) ** 2, 0))
    if (denX === 0 || denY === 0) return null
    return num / (denX * denY)
}

function getCorrelationLabel(r) {
    if (r === null) return null
    const abs = Math.abs(r)
    const sign = r > 0 ? '+' : ''
    if (abs > 0.7) return `${sign}${r.toFixed(2)} ${r > 0 ? '↑ silna' : '↓ silna ujemna'}`
    if (abs > 0.4) return `${sign}${r.toFixed(2)} → umiarkowana`
    return `${r.toFixed(2)} ≈ brak korelacji`
}

function formatDate(dateStr) {
    const d = new Date(dateStr)
    return `${d.getDate()}.${(d.getMonth() + 1).toString().padStart(2, '0')}`
}

function formatTimestamp(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function needsDualAxis(metrics) {
    const pct = ['ctr', 'conversion_rate', 'search_impression_share', 'search_top_impression_share', 'search_abs_top_impression_share', 'search_budget_lost_is', 'search_rank_lost_is', 'search_click_share', 'abs_top_impression_pct', 'top_impression_pct']
    const hasPct = metrics.some(m => pct.includes(m))
    const hasNonPct = metrics.some(m => !pct.includes(m))
    return hasPct && hasNonPct
}

/** Parse old/new value JSON and return readable before→after string */
function formatBeforeAfter(entry) {
    const parts = []
    try {
        const oldVal = entry.old_value_json ? (typeof entry.old_value_json === 'string' ? JSON.parse(entry.old_value_json) : entry.old_value_json) : null
        const newVal = entry.new_value_json ? (typeof entry.new_value_json === 'string' ? JSON.parse(entry.new_value_json) : entry.new_value_json) : null

        if (!oldVal && !newVal) return null

        // Handle common patterns
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

        // Fallback: show raw key changes if nothing matched
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

// ─── KPI Row (ALL metrics) ──────────────────────────────────────────────────
function KpiRow({ kpis, campaignType }) {
    if (!kpis) return null
    const { current, change_pct } = kpis

    // Core metrics (always shown)
    const coreItems = [
        { label: 'Kliknięcia', key: 'clicks', icon: MousePointerClick, color: '#4F8EF7' },
        { label: 'Wyświetlenia', key: 'impressions', icon: Eye, color: '#4F8EF7' },
        { label: 'Koszt', key: 'cost', suffix: ' zł', icon: DollarSign, color: '#7B5CE0' },
        { label: 'Konwersje', key: 'conversions', icon: Target, color: '#4ADE80' },
        { label: 'Wartość konw.', key: 'conversion_value', suffix: ' zł', icon: Wallet, color: '#4ADE80' },
        { label: 'CTR', key: 'ctr', suffix: '%', icon: Percent, color: '#FBBF24', tooltip: 'Click-Through Rate' },
        { label: 'Avg CPC', key: 'avg_cpc', suffix: ' zł', icon: DollarSign, color: '#7B5CE0', tooltip: 'Średni koszt kliknięcia' },
        { label: 'CPA', key: 'cpa', suffix: ' zł', icon: Crosshair, color: '#F87171', tooltip: 'Koszt za konwersję', invertChange: true },
        { label: 'CVR', key: 'conversion_rate', suffix: '%', icon: Activity, color: '#4ADE80', tooltip: 'Conversion Rate' },
        { label: 'ROAS', key: 'roas', suffix: '×', icon: BarChart3, color: '#FBBF24', tooltip: 'Return On Ad Spend' },
    ]

    // IS metrics (SEARCH only)
    const isItems = campaignType === 'SEARCH' ? [
        { label: 'Impr. Share', key: 'search_impression_share', isPct: true, icon: ArrowUpRight, color: '#4F8EF7', tooltip: 'Udział w wyświetleniach' },
        { label: 'Top IS', key: 'search_top_impression_share', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: 'Wyśw. na górze strony' },
        { label: 'Abs Top IS', key: 'search_abs_top_impression_share', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: 'Wyśw. na samej górze' },
        { label: 'Budget Lost IS', key: 'search_budget_lost_is', isPct: true, icon: Wallet, color: '#F87171', tooltip: 'Utracone — budżet', invertChange: true },
        { label: 'Rank Lost IS', key: 'search_rank_lost_is', isPct: true, icon: TrendingDown, color: '#FBBF24', tooltip: 'Utracone — ranking', invertChange: true },
        { label: 'Click Share', key: 'search_click_share', isPct: true, icon: MousePointerClick, color: '#4F8EF7', tooltip: 'Udział w kliknięciach' },
        { label: 'Abs Top %', key: 'abs_top_impression_pct', isPct: true, icon: ArrowUpRight, color: '#4F8EF7', tooltip: '% wyśw. na 1. pozycji' },
        { label: 'Top Impr %', key: 'top_impression_pct', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: '% wyśw. na górze' },
    ] : []

    const allItems = [...coreItems, ...isItems]

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 16 }}>
            {allItems.map(({ label, key, suffix = '', icon: Icon, color, tooltip, isPct, invertChange }) => {
                const raw = current?.[key]
                // IS values from backend are 0.0-1.0 scale, display as percentage
                const value = isPct && raw != null ? +(raw * 100).toFixed(1) : raw
                const displaySuffix = isPct ? '%' : suffix
                const rawChange = change_pct?.[key]
                // For CPA and lost IS, lower is better — invert the color
                const changeForColor = invertChange ? -(rawChange || 0) : (rawChange || 0)
                const isUp = changeForColor > 0
                const isDown = changeForColor < 0

                return (
                    <div key={key} className="v2-card" style={{ padding: '10px 12px' }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                            <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', lineHeight: 1.2 }} title={tooltip || undefined}>{label}</span>
                            <div style={{ width: 20, height: 20, borderRadius: 5, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Icon size={10} style={{ color }} />
                            </div>
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1 }}>
                            {value != null ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}{value != null ? displaySuffix : ''}
                        </div>
                        {rawChange !== undefined && rawChange !== null && (
                            <div style={{ marginTop: 3, fontSize: 10, color: isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: 2 }}>
                                {isUp ? <TrendingUp size={9} /> : isDown ? <TrendingDown size={9} /> : null}
                                {rawChange > 0 ? '+' : ''}{rawChange.toFixed(1)}%
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

// ─── Campaign Trend Explorer ────────────────────────────────────────────────
function CampaignTrendExplorer({ metrics, actionEvents, campaignType }) {
    const [activeMetrics, setActiveMetrics] = useState(['cost', 'clicks'])
    const [showDropdown, setShowDropdown] = useState(false)

    const PCT_KEYS = ['ctr', 'conversion_rate', 'search_impression_share', 'search_top_impression_share', 'search_abs_top_impression_share', 'search_budget_lost_is', 'search_rank_lost_is', 'search_click_share', 'abs_top_impression_pct', 'top_impression_pct']

    // Transform MetricDaily data for chart
    const chartData = useMemo(() => {
        if (!metrics?.length) return []
        return metrics.map(m => ({
            date: m.date,
            cost: m.cost,
            clicks: m.clicks,
            impressions: m.impressions,
            conversions: m.conversions,
            conversion_value: m.conversion_value,
            ctr: m.ctr,
            avg_cpc: m.avg_cpc,
            roas: m.roas,
            conversion_rate: m.conversion_rate,
            search_impression_share: m.search_impression_share != null ? +(m.search_impression_share * 100).toFixed(1) : null,
            search_top_impression_share: m.search_top_impression_share != null ? +(m.search_top_impression_share * 100).toFixed(1) : null,
            search_abs_top_impression_share: m.search_abs_top_impression_share != null ? +(m.search_abs_top_impression_share * 100).toFixed(1) : null,
            search_budget_lost_is: m.search_budget_lost_is != null ? +(m.search_budget_lost_is * 100).toFixed(1) : null,
            search_rank_lost_is: m.search_rank_lost_is != null ? +(m.search_rank_lost_is * 100).toFixed(1) : null,
            search_click_share: m.search_click_share != null ? +(m.search_click_share * 100).toFixed(1) : null,
            abs_top_impression_pct: m.abs_top_impression_pct != null ? +(m.abs_top_impression_pct * 100).toFixed(1) : null,
            top_impression_pct: m.top_impression_pct != null ? +(m.top_impression_pct * 100).toFixed(1) : null,
        }))
    }, [metrics])

    // Group events by date
    const eventsByDate = useMemo(() => {
        const map = {}
        ;(actionEvents || []).forEach(e => {
            const d = (e.timestamp || e.executed_at || e.change_date_time || '').slice(0, 10)
            if (d) {
                if (!map[d]) map[d] = []
                map[d].push(e)
            }
        })
        return map
    }, [actionEvents])

    const eventDates = Object.keys(eventsByDate)

    // Filter metric options for campaign type
    const availableOptions = useMemo(() =>
        METRIC_OPTIONS.filter(m => !m.searchOnly || campaignType === 'SEARCH'),
    [campaignType])

    const availableToAdd = availableOptions.filter(m => !activeMetrics.includes(m.key))

    const addMetric = (key) => {
        if (activeMetrics.length >= 5 || activeMetrics.includes(key)) return
        setActiveMetrics(prev => [...prev, key])
        setShowDropdown(false)
    }
    const removeMetric = (key) => {
        if (activeMetrics.length <= 1) return
        setActiveMetrics(prev => prev.filter(m => m !== key))
    }

    // Correlation
    let correlationLabel = null
    if (activeMetrics.length >= 2 && chartData.length >= 3) {
        const x = chartData.map(d => d[activeMetrics[0]] ?? 0)
        const y = chartData.map(d => d[activeMetrics[1]] ?? 0)
        const r = pearsonCorrelation(x, y)
        correlationLabel = getCorrelationLabel(r)
    }

    const dual = needsDualAxis(activeMetrics)

    // Rich tooltip with event details
    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload?.length) return null
        const events = eventsByDate[label] || []
        return (
            <div style={{
                background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 8, padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', fontSize: 12,
                maxWidth: 320,
            }}>
                <div style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 6 }}>{label}</div>
                {payload.map((p, i) => (
                    <div key={i} style={{ color: p.color, marginBottom: 2 }}>
                        {p.name}: <strong>{p.value?.toLocaleString?.('pl-PL', { maximumFractionDigits: 2 }) ?? '—'}</strong>
                    </div>
                ))}
                {events.length > 0 && (
                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 6, paddingTop: 6 }}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Zmiany w tym dniu
                        </div>
                        {events.map((e, i) => {
                            const ts = e.timestamp || e.executed_at || e.change_date_time
                            const op = e.operation || e.action_type
                            const beforeAfter = formatBeforeAfter(e)
                            return (
                                <div key={i} style={{
                                    padding: '4px 0',
                                    borderBottom: i < events.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                                }}>
                                    <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                                        <span style={{
                                            fontSize: 8, fontWeight: 700, padding: '1px 5px', borderRadius: 999,
                                            background: e.source === 'helper' ? 'rgba(79,142,247,0.2)' : 'rgba(251,191,36,0.2)',
                                            color: e.source === 'helper' ? '#4F8EF7' : '#FBBF24',
                                        }}>
                                            {e.source === 'helper' ? 'HELPER' : 'ZEWN.'}
                                        </span>
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                                            {ts ? formatTimestamp(ts) : ''}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: 11, color: '#F0F0F0', fontWeight: 500 }}>
                                        {getOperationLabel(op)}
                                    </div>
                                    {e.entity_name && (
                                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                                            {e.entity_name}
                                        </div>
                                    )}
                                    {beforeAfter && beforeAfter.map((line, j) => (
                                        <div key={j} style={{ fontSize: 10, color: '#A78BFA', fontFamily: 'monospace' }}>
                                            {line}
                                        </div>
                                    ))}
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="v2-card" style={{ padding: '20px 24px', marginBottom: 16 }}>
            {/* Header */}
            <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div className="flex items-center gap-2">
                    <TrendingUp size={16} style={{ color: '#4F8EF7' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Trend Explorer
                    </span>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    {activeMetrics.map((key, idx) => {
                        const opt = availableOptions.find(m => m.key === key)
                        return (
                            <div key={key} className="flex items-center gap-1.5" style={{
                                background: `${METRIC_COLORS[idx]}20`, border: `1px solid ${METRIC_COLORS[idx]}40`,
                                borderRadius: 999, padding: '3px 10px 3px 12px', fontSize: 12, color: METRIC_COLORS[idx],
                            }}>
                                <span title={opt?.tooltip || undefined}>{opt?.label ?? key}</span>
                                {activeMetrics.length > 1 && (
                                    <button onClick={() => removeMetric(key)} style={{ color: 'rgba(255,255,255,0.4)', lineHeight: 1 }} className="hover:text-white/70">
                                        <X size={12} />
                                    </button>
                                )}
                            </div>
                        )
                    })}
                    {activeMetrics.length < 5 && availableToAdd.length > 0 && (
                        <div style={{ position: 'relative' }}>
                            <button onClick={() => setShowDropdown(v => !v)} style={{
                                display: 'flex', alignItems: 'center', gap: 5,
                                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: 999, padding: '3px 12px', fontSize: 12, color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
                            }} className="hover:border-white/20 hover:text-white/70">
                                <Plus size={12} /> Dodaj
                            </button>
                            {showDropdown && (
                                <div style={{
                                    position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                    background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)',
                                    borderRadius: 8, boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                                    zIndex: 50, minWidth: 180, overflow: 'hidden', maxHeight: 300, overflowY: 'auto',
                                }}>
                                    {availableToAdd.map(opt => (
                                        <button key={opt.key} onClick={() => addMetric(opt.key)} style={{
                                            display: 'block', width: '100%', textAlign: 'left',
                                            padding: '8px 14px', fontSize: 12, color: 'rgba(255,255,255,0.7)',
                                            cursor: 'pointer', background: 'transparent', border: 'none',
                                        }} className="hover:bg-white/5 hover:text-white">
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                    {correlationLabel && (
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', paddingLeft: 8, borderLeft: '1px solid rgba(255,255,255,0.08)' }}>
                            Kor. <span style={{ color: '#FBBF24' }}>{correlationLabel}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Chart */}
            {chartData.length === 0 ? (
                <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
                    Brak danych metrycznych
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={280}>
                    <ComposedChart data={chartData} margin={{ top: 4, right: dual ? 40 : 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} />
                        <YAxis yAxisId="left" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} width={45} />
                        {dual && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} axisLine={false} tickLine={false} width={40} />}
                        <Tooltip content={<CustomTooltip />} />
                        {/* Action markers — thicker, more visible */}
                        {eventDates.map(d => {
                            const isHelper = eventsByDate[d].some(e => e.source === 'helper')
                            return (
                                <ReferenceLine
                                    key={d}
                                    x={d}
                                    yAxisId="left"
                                    stroke={isHelper ? '#4F8EF7' : '#FBBF24'}
                                    strokeDasharray="6 3"
                                    strokeWidth={2}
                                    label={{
                                        value: '●',
                                        position: 'top',
                                        fill: isHelper ? '#4F8EF7' : '#FBBF24',
                                        fontSize: 14,
                                    }}
                                />
                            )
                        })}
                        {activeMetrics.map((key, idx) => {
                            const yAxis = dual && PCT_KEYS.includes(key) ? 'right' : 'left'
                            const opt = availableOptions.find(m => m.key === key)
                            return (
                                <Line
                                    key={key} yAxisId={yAxis} type="monotone" dataKey={key}
                                    name={opt?.label ?? key} stroke={METRIC_COLORS[idx]}
                                    strokeWidth={1.8} dot={false} activeDot={{ r: 4, fill: METRIC_COLORS[idx] }}
                                    connectNulls
                                />
                            )
                        })}
                    </ComposedChart>
                </ResponsiveContainer>
            )}

            {/* Legend for markers */}
            {eventDates.length > 0 && (
                <div className="flex items-center gap-4 mt-2" style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                    <span className="flex items-center gap-1"><span style={{ width: 14, height: 0, borderTop: '2px dashed #4F8EF7', display: 'inline-block' }} /> <span style={{ color: '#4F8EF7' }}>●</span> Akcja Helper</span>
                    <span className="flex items-center gap-1"><span style={{ width: 14, height: 0, borderTop: '2px dashed #FBBF24', display: 'inline-block' }} /> <span style={{ color: '#FBBF24' }}>●</span> Zmiana zewn.</span>
                </div>
            )}
        </div>
    )
}

// ─── Action History Timeline ────────────────────────────────────────────────
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

// ─── Main Component ──────────────────────────────────────────────────────────
export default function Campaigns() {
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
                                            Confidence {selected.role_confidence != null ? `${Math.round(selected.role_confidence * 100)}%` : '�'}
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
                            <KpiRow kpis={kpis} campaignType={selected.campaign_type} />

                            {/* 2. Trend Explorer */}
                            <CampaignTrendExplorer
                                metrics={metrics}
                                actionEvents={actionTimeline}
                                campaignType={selected.campaign_type}
                            />

                            {/* 3. Budget Pacing */}
                            {budgetPacing && (
                                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 10, fontFamily: 'Syne' }}>
                                        Pacing budżetu
                                    </div>
                                    {(() => {
                                        const c = budgetPacing
                                        const color = c.status === 'overspend' ? '#F87171' : c.status === 'underspend' ? '#FBBF24' : '#4ADE80'
                                        const bg = c.status === 'overspend' ? 'rgba(248,113,113,0.08)' : c.status === 'underspend' ? 'rgba(251,191,36,0.08)' : 'rgba(74,222,128,0.08)'
                                        const label = c.status === 'overspend' ? 'Przekroczenie' : c.status === 'underspend' ? 'Niedostateczne' : 'Na torze'
                                        return (
                                            <div>
                                                <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                                                    <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                                                        {c.actual_spend_usd?.toFixed(0)} / {c.expected_spend_usd?.toFixed(0)} zł (proj. {c.projected_spend_usd?.toFixed(0)} zł)
                                                    </span>
                                                    <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: bg, color, border: `1px solid ${color}30` }}>
                                                        {label}
                                                    </span>
                                                </div>
                                                <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.06)' }}>
                                                    <div style={{ height: '100%', borderRadius: 3, background: color, width: `${Math.min(c.pacing_pct, 100)}%`, transition: 'width 0.3s' }} />
                                                </div>
                                                <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                                                    <span>Dzień {c.days_elapsed} / {c.days_in_month}</span>
                                                    <span style={{ color }}>{c.pacing_pct}%</span>
                                                </div>
                                            </div>
                                        )
                                    })()}
                                </div>
                            )}

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





