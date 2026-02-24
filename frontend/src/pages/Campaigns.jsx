import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { MetricsAreaChart } from '../components/Charts'
import { LoadingSpinner, ErrorMessage } from '../components/UI'
import { getCampaigns, getCampaignKPIs, getCampaignMetrics } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import FilterBar from '../components/FilterBar'
import EmptyState from '../components/EmptyState'
import { MousePointerClick, DollarSign, Target, TrendingUp, TrendingDown, KeyRound, Search } from 'lucide-react'

const STATUS_CONFIG = {
    ENABLED: { dot: '#4ADE80', color: '#4ADE80', label: 'Aktywna'    },
    PAUSED:  { dot: '#FBBF24', color: '#FBBF24', label: 'Wstrzymana' },
    REMOVED: { dot: '#F87171', color: '#F87171', label: 'Usunięta'   },
}

const TYPE_LABELS = {
    SEARCH: 'Search', PERFORMANCE_MAX: 'PMax',
    DISPLAY: 'Display', SHOPPING: 'Shopping', VIDEO: 'Video',
}

function KpiRow({ kpis }) {
    if (!kpis) return null
    const { current, change_pct } = kpis
    const items = [
        { label: 'Kliknięcia', value: current?.clicks, change: change_pct?.clicks, icon: MousePointerClick, color: '#4F8EF7' },
        { label: 'Koszt', value: current?.cost, change: change_pct?.cost, suffix: ' zł', icon: DollarSign, color: '#7B5CE0' },
        { label: 'Konwersje', value: current?.conversions, change: change_pct?.conversions, icon: Target, color: '#4ADE80' },
        { label: 'CTR', value: current?.ctr, change: change_pct?.ctr, suffix: '%', icon: TrendingUp, color: '#FBBF24', tooltip: 'Click-Through Rate — stosunek kliknięć do wyświetleń' },
    ]
    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
            {items.map(({ label, value, change, suffix = '', icon: Icon, color, tooltip }) => {
                const isUp = change > 0, isDown = change < 0
                return (
                    <div key={label} className="v2-card" style={{ padding: '12px 14px' }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }} title={tooltip || undefined}>{label}</span>
                            <div style={{ width: 24, height: 24, borderRadius: 6, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Icon size={12} style={{ color }} />
                            </div>
                        </div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1 }}>
                            {typeof value === 'number' ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}{suffix}
                        </div>
                        {change !== undefined && (
                            <div style={{ marginTop: 4, fontSize: 11, color: isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: 2 }}>
                                {isUp ? <TrendingUp size={10} /> : isDown ? <TrendingDown size={10} /> : null}
                                {Math.abs(change).toFixed(1)}%
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

export default function Campaigns() {
    const navigate = useNavigate()
    const { selectedClientId } = useApp()
    const { filters } = useFilter()
    const [campaigns, setCampaigns] = useState([])
    const [selected, setSelected] = useState(null)
    const [kpis, setKpis] = useState(null)
    const [metrics, setMetrics] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (selectedClientId) loadCampaigns()
    }, [selectedClientId])

    async function loadCampaigns() {
        setLoading(true)
        try {
            const data = await getCampaigns(selectedClientId)
            const items = data.items || []
            setCampaigns(items)
            if (items.length > 0) selectCampaign(items[0])
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    async function selectCampaign(campaign) {
        setSelected(campaign)
        setKpis(null)
        setMetrics([])
        try {
            const [kpiData, metricData] = await Promise.all([
                getCampaignKPIs(campaign.id, filters.period),
                getCampaignMetrics(campaign.id),
            ])
            setKpis(kpiData)
            setMetrics(metricData.map(m => ({
                date: m.date.slice(5),
                cost: m.cost,
                clicks: m.clicks,
                conversions: m.conversions,
            })))
        } catch (err) {
            console.error('Failed to load campaign details:', err)
        }
    }

    // Filter campaign list in-memory
    const filteredCampaigns = useMemo(() => campaigns.filter(c => {
        if (filters.campaignType !== 'ALL' && c.campaign_type !== filters.campaignType) return false
        if (filters.status !== 'ALL' && c.status !== filters.status) return false
        return true
    }), [campaigns, filters.campaignType, filters.status])

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
                <FilterBar hidePeriod />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
                {/* Campaign list */}
                <div className="v2-card" style={{ padding: 6, maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
                    {filteredCampaigns.length === 0 ? (
                        <div style={{ padding: '24px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
                            Brak kampanii
                        </div>
                    ) : filteredCampaigns.map(c => {
                        const active = selected?.id === c.id
                        const sCfg = STATUS_CONFIG[c.status] || { dot: '#666', color: '#666', label: c.status }
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
                                    <span>•</span>
                                    <span>{c.budget_usd?.toFixed(0)} zł/d</span>
                                </div>
                            </button>
                        )
                    })}
                </div>

                {/* Campaign detail */}
                <div>
                    {selected ? (
                        <>
                            <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0' }}>{selected.name}</span>
                                {(() => {
                                    const sCfg = STATUS_CONFIG[selected.status] || { color: '#666', label: selected.status }
                                    return (
                                        <span style={{ fontSize: 11, color: sCfg.color }}>
                                            ● {sCfg.label}
                                        </span>
                                    )
                                })()}
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
                            <KpiRow kpis={kpis} />
                            {/* IS summary for SEARCH campaigns */}
                            {selected.campaign_type === 'SEARCH' && selected.search_impression_share != null && (
                                <div className="v2-card" style={{ padding: '12px 16px', marginBottom: 12 }}>
                                    <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                                        Impression Share
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                                        {[
                                            { label: 'IS', value: selected.search_impression_share, color: '#4F8EF7' },
                                            { label: 'Top IS', value: selected.search_top_impression_share, color: '#7B5CE0' },
                                            { label: 'Budget Lost', value: selected.search_budget_lost_is, color: '#F87171' },
                                            { label: 'Rank Lost', value: selected.search_rank_lost_is, color: '#FBBF24' },
                                        ].map(({ label, value, color }) => (
                                            <div key={label} style={{ textAlign: 'center' }}>
                                                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'Syne', color }}>{value != null ? `${(value * 100).toFixed(1)}%` : '—'}</div>
                                                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>{label}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {metrics.length > 0 && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                    <MetricsAreaChart data={metrics} dataKey="cost" title="Koszt dzienny" color="#4F8EF7" />
                                    <MetricsAreaChart data={metrics} dataKey="clicks" title="Kliknięcia" color="#7B5CE0" />
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
