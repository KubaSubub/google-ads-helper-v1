import { useState, useMemo } from 'react'
import {
    ComposedChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
    ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { TrendingUp, Plus, X } from 'lucide-react'

// ─── Constants (local copies — kept in sync with CampaignsPage) ──────────────
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

const PCT_KEYS = [
    'ctr', 'conversion_rate', 'search_impression_share', 'search_top_impression_share',
    'search_abs_top_impression_share', 'search_budget_lost_is', 'search_rank_lost_is',
    'search_click_share', 'abs_top_impression_pct', 'top_impression_pct',
]

// ─── Helpers ──────────────────────────────────────────────────────────────────
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
    const hasPct = metrics.some(m => PCT_KEYS.includes(m))
    const hasNonPct = metrics.some(m => !PCT_KEYS.includes(m))
    return hasPct && hasNonPct
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

// ─── CampaignTrendExplorer ────────────────────────────────────────────────────
// Props:
//   metrics       — array of MetricDaily objects from getCampaignMetrics
//   actionEvents  — array of action/change log entries (unified timeline)
//   campaignType  — string e.g. 'SEARCH'
export default function CampaignTrendExplorer({ metrics, actionEvents, campaignType }) {
    const [activeMetrics, setActiveMetrics] = useState(['cost', 'clicks'])
    const [showDropdown, setShowDropdown] = useState(false)

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
