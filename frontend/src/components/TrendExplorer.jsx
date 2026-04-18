import { memo, useState, useEffect, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip,
    ResponsiveContainer, CartesianGrid, ReferenceLine, Brush,
} from 'recharts'
import { Plus, X, TrendingUp, Settings, Save, Layers, ChevronDown, ChevronUp, Maximize2, Minimize2, ArrowRight } from 'lucide-react'
import { getCorrelationMatrix, getTrends, getTrendsByDevice, getUnifiedTimeline } from '../api'
import { useFilter } from '../contexts/FilterContext'
import { useApp } from '../contexts/AppContext'
import { C, B } from '../constants/designTokens'
import {
    rollingCorrelation,
    forecastPoints,
    computeDelta,
    mergePeriodOverPeriod,
    loadPresets,
    savePreset,
    deletePreset,
    BUILT_IN_PRESETS,
} from './trendExplorerUtils'

const METRIC_COLORS = [C.accentBlue, C.accentPurple, C.success, C.warning, C.danger, '#06B6D4', '#EC4899']
const MAX_METRICS = 7
const DEVICE_COLORS = { MOBILE: '#4F8EF7', DESKTOP: '#7B5CE0', TABLET: '#FBBF24', OTHER: '#9CA3AF' }

// Unified metric set shared by Dashboard (aggregated) and Campaigns (per-campaign).
const METRIC_OPTIONS = [
    { key: 'cost', label: 'Koszt (zł)', unit: 'PLN' },
    { key: 'clicks', label: 'Kliknięcia', unit: '' },
    { key: 'impressions', label: 'Wyświetlenia', unit: '' },
    { key: 'conversions', label: 'Konwersje', unit: '' },
    { key: 'conversion_value', label: 'Wartość konw.', unit: 'PLN' },
    { key: 'ctr', label: 'CTR (%)', unit: '%', tooltip: 'Click-Through Rate' },
    { key: 'cpc', label: 'CPC (avg)', unit: 'PLN', tooltip: 'Średni koszt kliknięcia' },
    { key: 'cpa', label: 'CPA', unit: 'PLN', tooltip: 'Koszt pozyskania konwersji' },
    { key: 'cvr', label: 'CVR (%)', unit: '%', tooltip: 'Conversion Rate' },
    { key: 'roas', label: 'ROAS', unit: '', tooltip: 'Return On Ad Spend' },
    { key: 'search_impression_share', label: 'Impression Share', unit: '%', searchOnly: true },
    { key: 'search_top_impression_share', label: 'Top IS', unit: '%', searchOnly: true },
    { key: 'search_abs_top_impression_share', label: 'Abs Top IS', unit: '%', searchOnly: true },
    { key: 'search_budget_lost_is', label: 'Budget Lost IS', unit: '%', searchOnly: true },
    { key: 'search_rank_lost_is', label: 'Rank Lost IS', unit: '%', searchOnly: true },
    { key: 'search_click_share', label: 'Click Share', unit: '%', searchOnly: true },
    { key: 'abs_top_impression_pct', label: 'Abs Top %', unit: '%' },
    { key: 'top_impression_pct', label: 'Top Impr %', unit: '%' },
]
const METRIC_LABELS = Object.fromEntries(METRIC_OPTIONS.map(m => [m.key, m.label]))

const PCT_KEYS = new Set([
    'ctr', 'cvr',
    'search_impression_share', 'search_top_impression_share', 'search_abs_top_impression_share',
    'search_budget_lost_is', 'search_rank_lost_is', 'search_click_share',
    'abs_top_impression_pct', 'top_impression_pct',
])
const MONEY_KEYS = new Set(['cost', 'cpc', 'cpa', 'conversion_value'])

function getCorrelationLabel(r) {
    if (r === null || r === undefined) return null
    const abs = Math.abs(r)
    const sign = r > 0 ? '+' : ''
    if (abs > 0.7) return r > 0 ? `${sign}${r.toFixed(2)} ↑ silna dodatnia` : `${r.toFixed(2)} ↓ silna ujemna`
    if (abs > 0.4) return r > 0 ? `${sign}${r.toFixed(2)} → umiarkowana dodatnia` : `${r.toFixed(2)} → umiarkowana ujemna`
    return `${r.toFixed(2)} ≈ słaba / brak`
}

function formatDate(dateStr) {
    const d = new Date(dateStr)
    return `${d.getDate()}.${(d.getMonth() + 1).toString().padStart(2, '0')}`
}

function needsDualAxis(metrics) {
    const hasPct = metrics.some(m => PCT_KEYS.has(m))
    const hasMoney = metrics.some(m => MONEY_KEYS.has(m))
    const hasCount = metrics.some(m => !PCT_KEYS.has(m) && !MONEY_KEYS.has(m))
    return (hasPct && (hasMoney || hasCount)) || (hasMoney && hasCount)
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
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatBeforeAfter(entry) {
    const parts = []
    try {
        const oldVal = entry.old_value_json ? (typeof entry.old_value_json === 'string' ? JSON.parse(entry.old_value_json) : entry.old_value_json) : null
        const newVal = entry.new_value_json ? (typeof entry.new_value_json === 'string' ? JSON.parse(entry.new_value_json) : entry.new_value_json) : null
        if (!oldVal && !newVal) return null
        if (oldVal?.bid_micros !== undefined || newVal?.bid_micros !== undefined) {
            const o = oldVal?.bid_micros != null ? (oldVal.bid_micros / 1_000_000).toFixed(2) : '—'
            const n = newVal?.bid_micros != null ? (newVal.bid_micros / 1_000_000).toFixed(2) : '—'
            parts.push(`Stawka: ${o} → ${n} zł`)
        }
        if (oldVal?.budget_micros !== undefined || newVal?.budget_micros !== undefined) {
            const o = oldVal?.budget_micros != null ? (oldVal.budget_micros / 1_000_000).toFixed(0) : '—'
            const n = newVal?.budget_micros != null ? (newVal.budget_micros / 1_000_000).toFixed(0) : '—'
            parts.push(`Budżet: ${o} → ${n} zł`)
        }
        if (oldVal?.status !== undefined || newVal?.status !== undefined) {
            const pl = { ENABLED: 'Aktywny', PAUSED: 'Wstrzymany', REMOVED: 'Usunięty' }
            parts.push(`Status: ${pl[oldVal?.status] || oldVal?.status || '—'} → ${pl[newVal?.status] || newVal?.status || '—'}`)
        }
    } catch { return null }
    return parts.length > 0 ? parts : null
}

// Shift a date string by N days
function shiftDate(dateStr, deltaDays) {
    const d = new Date(dateStr)
    d.setDate(d.getDate() + deltaDays)
    return d.toISOString().slice(0, 10)
}

// Full list of actions in the selected period. Shown under the chart as an
// expandable panel so users aren't capped at the 3 events shown in the tooltip.
function ActionsDrawer({ events, eventsByDate, actionsFilter, setActionsFilter, onRowClick }) {
    const opTypes = useMemo(() => {
        const set = new Set()
        events.forEach(e => { const op = e.operation || e.action_type; if (op) set.add(op) })
        return Array.from(set).sort()
    }, [events])

    const filteredDates = useMemo(() => {
        const dates = Object.keys(eventsByDate).sort((a, b) => b.localeCompare(a))
        if (actionsFilter === 'ALL') return dates
        return dates
            .map(d => [d, eventsByDate[d].filter(e => (e.operation || e.action_type) === actionsFilter)])
            .filter(([, list]) => list.length > 0)
            .map(([d]) => d)
    }, [eventsByDate, actionsFilter])

    const rowsForDate = (d) => {
        const list = eventsByDate[d] || []
        return actionsFilter === 'ALL' ? list : list.filter(e => (e.operation || e.action_type) === actionsFilter)
    }

    return (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: B.subtle }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                <button
                    onClick={() => setActionsFilter('ALL')}
                    style={{
                        fontSize: 10, padding: '3px 10px', borderRadius: 999,
                        background: actionsFilter === 'ALL' ? 'rgba(79,142,247,0.15)' : C.w04,
                        border: actionsFilter === 'ALL' ? '1px solid rgba(79,142,247,0.4)' : B.subtle,
                        color: actionsFilter === 'ALL' ? C.accentBlue : C.w60,
                        cursor: 'pointer',
                    }}
                >
                    Wszystkie ({events.length})
                </button>
                {opTypes.map(op => {
                    const count = events.filter(e => (e.operation || e.action_type) === op).length
                    const active = actionsFilter === op
                    return (
                        <button
                            key={op}
                            onClick={() => setActionsFilter(op)}
                            style={{
                                fontSize: 10, padding: '3px 10px', borderRadius: 999,
                                background: active ? 'rgba(79,142,247,0.15)' : C.w04,
                                border: active ? '1px solid rgba(79,142,247,0.4)' : B.subtle,
                                color: active ? C.accentBlue : C.w60,
                                cursor: 'pointer',
                            }}
                        >
                            {getOperationLabel(op)} ({count})
                        </button>
                    )
                })}
            </div>

            <div style={{ maxHeight: 220, overflowY: 'auto', fontSize: 11 }}>
                {filteredDates.length === 0 ? (
                    <div style={{ padding: '20px 0', textAlign: 'center', color: C.w30, fontStyle: 'italic' }}>
                        Brak akcji dla tego filtra
                    </div>
                ) : filteredDates.map(d => (
                    <div key={d} style={{ marginBottom: 10 }}>
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            fontSize: 10, color: C.w40, textTransform: 'uppercase',
                            letterSpacing: '0.05em', marginBottom: 4, fontWeight: 600,
                        }}>
                            {d}
                            <button
                                onClick={() => onRowClick(d)}
                                title="Otwórz w Action History"
                                style={{
                                    fontSize: 10, color: C.accentBlue,
                                    background: 'transparent', border: 'none', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', gap: 3,
                                }}
                            >
                                Historia <ArrowRight size={10} />
                            </button>
                        </div>
                        {rowsForDate(d).map((e, i) => {
                            const op = e.operation || e.action_type
                            const isHelper = e.source !== 'external'
                            const beforeAfter = formatBeforeAfter(e)
                            const ts = e.timestamp || e.executed_at
                            return (
                                <div
                                    key={i}
                                    onClick={() => onRowClick(d)}
                                    style={{
                                        display: 'grid',
                                        gridTemplateColumns: '50px 1fr auto',
                                        gap: 10, alignItems: 'center',
                                        padding: '6px 8px', borderRadius: 6,
                                        background: C.w03, marginBottom: 3,
                                        cursor: 'pointer',
                                    }}
                                    className="hover:bg-white/5"
                                >
                                    <span style={{
                                        fontSize: 8, fontWeight: 700, padding: '2px 6px', borderRadius: 999,
                                        background: isHelper ? 'rgba(79,142,247,0.2)' : 'rgba(251,191,36,0.2)',
                                        color: isHelper ? '#4F8EF7' : '#FBBF24',
                                        textAlign: 'center',
                                    }}>
                                        {isHelper ? 'HELPER' : 'ZEWN.'}
                                    </span>
                                    <div style={{ minWidth: 0 }}>
                                        <div style={{ color: C.textPrimary, fontWeight: 500, fontSize: 11 }}>
                                            {getOperationLabel(op)}
                                        </div>
                                        {e.entity_name && (
                                            <div style={{ color: C.w40, fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {e.entity_name}
                                            </div>
                                        )}
                                        {beforeAfter && beforeAfter.map((line, j) => (
                                            <div key={j} style={{ fontSize: 10, color: '#A78BFA', fontFamily: 'monospace' }}>{line}</div>
                                        ))}
                                    </div>
                                    <span style={{ fontSize: 9, color: C.w30, whiteSpace: 'nowrap' }}>
                                        {ts ? formatTimestamp(ts) : ''}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                ))}
            </div>
        </div>
    )
}

/**
 * Unified Trend Explorer — used in both Dashboard (aggregated) and Campaigns (scoped).
 *
 * Props:
 *   campaignIds?: number[]   — restrict to these campaigns
 *   campaignType?: string    — non-SEARCH hides search-only metrics
 *   campaignName?: string    — filter action markers to that campaign
 */
function TrendExplorer({ campaignIds = [], campaignType = null, campaignName = null }) {
    const navigate = useNavigate()
    const { selectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [activeMetrics, setActiveMetrics] = useState(['cost', 'clicks'])
    const [showDropdown, setShowDropdown] = useState(false)
    const [showOptions, setShowOptions] = useState(false)
    const [showPresetsMenu, setShowPresetsMenu] = useState(false)
    const [data, setData] = useState([])
    const [prevData, setPrevData] = useState([])
    const [deviceData, setDeviceData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState(null)
    const [isMock, setIsMock] = useState(false)
    const [correlationData, setCorrelationData] = useState(null)
    const [showCorrelationPopup, setShowCorrelationPopup] = useState(false)
    const [actionEvents, setActionEvents] = useState([])
    const [deltaPopup, setDeltaPopup] = useState(null) // { date, metrics, delta }
    const [presetsVersion, setPresetsVersion] = useState(0)
    const [showActionsDrawer, setShowActionsDrawer] = useState(false)
    const [actionsFilter, setActionsFilter] = useState('ALL') // operation filter
    const [fullscreen, setFullscreen] = useState(false)
    // When a preset is loaded we remember its name so the guidance panel stays
    // visible. Any manual edit (metric add/remove, option toggle) clears it —
    // a preset's guidance only makes sense while its exact combo is on screen.
    const [activePresetName, setActivePresetName] = useState(null)

    // Lock background scroll and hook ESC while fullscreen is open, so the
    // modal feels like a real modal instead of a co-existing tall element.
    useEffect(() => {
        if (!fullscreen) return
        const prev = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        const onKey = (e) => { if (e.key === 'Escape') setFullscreen(false) }
        window.addEventListener('keydown', onKey)
        return () => {
            document.body.style.overflow = prev
            window.removeEventListener('keydown', onKey)
        }
    }, [fullscreen])

    // Display options (persist in component state, optionally saved in preset)
    const [options, setOptions] = useState({
        showDots: false,
        showForecast: false,
        showRollingCorrelation: false,
        showPeriodOverPeriod: false,
        showZoomBrush: false,
        showDeviceSegmentation: false,
        showActionMarkers: true,  // default on — killer feature; off when chart is crowded
    })
    const toggleOption = (key) => {
        setOptions(o => ({ ...o, [key]: !o[key] }))
        setActivePresetName(null)
    }

    const variant = (campaignIds && campaignIds.length > 0) ? 'campaigns' : 'dashboard'

    const campaignIdsKey = useMemo(() => (campaignIds || []).join(','), [campaignIds])
    const userPresets = useMemo(() => loadPresets(), [presetsVersion])
    // Hide Search-only built-ins for non-SEARCH campaigns to avoid presenting metrics
    // that will be empty.
    const builtInPresets = useMemo(() => {
        if (!campaignType || campaignType === 'SEARCH') return BUILT_IN_PRESETS
        return Object.fromEntries(
            Object.entries(BUILT_IN_PRESETS).filter(([, p]) => !p.searchOnly)
        )
    }, [campaignType])

    // Filter metric options: non-SEARCH campaign type hides search-only
    const availableOptions = useMemo(() => {
        if (campaignType && campaignType !== 'SEARCH') {
            return METRIC_OPTIONS.filter(m => !m.searchOnly)
        }
        return METRIC_OPTIONS
    }, [campaignType])

    useEffect(() => {
        const allowed = new Set(availableOptions.map(m => m.key))
        setActiveMetrics(prev => {
            const filtered = prev.filter(m => allowed.has(m))
            return filtered.length > 0 ? filtered : ['cost', 'clicks']
        })
    }, [availableOptions])

    // ─── Main data fetch ──────────────────────────────────────────────────────
    const fetchData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        setLoadError(null)
        try {
            const baseParams = {
                metrics: activeMetrics.join(','),
                date_from: filters.dateFrom,
                date_to: filters.dateTo,
            }
            if (campaignIdsKey) {
                baseParams.campaign_ids = campaignIdsKey
            } else {
                if (filters.campaignType !== 'ALL') baseParams.campaign_type = filters.campaignType
                if (filters.status !== 'ALL') baseParams.status = filters.status
            }

            const fetches = [getTrends(selectedClientId, baseParams)]

            // Period-over-period: fetch the previous period aligned day-for-day
            if (options.showPeriodOverPeriod && filters.dateFrom && filters.dateTo) {
                const from = new Date(filters.dateFrom)
                const to = new Date(filters.dateTo)
                const span = Math.round((to - from) / 86400000)
                const prevParams = {
                    ...baseParams,
                    date_from: shiftDate(filters.dateFrom, -(span + 1)),
                    date_to: shiftDate(filters.dateTo, -(span + 1)),
                }
                fetches.push(getTrends(selectedClientId, prevParams).catch(() => ({ data: [] })))
            } else {
                fetches.push(Promise.resolve({ data: [] }))
            }

            // Device segmentation on the first active metric
            if (options.showDeviceSegmentation) {
                const devParams = {
                    metric: activeMetrics[0],
                    date_from: filters.dateFrom,
                    date_to: filters.dateTo,
                }
                if (campaignIdsKey) devParams.campaign_ids = campaignIdsKey
                fetches.push(getTrendsByDevice(selectedClientId, devParams).catch(() => null))
            } else {
                fetches.push(Promise.resolve(null))
            }

            const [trendResult, prevResult, devResult] = await Promise.all(fetches)
            setData(trendResult.data || [])
            setPrevData(prevResult?.data || [])
            setDeviceData(devResult?.devices || null)
            setIsMock(trendResult.is_mock || false)
        } catch (e) {
            console.error('TrendExplorer fetch error:', e)
            setData([])
            setPrevData([])
            setDeviceData(null)
            setLoadError(e.message || 'Nie udało się załadować danych trendu')
            showToast?.(`Trend Explorer: ${e.message || 'błąd ładowania'}`, 'error')
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, activeMetrics, filters.dateFrom, filters.dateTo, filters.campaignType, filters.status, campaignIdsKey, options.showPeriodOverPeriod, options.showDeviceSegmentation, showToast])

    useEffect(() => { fetchData() }, [fetchData])

    // ─── Action timeline ──────────────────────────────────────────────────────
    useEffect(() => {
        if (!selectedClientId) { setActionEvents([]); return }
        let cancelled = false
        const params = { limit: 200 }
        if (filters.dateFrom) params.date_from = filters.dateFrom
        if (filters.dateTo) params.date_to = filters.dateTo
        if (campaignName) params.campaign_name = campaignName
        getUnifiedTimeline(selectedClientId, params)
            .then(res => {
                if (cancelled) return
                const all = res?.entries || []
                const scoped = campaignName ? all.filter(e => e.campaign_name === campaignName) : all
                setActionEvents(scoped)
            })
            .catch(() => !cancelled && setActionEvents([]))
        return () => { cancelled = true }
    }, [selectedClientId, filters.dateFrom, filters.dateTo, campaignName])

    const eventsByDate = useMemo(() => {
        const map = {}
        ;(actionEvents || []).forEach(e => {
            const ts = e.timestamp || e.executed_at || e.change_date_time || ''
            const d = ts.slice(0, 10)
            if (d) {
                if (!map[d]) map[d] = []
                map[d].push(e)
            }
        })
        return map
    }, [actionEvents])
    const eventDates = Object.keys(eventsByDate)

    // ─── Enriched chart data: merge period-over-period + forecast ────────────
    const enrichedData = useMemo(() => {
        let result = data
        if (options.showPeriodOverPeriod && prevData.length > 0) {
            result = mergePeriodOverPeriod(result, prevData, activeMetrics)
        }
        if (options.showForecast && result.length >= 3) {
            const forecast = forecastPoints(result, activeMetrics, 7)
            // Ensure forecast rows also carry a 'continuation' value for the last real day
            // so the dashed line connects smoothly.
            result = [...result, ...forecast]
        }
        return result
    }, [data, prevData, options.showPeriodOverPeriod, options.showForecast, activeMetrics])

    // ─── Rolling correlation series (first 2 active metrics) ─────────────────
    const rollingCorrSeries = useMemo(() => {
        if (!options.showRollingCorrelation || activeMetrics.length < 2 || data.length < 14) return null
        return rollingCorrelation(data, activeMetrics[0], activeMetrics[1], 14)
    }, [options.showRollingCorrelation, activeMetrics, data])

    // ─── Device segmentation merged series ───────────────────────────────────
    // Precompute once per deviceData change. Without memo the IIFE in render rebuilt
    // the Map on every unrelated re-render (options toggle, metric pill add/remove).
    const deviceChartData = useMemo(() => {
        if (!deviceData) return []
        const dateMap = new Map()
        Object.entries(deviceData).forEach(([dev, series]) => {
            series.forEach(pt => {
                if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date })
                dateMap.get(pt.date)[dev] = pt.value
            })
        })
        return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date))
    }, [deviceData])

    // ─── Tooltip with clickable event actions ────────────────────────────────
    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload?.length) return null
        const events = eventsByDate[label] || []
        return (
            <div style={{
                background: C.surfaceElevated,
                border: B.hover,
                borderRadius: 8,
                padding: '10px 14px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                fontSize: 12,
                maxWidth: 360,
                pointerEvents: 'auto',
            }}>
                <div style={{ color: C.w50, marginBottom: 6 }}>{label}</div>
                {payload
                    .filter(p => !p.dataKey?.startsWith('__'))
                    .map((p, i) => (
                        <div key={i} style={{ color: p.color, marginBottom: 2 }}>
                            {p.name}: <strong>{p.value?.toLocaleString?.('pl-PL', { maximumFractionDigits: 2 }) ?? p.value}</strong>
                        </div>
                    ))}
                {events.length > 0 && (
                    <div style={{ borderTop: B.subtle, marginTop: 8, paddingTop: 8 }}>
                        <div style={{ fontSize: 10, color: C.accentBlue, fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            ● {events.length} {events.length === 1 ? 'zmiana' : 'zmian'} w tym dniu
                        </div>
                        {events.slice(0, 3).map((e, i) => {
                            const op = e.operation || e.action_type
                            const beforeAfter = formatBeforeAfter(e)
                            const ts = e.timestamp || e.executed_at
                            const isHelper = e.source !== 'external'
                            return (
                                <div key={i} style={{ padding: '5px 0', borderBottom: i < Math.min(events.length, 3) - 1 ? `1px solid ${C.w06}` : 'none' }}>
                                    <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                                        <span style={{
                                            fontSize: 8, fontWeight: 700, padding: '1px 5px', borderRadius: 999,
                                            background: isHelper ? 'rgba(79,142,247,0.2)' : 'rgba(251,191,36,0.2)',
                                            color: isHelper ? '#4F8EF7' : '#FBBF24',
                                        }}>{isHelper ? 'HELPER' : 'ZEWN.'}</span>
                                        <span style={{ fontSize: 11, color: C.textPrimary, fontWeight: 500 }}>{getOperationLabel(op)}</span>
                                        {ts && <span style={{ fontSize: 9, color: C.w30, marginLeft: 'auto' }}>{formatTimestamp(ts)}</span>}
                                    </div>
                                    {e.entity_name && <div style={{ fontSize: 10, color: C.w40, marginBottom: 2 }}>{e.entity_name}</div>}
                                    {beforeAfter && beforeAfter.map((line, j) => (
                                        <div key={j} style={{ fontSize: 10, color: '#A78BFA', fontFamily: 'monospace' }}>{line}</div>
                                    ))}
                                </div>
                            )
                        })}
                        {events.length > 3 && (
                            <div style={{ fontSize: 10, color: C.w30, fontStyle: 'italic', paddingTop: 4 }}>
                                +{events.length - 3} więcej…
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                            <button
                                onClick={(ev) => { ev.stopPropagation(); handleDeltaClick(label) }}
                                style={{
                                    fontSize: 10, padding: '4px 8px', borderRadius: 6,
                                    background: 'rgba(79,142,247,0.15)', border: '1px solid rgba(79,142,247,0.3)',
                                    color: '#4F8EF7', cursor: 'pointer',
                                }}
                            >
                                📊 Analiza delta
                            </button>
                            <button
                                onClick={(ev) => { ev.stopPropagation(); navigate('/action-history') }}
                                style={{
                                    fontSize: 10, padding: '4px 8px', borderRadius: 6,
                                    background: 'rgba(123,92,224,0.15)', border: '1px solid rgba(123,92,224,0.3)',
                                    color: '#A78BFA', cursor: 'pointer',
                                }}
                            >
                                → Historia
                            </button>
                        </div>
                    </div>
                )}
            </div>
        )
    }

    // ─── Close popups on outside click ───────────────────────────────────────
    useEffect(() => {
        if (!showCorrelationPopup && !showDropdown && !showOptions && !showPresetsMenu && !deltaPopup) return
        const handler = (e) => {
            if (!e.target.closest('[data-te-popup]')) {
                setShowCorrelationPopup(false)
                setShowDropdown(false)
                setShowOptions(false)
                setShowPresetsMenu(false)
                setDeltaPopup(null)
            }
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [showCorrelationPopup, showDropdown, showOptions, showPresetsMenu, deltaPopup])

    const addMetric = (key) => {
        if (activeMetrics.length >= MAX_METRICS || activeMetrics.includes(key)) return
        setActiveMetrics(prev => [...prev, key])
        setShowDropdown(false)
        setActivePresetName(null)
    }

    const removeMetric = (key) => {
        if (activeMetrics.length <= 1) return
        setActiveMetrics(prev => prev.filter(m => m !== key))
        setActivePresetName(null)
    }

    // ─── Correlation ──────────────────────────────────────────────────────────
    useEffect(() => {
        let cancelled = false
        const fetchCorrelation = async () => {
            if (activeMetrics.length < 2 || data.length < 3) {
                if (!cancelled) setCorrelationData(null)
                return
            }
            try {
                const response = await getCorrelationMatrix({
                    campaign_ids: campaignIds && campaignIds.length > 0 ? campaignIds : undefined,
                    metrics: activeMetrics,
                    date_from: filters.dateFrom || undefined,
                    date_to: filters.dateTo || undefined,
                })
                if (cancelled) return
                const pairs = []
                let bestIdx = -1
                for (let i = 0; i < activeMetrics.length; i++) {
                    for (let j = i + 1; j < activeMetrics.length; j++) {
                        const a = activeMetrics[i]
                        const b = activeMetrics[j]
                        const r = response?.matrix?.[a]?.[b]
                        if (typeof r === 'number') {
                            const labelA = METRIC_LABELS[a] ?? a
                            const labelB = METRIC_LABELS[b] ?? b
                            pairs.push({ a: labelA, b: labelB, r, label: getCorrelationLabel(r) })
                            if (bestIdx < 0 || Math.abs(r) > Math.abs(pairs[bestIdx].r)) bestIdx = pairs.length - 1
                        }
                    }
                }
                if (pairs.length > 0 && bestIdx >= 0) {
                    const best = pairs[bestIdx]
                    setCorrelationData({
                        best: { pairLabel: `${best.a} vs ${best.b}`, label: best.label, r: best.r },
                        pairs: pairs.sort((a, b) => Math.abs(b.r) - Math.abs(a.r)),
                    })
                } else {
                    setCorrelationData(null)
                }
            } catch (e) {
                if (!cancelled) setCorrelationData(null)
            }
        }
        fetchCorrelation()
        return () => { cancelled = true }
    }, [activeMetrics, campaignIdsKey, data, filters.dateFrom, filters.dateTo])

    // ─── Delta analysis (click from tooltip) ─────────────────────────────────
    const handleDeltaClick = useCallback((markerDate) => {
        const delta = computeDelta(data, markerDate, activeMetrics, 7)
        if (!delta) {
            showToast?.('Za mało danych dla analizy delta (potrzeba min. 1 dzień przed i po)', 'warning')
            return
        }
        setDeltaPopup({ date: markerDate, delta })
    }, [data, activeMetrics, showToast])

    // ─── Presets ──────────────────────────────────────────────────────────────
    const handleSavePreset = () => {
        const name = window.prompt('Nazwa presetu:')
        if (!name) return
        const trimmed = name.trim()
        if (BUILT_IN_PRESETS[trimmed]) {
            showToast?.(`Nazwa "${trimmed}" jest zarezerwowana dla presetu wbudowanego`, 'warning')
            return
        }
        savePreset(trimmed, { metrics: activeMetrics, options })
        setPresetsVersion(v => v + 1)
        showToast?.(`Preset "${trimmed}" zapisany`, 'success')
    }
    const handleLoadPreset = (name) => {
        const preset = builtInPresets[name] || userPresets[name]
        if (!preset) return
        setActiveMetrics(preset.metrics || ['cost', 'clicks'])
        // Reset all option toggles to the preset's desired state so loading a
        // preset gives a predictable view (not a merge with stale flags).
        setOptions({
            showDots: false,
            showForecast: false,
            showRollingCorrelation: false,
            showPeriodOverPeriod: false,
            showZoomBrush: false,
            showDeviceSegmentation: false,
            showActionMarkers: true,
            ...(preset.options || {}),
        })
        setShowPresetsMenu(false)
        setActivePresetName(name)
        showToast?.(`Preset "${name}" załadowany`, 'success')
    }
    const handleDeletePreset = (name) => {
        if (BUILT_IN_PRESETS[name]) return  // guarded at util level too
        if (!window.confirm(`Usunąć preset "${name}"?`)) return
        deletePreset(name)
        setPresetsVersion(v => v + 1)
    }

    // ─── Cross-link ───────────────────────────────────────────────────────────
    const crossLinkTarget = variant === 'dashboard' ? '/campaigns' : '/'
    const crossLinkLabel = variant === 'dashboard' ? 'Rozbij per kampania →' : '← Widok konta'

    const dual = needsDualAxis(activeMetrics)
    const availableToAdd = availableOptions.filter(m => !activeMetrics.includes(m.key))

    // ─── Delta grid: current vs previous totals per active metric ─────────────
    // Shown only in fullscreen mode. Needs `showPeriodOverPeriod` to have data;
    // otherwise we fall back to comparing first half vs second half of `data`.
    const deltaGrid = useMemo(() => {
        if (!data.length) return null
        const sumFor = (rows, key) => rows.reduce((s, r) => s + (Number(r[key]) || 0), 0)
        const avgFor = (rows, key) => rows.length ? sumFor(rows, key) / rows.length : 0
        const usePrev = options.showPeriodOverPeriod && prevData.length > 0
        return activeMetrics.map(key => {
            const curRows = data
            const prevRows = usePrev ? prevData : data.slice(0, Math.floor(data.length / 2))
            const curRowsForAvg = usePrev ? data : data.slice(Math.floor(data.length / 2))
            const isRate = PCT_KEYS.has(key) || ['cpc', 'cpa', 'cvr', 'roas'].includes(key)
            const cur = isRate ? avgFor(curRowsForAvg, key) : sumFor(curRows, key)
            const prev = isRate ? avgFor(prevRows, key) : sumFor(prevRows, key)
            const pct = prev ? ((cur - prev) / prev) * 100 : null
            return {
                key,
                label: METRIC_LABELS[key] || key,
                cur: +cur.toFixed(2),
                prev: +prev.toFixed(2),
                pct: pct === null ? null : +pct.toFixed(1),
                usePrev,
            }
        })
    }, [data, prevData, activeMetrics, options.showPeriodOverPeriod])

    const cardStyle = fullscreen
        ? { padding: '24px 32px', borderRadius: 0, minHeight: '100%', boxSizing: 'border-box' }
        : { padding: '20px 24px' }

    const cardBody = (
        <div className="v2-card" style={cardStyle} data-trend-explorer-card>
            {/* ─── Header ────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between mb-4" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div className="flex items-center gap-2">
                    <TrendingUp size={16} style={{ color: C.accentBlue }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                        Trend Explorer
                    </span>
                    <button
                        onClick={() => navigate(crossLinkTarget)}
                        title={crossLinkLabel}
                        style={{
                            fontSize: 10, padding: '2px 8px', borderRadius: 999,
                            background: C.w04, border: B.subtle, color: C.w50,
                            cursor: 'pointer', marginLeft: 6,
                        }}
                    >
                        {crossLinkLabel}
                    </button>
                    <button
                        onClick={() => { setFullscreen(v => !v); if (!fullscreen) setShowActionsDrawer(true) }}
                        title={fullscreen ? 'Zwiń widok' : 'Rozwiń na pełny ekran'}
                        style={{
                            fontSize: 10, padding: '3px 8px', borderRadius: 6,
                            background: C.w04, border: B.subtle, color: C.w60,
                            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                        }}
                    >
                        {fullscreen ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
                        {fullscreen ? 'Zwiń' : 'Rozwiń'}
                    </button>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {/* Metric pills */}
                    {activeMetrics.map((key, idx) => {
                        const opt = METRIC_OPTIONS.find(m => m.key === key)
                        return (
                            <div
                                key={key}
                                className="flex items-center gap-1.5"
                                style={{
                                    background: `${METRIC_COLORS[idx]}20`,
                                    border: `1px solid ${METRIC_COLORS[idx]}40`,
                                    borderRadius: 999,
                                    padding: '3px 10px 3px 12px',
                                    fontSize: 12,
                                    color: METRIC_COLORS[idx],
                                }}
                            >
                                <span title={opt?.tooltip || undefined}>{opt?.label ?? key}</span>
                                {activeMetrics.length > 1 && (
                                    <button onClick={() => removeMetric(key)} style={{ color: C.w40, lineHeight: 1 }} className="hover:text-white/70">
                                        <X size={12} />
                                    </button>
                                )}
                            </div>
                        )
                    })}

                    {/* Add metric */}
                    {activeMetrics.length < MAX_METRICS && availableToAdd.length > 0 && (
                        <div style={{ position: 'relative' }} data-te-popup>
                            <button
                                onClick={() => { setShowDropdown(v => !v); setShowOptions(false); setShowPresetsMenu(false) }}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    background: C.w04, border: B.medium, borderRadius: 999,
                                    padding: '3px 12px', fontSize: 12, color: C.w50, cursor: 'pointer',
                                }}
                                className="hover:border-white/20 hover:text-white/70"
                            >
                                <Plus size={12} />
                                Dodaj metrykę
                            </button>
                            {showDropdown && (
                                <div style={{
                                    position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                    background: C.surfaceElevated, border: B.hover, borderRadius: 8,
                                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 50,
                                    minWidth: 200, maxHeight: 340, overflowY: 'auto',
                                }}>
                                    {availableToAdd.map(opt => (
                                        <button
                                            key={opt.key}
                                            onClick={() => addMetric(opt.key)}
                                            style={{
                                                display: 'block', width: '100%', textAlign: 'left',
                                                padding: '8px 14px', fontSize: 12, color: C.w70,
                                                cursor: 'pointer', background: 'transparent', border: 'none',
                                            }}
                                            className="hover:bg-white/5 hover:text-white"
                                        >
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Correlation badge */}
                    {correlationData && (
                        <div style={{ position: 'relative' }} data-te-popup>
                            <button
                                onClick={() => setShowCorrelationPopup(v => !v)}
                                style={{
                                    fontSize: 11, color: C.w40, paddingLeft: 8,
                                    background: 'none', border: 'none',
                                    borderLeft: `1px solid ${C.w08}`,
                                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                                }}
                                className="hover:text-white/60"
                            >
                                <span style={{ color: C.w30 }}>Kor.</span>
                                <span style={{
                                    color: Math.abs(correlationData.best.r) > 0.7 ? C.success
                                         : Math.abs(correlationData.best.r) > 0.4 ? C.warning
                                         : C.textMuted,
                                }}>
                                    {correlationData.best.r > 0 ? '+' : ''}{correlationData.best.r.toFixed(2)}
                                </span>
                                {correlationData.pairs.length > 1 && (
                                    <span style={{ fontSize: 9, color: C.w25 }}>({correlationData.pairs.length} par)</span>
                                )}
                            </button>
                            {showCorrelationPopup && (
                                <div style={{
                                    position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                    background: C.surfaceElevated, border: B.hover, borderRadius: 8,
                                    boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50,
                                    minWidth: 280, padding: '12px 0',
                                }}>
                                    <div style={{ padding: '0 14px 8px', fontSize: 11, fontWeight: 600, color: C.w50, borderBottom: B.subtle, marginBottom: 4 }}>
                                        Macierz korelacji (Pearson)
                                    </div>
                                    {correlationData.pairs.map((pair, i) => {
                                        const absR = Math.abs(pair.r)
                                        const rColor = absR > 0.7 ? C.success : absR > 0.4 ? C.warning : C.textMuted
                                        return (
                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 14px', fontSize: 11 }}>
                                                <span style={{ color: C.w60, flex: 1 }}>
                                                    {pair.a} <span style={{ color: C.w20 }}>vs</span> {pair.b}
                                                </span>
                                                <span style={{ color: rColor, fontWeight: 600, marginLeft: 12, whiteSpace: 'nowrap' }}>
                                                    {pair.r > 0 ? '+' : ''}{pair.r.toFixed(2)}
                                                </span>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Options gear */}
                    <div style={{ position: 'relative' }} data-te-popup>
                        <button
                            onClick={() => { setShowOptions(v => !v); setShowDropdown(false); setShowPresetsMenu(false) }}
                            title="Opcje widoku"
                            style={{
                                display: 'flex', alignItems: 'center',
                                background: C.w04, border: B.medium, borderRadius: 6,
                                padding: '5px 8px', color: C.w50, cursor: 'pointer',
                            }}
                        >
                            <Settings size={12} />
                        </button>
                        {showOptions && (
                            <div style={{
                                position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                background: C.surfaceElevated, border: B.hover, borderRadius: 8,
                                boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50,
                                minWidth: 240, padding: '8px 0',
                            }}>
                                <div style={{ padding: '4px 14px 8px', fontSize: 10, fontWeight: 600, color: C.w40, textTransform: 'uppercase' }}>
                                    Opcje widoku
                                </div>
                                {[
                                    ['showActionMarkers', 'Znaczniki zmian na wykresie'],
                                    ['showDots', 'Kropki na linii'],
                                    ['showForecast', 'Prognoza 7 dni (linear)'],
                                    ['showRollingCorrelation', 'Korelacja krocząca (14d)'],
                                    ['showPeriodOverPeriod', 'Nakładka: poprzedni okres'],
                                    ['showZoomBrush', 'Zoom brush (oś czasu)'],
                                    ['showDeviceSegmentation', 'Segmentacja per urządzenie'],
                                ].map(([key, label]) => (
                                    <label key={key} style={{
                                        display: 'flex', alignItems: 'center', gap: 8,
                                        padding: '6px 14px', fontSize: 12, color: C.w70, cursor: 'pointer',
                                    }}>
                                        <input
                                            type="checkbox"
                                            checked={options[key]}
                                            onChange={() => toggleOption(key)}
                                            style={{ cursor: 'pointer' }}
                                        />
                                        {label}
                                    </label>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Presets */}
                    <div style={{ position: 'relative' }} data-te-popup>
                        <button
                            onClick={() => { setShowPresetsMenu(v => !v); setShowDropdown(false); setShowOptions(false) }}
                            title="Presety"
                            style={{
                                display: 'flex', alignItems: 'center',
                                background: C.w04, border: B.medium, borderRadius: 6,
                                padding: '5px 8px', color: C.w50, cursor: 'pointer',
                            }}
                        >
                            <Save size={12} />
                        </button>
                        {showPresetsMenu && (
                            <div style={{
                                position: 'absolute', top: '100%', right: 0, marginTop: 6,
                                background: C.surfaceElevated, border: B.hover, borderRadius: 8,
                                boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50,
                                minWidth: 260, padding: '8px 0',
                            }}>
                                <div style={{ padding: '4px 14px 6px', fontSize: 10, fontWeight: 600, color: C.w40, textTransform: 'uppercase' }}>
                                    Wbudowane presety
                                </div>
                                {Object.entries(builtInPresets).map(([name, preset]) => (
                                    <button
                                        key={name}
                                        onClick={() => handleLoadPreset(name)}
                                        style={{
                                            display: 'block', width: '100%', textAlign: 'left',
                                            padding: '6px 14px', fontSize: 12, color: C.w70,
                                            cursor: 'pointer', background: 'transparent', border: 'none',
                                        }}
                                        className="hover:bg-white/5 hover:text-white"
                                    >
                                        <div style={{ fontWeight: 500 }}>{name}</div>
                                        {preset.description && (
                                            <div style={{ fontSize: 10, color: C.w40, marginTop: 1 }}>
                                                {preset.description}
                                            </div>
                                        )}
                                    </button>
                                ))}
                                <div style={{ borderTop: B.subtle, marginTop: 6 }} />
                                <div style={{ padding: '6px 14px 4px', fontSize: 10, fontWeight: 600, color: C.w40, textTransform: 'uppercase' }}>
                                    Moje presety
                                </div>
                                <button
                                    onClick={handleSavePreset}
                                    style={{
                                        display: 'block', width: '100%', textAlign: 'left',
                                        padding: '6px 14px', fontSize: 12, color: C.accentBlue,
                                        cursor: 'pointer', background: 'transparent', border: 'none',
                                    }}
                                    className="hover:bg-white/5"
                                >
                                    + Zapisz bieżący układ
                                </button>
                                {Object.keys(userPresets).length === 0 ? (
                                    <div style={{ padding: '6px 14px', fontSize: 11, color: C.w30, fontStyle: 'italic' }}>
                                        Brak zapisanych presetów
                                    </div>
                                ) : (
                                    <>
                                        {Object.keys(userPresets).map(name => (
                                            <div key={name} style={{
                                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                padding: '4px 14px',
                                            }}>
                                                <button
                                                    onClick={() => handleLoadPreset(name)}
                                                    style={{
                                                        flex: 1, textAlign: 'left', fontSize: 12, color: C.w70,
                                                        background: 'transparent', border: 'none', cursor: 'pointer',
                                                        padding: '4px 0',
                                                    }}
                                                    className="hover:text-white"
                                                >
                                                    {name}
                                                </button>
                                                <button
                                                    onClick={() => handleDeletePreset(name)}
                                                    style={{ color: C.w30, background: 'transparent', border: 'none', cursor: 'pointer' }}
                                                    className="hover:text-red-400"
                                                >
                                                    <X size={12} />
                                                </button>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        )}
                    </div>

                </div>
            </div>

            {/* ─── Mock banner ──────────────────────────────────────────── */}
            {isMock && !loading && (
                <div style={{
                    background: 'rgba(251, 191, 36, 0.1)',
                    border: '1px solid #FBBF24',
                    borderRadius: 6, padding: '10px 14px', marginBottom: 12,
                    fontSize: 12, color: C.warning,
                    display: 'flex', alignItems: 'center', gap: 10,
                }}>
                    <span>⚠️</span>
                    <span>Brak rzeczywistych danych — synchronizuj konto aby zebrać dane metryk</span>
                </div>
            )}

            {/* ─── Chart ──────────────────────────────────────────────── */}
            <div>
                {loading ? (
                    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.w30, fontSize: 12 }}>
                        Ładowanie danych…
                    </div>
                ) : loadError ? (
                    <div style={{ height: 260, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: C.w40, fontSize: 12, gap: 6 }}>
                        <span style={{ color: C.danger }}>⚠ Nie udało się załadować trendu</span>
                        <span style={{ fontSize: 11, color: C.w30 }}>{loadError}</span>
                    </div>
                ) : enrichedData.length < 2 ? (
                    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.w30, fontSize: 12 }}>
                        {enrichedData.length === 0
                            ? 'Brak danych dla wybranych filtrów'
                            : 'Wybierz zakres co najmniej 2 dni, aby zobaczyć trend'}
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height={fullscreen ? (options.showZoomBrush ? 540 : 500) : (options.showZoomBrush ? 300 : 260)}>
                        <ComposedChart data={enrichedData} margin={{ top: 4, right: dual ? 40 : 8, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis
                                dataKey="date"
                                tickFormatter={formatDate}
                                tick={{ fontSize: 10, fill: C.w30 }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <YAxis yAxisId="left" tick={{ fontSize: 10, fill: C.w30 }} axisLine={false} tickLine={false} width={45} />
                            {dual && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: C.w30 }} axisLine={false} tickLine={false} width={40} />}
                            <Tooltip content={<CustomTooltip />} />
                            {options.showActionMarkers && eventDates.map(d => {
                                const isHelper = eventsByDate[d].some(e => e.source !== 'external')
                                const color = isHelper ? '#4F8EF7' : '#FBBF24'
                                const count = eventsByDate[d].length
                                // Clickable marker: a <text> label with onClick opens Action History
                                // filtered to this date. A larger transparent circle behind it widens
                                // the hit area so the 12px dot isn't frustrating to click.
                                const clickableLabel = (labelProps) => {
                                    const { viewBox } = labelProps
                                    if (!viewBox) return null
                                    const cx = viewBox.x
                                    const cy = (viewBox.y ?? 0) + 8
                                    return (
                                        <g
                                            style={{ cursor: 'pointer' }}
                                            onClick={(ev) => { ev.stopPropagation(); navigate(`/action-history?date=${d}`) }}
                                        >
                                            <title>
                                                {`${count} ${count === 1 ? 'zmiana' : 'zmian'} ${d} — kliknij aby otworzyć Action History`}
                                            </title>
                                            <circle cx={cx} cy={cy} r={10} fill="transparent" />
                                            <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fill={color} fontSize={14} fontWeight={700}>
                                                ●
                                            </text>
                                            {count > 1 && (
                                                <text x={cx + 7} y={cy - 4} textAnchor="start" fill={color} fontSize={8} fontWeight={700}>
                                                    {count}
                                                </text>
                                            )}
                                        </g>
                                    )
                                }
                                return (
                                    <ReferenceLine
                                        key={d} x={d} yAxisId="left"
                                        stroke={color}
                                        strokeDasharray="4 3" strokeWidth={1.5}
                                        label={clickableLabel}
                                    />
                                )
                            })}
                            {/* Main metric lines */}
                            {activeMetrics.map((key, idx) => {
                                const opt = METRIC_OPTIONS.find(m => m.key === key)
                                const yAxis = dual && PCT_KEYS.has(key) ? 'right' : 'left'
                                return (
                                    <Line
                                        key={key}
                                        yAxisId={yAxis}
                                        type="monotone"
                                        dataKey={key}
                                        name={opt?.label ?? key}
                                        stroke={METRIC_COLORS[idx]}
                                        strokeWidth={1.8}
                                        dot={options.showDots ? { r: 2, fill: METRIC_COLORS[idx] } : false}
                                        activeDot={{ r: 4, fill: METRIC_COLORS[idx] }}
                                        connectNulls
                                    />
                                )
                            })}
                            {/* Period-over-period overlay (dashed) */}
                            {options.showPeriodOverPeriod && activeMetrics.map((key, idx) => {
                                const yAxis = dual && PCT_KEYS.has(key) ? 'right' : 'left'
                                return (
                                    <Line
                                        key={`prev_${key}`}
                                        yAxisId={yAxis}
                                        type="monotone"
                                        dataKey={`__prev_${key}`}
                                        name={`${METRIC_LABELS[key] || key} (poprz.)`}
                                        stroke={METRIC_COLORS[idx]}
                                        strokeWidth={1.2}
                                        strokeDasharray="5 4"
                                        strokeOpacity={0.55}
                                        dot={false}
                                        connectNulls
                                    />
                                )
                            })}
                            {/* Forecast ghost lines */}
                            {options.showForecast && activeMetrics.map((key, idx) => {
                                const yAxis = dual && PCT_KEYS.has(key) ? 'right' : 'left'
                                return (
                                    <Line
                                        key={`fc_${key}`}
                                        yAxisId={yAxis}
                                        type="monotone"
                                        dataKey={`${key}__forecast`}
                                        name={`${METRIC_LABELS[key] || key} (prog.)`}
                                        stroke={METRIC_COLORS[idx]}
                                        strokeWidth={1.4}
                                        strokeDasharray="2 3"
                                        strokeOpacity={0.75}
                                        dot={false}
                                        connectNulls
                                    />
                                )
                            })}
                            {options.showZoomBrush && (
                                <Brush
                                    dataKey="date"
                                    height={24}
                                    stroke="#4F8EF7"
                                    fill="rgba(79,142,247,0.08)"
                                    tickFormatter={formatDate}
                                    travellerWidth={8}
                                />
                            )}
                        </ComposedChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* ─── Rolling correlation mini-chart ───────────────────────── */}
            {options.showRollingCorrelation && rollingCorrSeries && (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: B.subtle }}>
                    <div style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', marginBottom: 6, letterSpacing: '0.05em' }}>
                        Korelacja krocząca (14d): {METRIC_LABELS[activeMetrics[0]]} vs {METRIC_LABELS[activeMetrics[1]]}
                    </div>
                    <ResponsiveContainer width="100%" height={60}>
                        <ComposedChart data={rollingCorrSeries} margin={{ top: 2, right: 8, left: 0, bottom: 0 }}>
                            <XAxis dataKey="date" hide />
                            <YAxis domain={[-1, 1]} tick={{ fontSize: 9, fill: C.w30 }} width={30} axisLine={false} tickLine={false} ticks={[-1, 0, 1]} />
                            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
                            <ReferenceLine y={0.7} stroke="rgba(74,222,128,0.25)" strokeDasharray="2 2" />
                            <ReferenceLine y={-0.7} stroke="rgba(248,113,113,0.25)" strokeDasharray="2 2" />
                            <Line type="monotone" dataKey="r" stroke="#A78BFA" strokeWidth={1.5} dot={false} connectNulls />
                            <Tooltip
                                contentStyle={{ background: C.surfaceElevated, border: B.hover, borderRadius: 6, fontSize: 11 }}
                                formatter={(v) => [v?.toFixed?.(2) ?? '—', 'r']}
                                labelFormatter={formatDate}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* ─── Device segmentation mini-chart ───────────────────────── */}
            {options.showDeviceSegmentation && deviceData && Object.keys(deviceData).length > 0 && (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: B.subtle }}>
                    <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                        <Layers size={11} style={{ color: C.w50 }} />
                        <span style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Segmentacja per urządzenie: {METRIC_LABELS[activeMetrics[0]]}
                        </span>
                    </div>
                    <ResponsiveContainer width="100%" height={120}>
                        <ComposedChart
                            data={deviceChartData}
                            margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 9, fill: C.w30 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: C.w30 }} width={40} axisLine={false} tickLine={false} />
                            <Tooltip
                                contentStyle={{ background: C.surfaceElevated, border: B.hover, borderRadius: 6, fontSize: 11 }}
                                labelFormatter={formatDate}
                            />
                            {Object.keys(deviceData).map(dev => (
                                <Line
                                    key={dev}
                                    type="monotone"
                                    dataKey={dev}
                                    name={dev}
                                    stroke={DEVICE_COLORS[dev] || '#9CA3AF'}
                                    strokeWidth={1.5}
                                    dot={false}
                                    connectNulls
                                />
                            ))}
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* ─── Preset guidance panel ────────────────────────────────── */}
            {activePresetName && (builtInPresets[activePresetName] || userPresets[activePresetName])?.guide && (
                <div style={{
                    marginTop: 12,
                    padding: '12px 14px',
                    background: 'rgba(79,142,247,0.06)',
                    border: '1px solid rgba(79,142,247,0.18)',
                    borderRadius: 8,
                    position: 'relative',
                }}>
                    <button
                        onClick={() => setActivePresetName(null)}
                        title="Ukryj wskazówki"
                        style={{
                            position: 'absolute', top: 8, right: 8,
                            color: C.w40, background: 'transparent', border: 'none', cursor: 'pointer',
                        }}
                        className="hover:text-white/70"
                    >
                        <X size={12} />
                    </button>
                    <div style={{
                        fontSize: 10, color: C.accentBlue, fontWeight: 700, textTransform: 'uppercase',
                        letterSpacing: '0.08em', marginBottom: 6,
                    }}>
                        Preset: {activePresetName} · Na co patrzeć
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: C.w70, lineHeight: 1.6 }}>
                        {(builtInPresets[activePresetName] || userPresets[activePresetName]).guide.map((line, i) => (
                            <li key={i}>{line}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* ─── Legend + Actions drawer toggle ───────────────────────── */}
            {eventDates.length > 0 && !loading && enrichedData.length > 0 && (
                <div className="flex items-center gap-4 mt-2" style={{ fontSize: 10, color: C.w30, flexWrap: 'wrap' }}>
                    <span className="flex items-center gap-1">
                        <span style={{ width: 14, height: 0, borderTop: '1.5px dashed #4F8EF7', display: 'inline-block' }} />
                        <span style={{ color: '#4F8EF7' }}>●</span>
                        <span>Akcja Helper</span>
                    </span>
                    <span className="flex items-center gap-1">
                        <span style={{ width: 14, height: 0, borderTop: '1.5px dashed #FBBF24', display: 'inline-block' }} />
                        <span style={{ color: '#FBBF24' }}>●</span>
                        <span>Zmiana zewnętrzna</span>
                    </span>
                    <button
                        onClick={() => setOptions(o => ({ ...o, showActionMarkers: !o.showActionMarkers }))}
                        title={options.showActionMarkers ? 'Ukryj znaczniki zmian na wykresie' : 'Pokaż znaczniki zmian na wykresie'}
                        style={{
                            marginLeft: 'auto',
                            fontSize: 10, padding: '3px 10px', borderRadius: 999,
                            background: options.showActionMarkers ? 'rgba(79,142,247,0.08)' : C.w04,
                            border: options.showActionMarkers ? '1px solid rgba(79,142,247,0.25)' : B.subtle,
                            color: options.showActionMarkers ? C.accentBlue : C.w50,
                            cursor: 'pointer',
                        }}
                    >
                        {options.showActionMarkers ? 'Ukryj zmiany' : 'Pokaż zmiany'}
                    </button>
                    <button
                        onClick={() => setShowActionsDrawer(v => !v)}
                        style={{
                            fontSize: 11, padding: '3px 10px', borderRadius: 999,
                            background: showActionsDrawer ? 'rgba(79,142,247,0.15)' : C.w04,
                            border: showActionsDrawer ? '1px solid rgba(79,142,247,0.4)' : B.subtle,
                            color: showActionsDrawer ? C.accentBlue : C.w50,
                            cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 6,
                        }}
                    >
                        {actionEvents.length} {actionEvents.length === 1 ? 'akcja' : 'akcji'} w okresie
                        {showActionsDrawer ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                    </button>
                </div>
            )}

            {/* ─── Actions drawer (full event list below chart) ────────── */}
            {showActionsDrawer && actionEvents.length > 0 && (
                <ActionsDrawer
                    events={actionEvents}
                    eventsByDate={eventsByDate}
                    actionsFilter={actionsFilter}
                    setActionsFilter={setActionsFilter}
                    onRowClick={(dateStr) => navigate(`/action-history?date=${dateStr}`)}
                />
            )}

            {/* ─── Delta grid (fullscreen only) ──────────────────────────── */}
            {fullscreen && deltaGrid && deltaGrid.length > 0 && enrichedData.length > 0 && (
                <div style={{ marginTop: 16, paddingTop: 12, borderTop: B.subtle }}>
                    <div style={{
                        fontSize: 10, color: C.w40, textTransform: 'uppercase',
                        letterSpacing: '0.05em', marginBottom: 8, fontWeight: 600,
                    }}>
                        Zmiana vs {deltaGrid[0]?.usePrev ? 'poprzedni okres' : 'pierwsza połowa zakresu'}
                    </div>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                        gap: 8,
                    }}>
                        {deltaGrid.map(row => {
                            const pct = row.pct
                            const color = pct === null ? C.w40
                                        : pct > 5 ? C.success
                                        : pct < -5 ? C.danger
                                        : C.warning
                            return (
                                <div key={row.key} style={{
                                    padding: '10px 12px', borderRadius: 8,
                                    background: C.w04, border: B.subtle,
                                }}>
                                    <div style={{ fontSize: 10, color: C.w50, marginBottom: 4 }}>{row.label}</div>
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                                        <span style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne' }}>
                                            {row.cur.toLocaleString('pl-PL', { maximumFractionDigits: 2 })}
                                        </span>
                                        {pct !== null && (
                                            <span style={{ fontSize: 11, color, fontWeight: 600 }}>
                                                {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
                                            </span>
                                        )}
                                    </div>
                                    <div style={{ fontSize: 10, color: C.w30, marginTop: 2 }}>
                                        vs {row.prev.toLocaleString('pl-PL', { maximumFractionDigits: 2 })}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* ─── Delta analysis popup ───────────────────────────────── */}
            {deltaPopup && (
                <div
                    data-te-popup
                    style={{
                        position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                        background: C.surfaceElevated, border: B.hover, borderRadius: 10,
                        boxShadow: '0 16px 64px rgba(0,0,0,0.6)', zIndex: 200,
                        minWidth: 360, maxWidth: 480, padding: '18px 22px',
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <div>
                            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                                Analiza delta: {deltaPopup.date}
                            </div>
                            <div style={{ fontSize: 10, color: C.w40, marginTop: 2 }}>
                                Średnia 7 dni przed vs 7 dni po akcji
                            </div>
                        </div>
                        <button
                            onClick={() => setDeltaPopup(null)}
                            style={{ color: C.w40, background: 'transparent', border: 'none', cursor: 'pointer' }}
                        >
                            <X size={16} />
                        </button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {activeMetrics.map(key => {
                            const d = deltaPopup.delta[key]
                            if (!d) return null
                            const pct = d.pctChange
                            const color = pct === null ? C.w40
                                        : pct > 5 ? C.success
                                        : pct < -5 ? C.danger
                                        : C.warning
                            return (
                                <div key={key} style={{
                                    display: 'grid', gridTemplateColumns: '1fr auto auto auto',
                                    alignItems: 'center', gap: 10, padding: '8px 10px',
                                    background: C.w04, borderRadius: 6, fontSize: 12,
                                }}>
                                    <span style={{ color: C.textPrimary, fontWeight: 500 }}>{METRIC_LABELS[key]}</span>
                                    <span style={{ color: C.w50 }}>{d.before.toLocaleString('pl-PL', { maximumFractionDigits: 2 })}</span>
                                    <span style={{ color: C.w30 }}>→</span>
                                    <span style={{ color, fontWeight: 600 }}>
                                        {d.after.toLocaleString('pl-PL', { maximumFractionDigits: 2 })}
                                        {pct !== null && (
                                            <span style={{ fontSize: 10, marginLeft: 6 }}>
                                                ({pct > 0 ? '+' : ''}{pct.toFixed(1)}%)
                                            </span>
                                        )}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}
        </div>
    )

    // Rendering the fullscreen layer via a portal on document.body sidesteps any
    // ancestor `transform`, `filter`, `contain`, or `overflow:hidden` that would
    // otherwise clip `position:fixed`. Without this, the v2-card's stacking
    // context wins and "fullscreen" ends up sized by its original slot.
    if (fullscreen) {
        return createPortal(
            <div
                data-trend-explorer-fullscreen
                style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 9999,
                    background: '#0D0F14',
                    overflowY: 'auto',
                }}
            >
                {cardBody}
            </div>,
            document.body,
        )
    }

    return cardBody
}

// Parent pages (Dashboard, Campaigns) pass arrays/strings that are stable across
// unrelated re-renders. React.memo skips the chart re-render when the parent
// re-renders for reasons unrelated to Trend Explorer inputs.
export default memo(TrendExplorer)
