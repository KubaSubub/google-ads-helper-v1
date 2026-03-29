import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
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

export default function ShoppingPage() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days } = useFilter()

    const [productGroups, setProductGroups] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!selectedClientId) return
        setLoading(true)
        getShoppingProductGroups(selectedClientId, allParams)
            .then((data) => setProductGroups(Array.isArray(data) ? data : []))
            .catch(() => showToast('Błąd ładowania grup produktów', 'error'))
            .finally(() => setLoading(false))
    }, [selectedClientId, allParams])

    if (!selectedClientId) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <PageHeader title="Produkty (Shopping)" subtitle="Wybierz klienta aby zobaczyć dane" />
                <EmptyState message="Brak wybranego klienta" />
            </div>
        )
    }

    // Aggregate KPIs
    const totalClicks = productGroups.reduce((s, r) => s + (r.clicks || 0), 0)
    const totalCostMicros = productGroups.reduce((s, r) => s + (r.cost_micros || 0), 0)
    const totalCost = totalCostMicros / 1e6
    const totalConversions = productGroups.reduce((s, r) => s + (r.conversions || 0), 0)
    const avgCpa = totalConversions > 0 ? totalCost / totalConversions : null

    const kpiCards = [
        { label: 'Kliknięcia', value: fmtInt(totalClicks), color: '#4F8EF7' },
        { label: 'Koszt (PLN)', value: `${totalCost.toFixed(2)} zł`, color: '#7B5CE0' },
        { label: 'Konwersje', value: fmt(totalConversions), color: '#4ADE80' },
        { label: 'Śr. CPA', value: avgCpa !== null ? `${avgCpa.toFixed(2)} zł` : '—', color: '#FBBF24' },
    ]

    return (
        <div style={{ maxWidth: 1400 }}>
            <PageHeader title="Produkty (Shopping)" subtitle={`Analiza ${days} dni`} />

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
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

            {/* Product Groups Table */}
            <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                        Grupy produktów
                    </span>
                    {loading && <Loader2 size={16} style={{ color: '#4F8EF7', animation: 'spin 1s linear infinite' }} />}
                </div>

                {loading && productGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
                        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
                        <div>Ładowanie danych…</div>
                    </div>
                ) : productGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak danych dla wybranego okresu
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
                                </tr>
                            </thead>
                            <tbody>
                                {productGroups.map((row, i) => (
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
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Feed Health Placeholder */}
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
        </div>
    )
}
