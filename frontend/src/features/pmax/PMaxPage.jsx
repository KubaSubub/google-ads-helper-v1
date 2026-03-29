import { useState, useEffect } from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'
import {
    getAssetGroupPerformance,
    getPmaxChannels,
    getPmaxChannelTrends,
    getPmaxSearchThemes,
    getPmaxSearchCannibalization,
} from '../../api'
import { PageHeader } from '../../components/UI'
import EmptyState from '../../components/EmptyState'
import { TH, TD, TD_DIM, AD_STRENGTH_COLOR, CHANNEL_COLORS } from '../../constants/designTokens'

const fmt = (n, d = 2) => (typeof n === 'number' ? n.toFixed(d) : '—')
const fmtInt = (n) => (typeof n === 'number' ? n.toLocaleString('pl-PL') : '—')
const fmtCost = (micros) => (typeof micros === 'number' ? (micros / 1e6).toFixed(2) : '—')
const fmtCpa = (cost, conv) => (conv > 0 ? (cost / conv).toFixed(2) : '—')
const fmtRoas = (value, cost) => (cost > 0 ? (value / cost).toFixed(2) : '—')

function AdStrengthBadge({ strength }) {
    const color = AD_STRENGTH_COLOR[strength] || 'rgba(255,255,255,0.4)'
    return (
        <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 999,
            background: `${color}1A`, color,
            fontFamily: 'DM Sans, sans-serif', fontWeight: 600,
        }}>
            {strength || '—'}
        </span>
    )
}

export default function PMaxPage() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days } = useFilter()

    const [assetGroups, setAssetGroups] = useState([])
    const [channels, setChannels] = useState([])
    const [searchThemes, setSearchThemes] = useState([])
    const [cannibalization, setCannibalization] = useState(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!selectedClientId) return
        setLoading(true)
        Promise.all([
            getAssetGroupPerformance(selectedClientId, allParams).catch(() => []),
            getPmaxChannels(selectedClientId, allParams).catch(() => []),
            getPmaxChannelTrends(selectedClientId, allParams).catch(() => []),
            getPmaxSearchThemes(selectedClientId, allParams).catch(() => []),
            getPmaxSearchCannibalization(selectedClientId, allParams).catch(() => null),
        ])
            .then(([ag, ch, , themes, cann]) => {
                setAssetGroups(Array.isArray(ag) ? ag : [])
                setChannels(Array.isArray(ch) ? ch : [])
                setSearchThemes(Array.isArray(themes) ? themes : [])
                setCannibalization(cann)
            })
            .catch(() => showToast('Błąd ładowania danych PMax', 'error'))
            .finally(() => setLoading(false))
    }, [selectedClientId, allParams])

    if (!selectedClientId) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <PageHeader title="Performance Max" subtitle="Wybierz klienta aby zobaczyć dane" />
                <EmptyState message="Brak wybranego klienta" />
            </div>
        )
    }

    // Aggregate KPIs from channels
    const totalCostMicros = channels.reduce((s, r) => s + (r.cost_micros || 0), 0)
    const totalCost = totalCostMicros / 1e6
    const totalConversions = channels.reduce((s, r) => s + (r.conversions || 0), 0)
    const channelCount = channels.length

    const kpiCards = [
        { label: 'Łączny koszt', value: `${totalCost.toFixed(2)} zł`, color: '#7B5CE0' },
        { label: 'Konwersje', value: fmt(totalConversions), color: '#4ADE80' },
        { label: 'Kanały', value: String(channelCount), color: '#4F8EF7' },
    ]

    // Cannibalization overlapping terms
    const overlappingTerms = cannibalization?.overlapping_terms ?? []
    const hasCannibalization = overlappingTerms.length > 0

    return (
        <div style={{ maxWidth: 1400 }}>
            <PageHeader title="Performance Max" subtitle={`Analiza ${days} dni`} />

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
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

            {/* Cannibalization Alert */}
            {hasCannibalization && (
                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 24, borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <AlertTriangle size={16} style={{ color: '#F87171' }} />
                        <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: '#F87171' }}>
                            Wykryto kanibalizację słów kluczowych ({overlappingTerms.length} fraz)
                        </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {overlappingTerms.slice(0, 20).map((term, i) => (
                            <span key={i} style={{
                                fontSize: 11, padding: '3px 10px', borderRadius: 999,
                                background: 'rgba(248,113,113,0.12)', color: '#F87171',
                                fontFamily: 'DM Sans, sans-serif',
                            }}>
                                {term.search_term || term.query || (typeof term === 'string' ? term : term.text || '—')}
                            </span>
                        ))}
                        {overlappingTerms.length > 20 && (
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', alignSelf: 'center' }}>
                                +{overlappingTerms.length - 20} więcej
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Asset Groups Table */}
            <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                        Grupy zasobów (Asset Groups)
                    </span>
                    {loading && <Loader2 size={16} style={{ color: '#4F8EF7', animation: 'spin 1s linear infinite' }} />}
                </div>

                {loading && assetGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif' }}>
                        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
                        <div>Ładowanie danych…</div>
                    </div>
                ) : assetGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak grup zasobów dla wybranego okresu
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                    <th style={TH}>Nazwa</th>
                                    <th style={TH}>Ad Strength</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Koszt (zł)</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Konw.</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>CPA (zł)</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>ROAS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {assetGroups.map((row, i) => {
                                    const cost = (row.cost_micros || 0) / 1e6
                                    const conv = row.conversions || 0
                                    const value = (row.conversion_value_micros || 0) / 1e6
                                    return (
                                        <tr
                                            key={row.id ?? i}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                                            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                        >
                                            <td style={TD_DIM}>{row.name || row.asset_group_name || '—'}</td>
                                            <td style={TD}><AdStrengthBadge strength={row.ad_strength} /></td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{cost.toFixed(2)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmt(conv)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmtCpa(cost, conv)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmtRoas(value, cost)}</td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Channel Breakdown Table */}
            <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                        Rozkład kanałów
                    </span>
                </div>

                {channels.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak danych kanałów
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                                    <th style={TH}>Kanał</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Kliknięcia</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Koszt (zł)</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Konw.</th>
                                    <th style={{ ...TH, textAlign: 'right' }}>Udział kosztu</th>
                                </tr>
                            </thead>
                            <tbody>
                                {channels.map((row, i) => {
                                    const network = row.network_type || row.channel || 'UNKNOWN'
                                    const channelColor = CHANNEL_COLORS[network] || 'rgba(255,255,255,0.5)'
                                    const costShare = row.cost_share_pct ?? null
                                    return (
                                        <tr
                                            key={i}
                                            style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.15s' }}
                                            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                        >
                                            <td style={TD}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: channelColor, display: 'inline-block', flexShrink: 0 }} />
                                                    <span style={{ color: channelColor, fontFamily: 'DM Sans, sans-serif' }}>{network}</span>
                                                </span>
                                            </td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.clicks)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.cost_micros)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.conversions)}</td>
                                            <td style={{ ...TD, textAlign: 'right' }}>
                                                {costShare !== null ? (
                                                    <span style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                                                        <span style={{
                                                            display: 'inline-block', height: 4, width: Math.max(4, (costShare / 100) * 60),
                                                            borderRadius: 999, background: channelColor, opacity: 0.7,
                                                        }} />
                                                        <span>{costShare.toFixed(1)}%</span>
                                                    </span>
                                                ) : '—'}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Search Themes */}
            <div className="v2-card" style={{ padding: '16px 20px' }}>
                <div style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)', marginBottom: 14 }}>
                    Motywy wyszukiwania (Search Themes)
                </div>
                {searchThemes.length === 0 ? (
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak motywów wyszukiwania dla wybranej kampanii
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {searchThemes.map((theme, i) => (
                            <span key={i} style={{
                                fontSize: 12, padding: '4px 12px', borderRadius: 999,
                                background: 'rgba(79,142,247,0.12)', color: '#4F8EF7',
                                border: '1px solid rgba(79,142,247,0.25)',
                                fontFamily: 'DM Sans, sans-serif',
                            }}>
                                {theme.text || theme.theme || theme}
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
