import { useState, useEffect, useMemo } from 'react'
import { Loader2, Search, TrendingUp, TrendingDown } from 'lucide-react'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import { getShoppingProductGroups } from '../../api'
import { PageHeader } from '../../components/UI'
import EmptyState from '../../components/EmptyState'
import { TH, TD, TD_DIM } from '../../constants/designTokens'

const fmt = (n, d = 2) => (typeof n === 'number' ? n.toFixed(d) : '—')
const fmtInt = (n) => (typeof n === 'number' ? n.toLocaleString('pl-PL') : '—')
const fmtCost = (micros) => (typeof micros === 'number' ? (micros / 1e6).toFixed(2) : '—')
const fmtCpa = (cost, conv) => (conv > 0 ? (cost / conv).toFixed(2) : '—')

const TABS = [
    { id: 'product_groups', label: 'Grupy produktów' },
    { id: 'performance', label: 'Performance' },
    { id: 'feed_health', label: 'Feed Health' },
]

function roasColor(roas) {
    if (roas == null || roas === '—') return 'rgba(255,255,255,0.8)'
    const v = typeof roas === 'string' ? parseFloat(roas) : roas
    if (isNaN(v)) return 'rgba(255,255,255,0.8)'
    if (v >= 4) return '#4ADE80'
    if (v >= 2) return '#FBBF24'
    return '#F87171'
}

function RoasBadge({ value }) {
    if (value == null || value === '—') return <span style={{ color: 'rgba(255,255,255,0.4)' }}>—</span>
    const color = roasColor(value)
    return (
        <span style={{
            fontSize: 11, padding: '2px 10px', borderRadius: 999,
            background: `${color}1A`, color,
            fontFamily: 'DM Sans, sans-serif', fontWeight: 600,
        }}>
            {typeof value === 'number' ? value.toFixed(2) : value}
        </span>
    )
}

function computeRoas(row) {
    const cost = (row.cost_micros || 0) / 1e6
    const convValue = (row.conversion_value_micros || 0) / 1e6
    if (cost <= 0) return null
    return convValue / cost
}

export default function ShoppingPage() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days } = useFilter()

    const [productGroups, setProductGroups] = useState([])
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('product_groups')
    const [searchQuery, setSearchQuery] = useState('')

    useEffect(() => {
        if (!selectedClientId) return
        setLoading(true)
        getShoppingProductGroups(selectedClientId, allParams)
            .then((data) => setProductGroups(Array.isArray(data) ? data : []))
            .catch(() => showToast('Błąd ładowania grup produktów', 'error'))
            .finally(() => setLoading(false))
    }, [selectedClientId, allParams])

    // Filtered product groups by search query
    const filteredGroups = useMemo(() => {
        if (!searchQuery.trim()) return productGroups
        const q = searchQuery.toLowerCase()
        return productGroups.filter((r) => {
            const name = (r.name || r.resource_name || '').toLowerCase()
            return name.includes(q)
        })
    }, [productGroups, searchQuery])

    if (!selectedClientId) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <PageHeader title="Produkty (Shopping)" subtitle="Wybierz klienta aby zobaczyć dane" />
                <EmptyState message="Brak wybranego klienta" />
            </div>
        )
    }

    // Aggregate KPIs from all product groups (not filtered)
    const totalClicks = productGroups.reduce((s, r) => s + (r.clicks || 0), 0)
    const totalImpressions = productGroups.reduce((s, r) => s + (r.impressions || 0), 0)
    const totalCostMicros = productGroups.reduce((s, r) => s + (r.cost_micros || 0), 0)
    const totalCost = totalCostMicros / 1e6
    const totalConversions = productGroups.reduce((s, r) => s + (r.conversions || 0), 0)
    const totalConvValueMicros = productGroups.reduce((s, r) => s + (r.conversion_value_micros || 0), 0)
    const totalConvValue = totalConvValueMicros / 1e6
    const avgCpa = totalConversions > 0 ? totalCost / totalConversions : null
    const totalRoas = totalCost > 0 ? totalConvValue / totalCost : null

    const kpiCards = [
        { label: 'Kliknięcia', value: fmtInt(totalClicks), color: '#4F8EF7' },
        { label: 'Koszt (PLN)', value: `${totalCost.toFixed(2)} zł`, color: '#7B5CE0' },
        { label: 'Konwersje', value: fmt(totalConversions), color: '#4ADE80' },
        { label: 'Śr. CPA', value: avgCpa !== null ? `${avgCpa.toFixed(2)} zł` : '—', color: '#FBBF24' },
        { label: 'ROAS', value: totalRoas !== null ? totalRoas.toFixed(2) : '—', color: roasColor(totalRoas) },
    ]

    // Performance tab data: top 5 and bottom 5 by ROAS (only groups with cost > 0)
    const groupsWithRoas = useMemo(() => {
        return productGroups
            .map((r) => ({ ...r, _roas: computeRoas(r) }))
            .filter((r) => r._roas !== null)
            .sort((a, b) => b._roas - a._roas)
    }, [productGroups])

    const topPerformers = groupsWithRoas.slice(0, 5)
    const bottomPerformers = [...groupsWithRoas].sort((a, b) => a._roas - b._roas).slice(0, 5)

    return (
        <div style={{ maxWidth: 1400 }}>
            <PageHeader title="Produkty (Shopping)" subtitle={`Analiza ${days} dni`} />

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 24 }}>
                {kpiCards.map((k) => (
                    <div key={k.label} className="v2-card" style={{ padding: '20px 24px' }}>
                        <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>
                            {k.label}
                        </div>
                        <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Syne, sans-serif', color: k.color }}>
                            {k.value}
                        </div>
                    </div>
                ))}
            </div>

            {/* Tab Switcher */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
                {TABS.map((tab) => {
                    const active = activeTab === tab.id
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                padding: '6px 18px',
                                borderRadius: 999,
                                border: active ? '1px solid #4F8EF7' : '1px solid rgba(255,255,255,0.1)',
                                background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                                color: active ? '#4F8EF7' : 'rgba(255,255,255,0.55)',
                                fontSize: 13,
                                fontWeight: active ? 600 : 400,
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                            }}
                        >
                            {tab.label}
                        </button>
                    )
                })}
            </div>

            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
                    <Loader2 size={32} className="animate-spin" style={{ color: '#4F8EF7' }} />
                </div>
            ) : (
                <>
                    {/* ── Product Groups Tab ── */}
                    {activeTab === 'product_groups' && (
                        <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                                    Grupy produktów
                                    {filteredGroups.length !== productGroups.length && (
                                        <span style={{ fontSize: 11, fontWeight: 400, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>
                                            ({filteredGroups.length} z {productGroups.length})
                                        </span>
                                    )}
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    {/* Search input */}
                                    <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                        <Search size={14} style={{ position: 'absolute', left: 10, color: 'rgba(255,255,255,0.3)', pointerEvents: 'none' }} />
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            placeholder="Szukaj grupy..."
                                            style={{
                                                padding: '6px 10px 6px 30px',
                                                fontSize: 12,
                                                fontFamily: 'DM Sans, sans-serif',
                                                background: 'rgba(255,255,255,0.05)',
                                                border: '1px solid rgba(255,255,255,0.1)',
                                                borderRadius: 8,
                                                color: 'rgba(255,255,255,0.8)',
                                                outline: 'none',
                                                width: 200,
                                                transition: 'border-color 0.15s',
                                            }}
                                            onFocus={(e) => (e.target.style.borderColor = 'rgba(79,142,247,0.5)')}
                                            onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
                                        />
                                    </div>
                                    {loading && <Loader2 size={16} style={{ color: '#4F8EF7', animation: 'spin 1s linear infinite' }} />}
                                </div>
                            </div>

                            {filteredGroups.length === 0 ? (
                                <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                                    {searchQuery ? 'Brak wyników dla podanego filtra' : 'Brak danych dla wybranego okresu'}
                                </div>
                            ) : (
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                                <th style={TH}>Grupa</th>
                                                <th style={TH}>Typ</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Bid (zł)</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Impr.</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Koszt (zł)</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>Konw.</th>
                                                <th style={{ ...TH, textAlign: 'right' }}>ROAS</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredGroups.map((row, i) => {
                                                const roas = computeRoas(row)
                                                return (
                                                    <tr
                                                        key={row.id ?? i}
                                                        style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                                                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                                                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                                    >
                                                        <td style={TD_DIM}>{row.name || row.resource_name || '—'}</td>
                                                        <td style={TD}>
                                                            <span style={{
                                                                fontSize: 11, padding: '2px 8px', borderRadius: 999,
                                                                background: 'rgba(79,142,247,0.12)', color: '#4F8EF7',
                                                                fontFamily: 'DM Sans, sans-serif',
                                                            }}>
                                                                {row.product_group_type || row.type || 'SUBDIVISION'}
                                                            </span>
                                                        </td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.bid_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.clicks)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.impressions)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.cost_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.conversions)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>
                                                            <RoasBadge value={roas} />
                                                        </td>
                                                    </tr>
                                                )
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── Performance Tab ── */}
                    {activeTab === 'performance' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                            {/* Top Performers */}
                            <div className="v2-card" style={{ padding: 0 }}>
                                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <TrendingUp size={16} style={{ color: '#4ADE80' }} />
                                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                                        Top 5 — najwyższy ROAS
                                    </span>
                                </div>

                                {topPerformers.length === 0 ? (
                                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                                        Brak danych do analizy (wymagany koszt > 0)
                                    </div>
                                ) : (
                                    <div style={{ overflowX: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                                    <th style={{ ...TH, width: 32 }}>#</th>
                                                    <th style={TH}>Grupa</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Koszt (zł)</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Konw.</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Wart. konw. (zł)</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>ROAS</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {topPerformers.map((row, i) => (
                                                    <tr
                                                        key={row.id ?? i}
                                                        style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                                                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                                                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                                    >
                                                        <td style={{ ...TD, color: '#4ADE80', fontWeight: 600 }}>{i + 1}</td>
                                                        <td style={TD_DIM}>{row.name || row.resource_name || '—'}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.clicks)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.cost_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.conversions)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.conversion_value_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>
                                                            <RoasBadge value={row._roas} />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>

                            {/* Bottom Performers */}
                            <div className="v2-card" style={{ padding: 0 }}>
                                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', gap: 10 }}>
                                    <TrendingDown size={16} style={{ color: '#F87171' }} />
                                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                                        Bottom 5 — najniższy ROAS
                                    </span>
                                </div>

                                {bottomPerformers.length === 0 ? (
                                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                                        Brak danych do analizy (wymagany koszt > 0)
                                    </div>
                                ) : (
                                    <div style={{ overflowX: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                                    <th style={{ ...TH, width: 32 }}>#</th>
                                                    <th style={TH}>Grupa</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Koszt (zł)</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Konw.</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>Wart. konw. (zł)</th>
                                                    <th style={{ ...TH, textAlign: 'right' }}>ROAS</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {bottomPerformers.map((row, i) => (
                                                    <tr
                                                        key={row.id ?? i}
                                                        style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                                                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                                                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                                    >
                                                        <td style={{ ...TD, color: '#F87171', fontWeight: 600 }}>{i + 1}</td>
                                                        <td style={TD_DIM}>{row.name || row.resource_name || '—'}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.clicks)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.cost_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.conversions)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.conversion_value_micros)}</td>
                                                        <td style={{ ...TD, textAlign: 'right' }}>
                                                            <RoasBadge value={row._roas} />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>

                            {/* Summary stats */}
                            {groupsWithRoas.length > 0 && (
                                <div className="v2-card" style={{ padding: '20px 24px' }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)', marginBottom: 16 }}>
                                        Podsumowanie ROAS
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                                        {[
                                            { label: 'Grupy z ROAS > 4', count: groupsWithRoas.filter((r) => r._roas >= 4).length, color: '#4ADE80' },
                                            { label: 'Grupy z ROAS 2–4', count: groupsWithRoas.filter((r) => r._roas >= 2 && r._roas < 4).length, color: '#FBBF24' },
                                            { label: 'Grupy z ROAS < 2', count: groupsWithRoas.filter((r) => r._roas < 2).length, color: '#F87171' },
                                        ].map((item) => (
                                            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <div style={{
                                                    width: 36, height: 36, borderRadius: 10,
                                                    background: `${item.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontSize: 16, fontWeight: 700, fontFamily: 'Syne, sans-serif', color: item.color,
                                                }}>
                                                    {item.count}
                                                </div>
                                                <span style={{ fontSize: 12, fontFamily: 'DM Sans, sans-serif', color: 'rgba(255,255,255,0.5)' }}>
                                                    {item.label}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── Feed Health Tab ── */}
                    {activeTab === 'feed_health' && (
                        <div className="v2-card" style={{ padding: 0 }}>
                            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                                    Feed Health
                                </span>
                            </div>
                            <div style={{ padding: 32 }}>
                                <EmptyState message="Diagnostyka feedu produktowego — wkrótce" />
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
