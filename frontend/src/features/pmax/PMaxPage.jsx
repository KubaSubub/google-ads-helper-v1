import React, { useState, useEffect } from 'react'
import { Loader2, AlertTriangle, ChevronUp, ChevronDown, ChevronRight, Layers, TrendingUp, TrendingDown, Award } from 'lucide-react'
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
const fmtCpa = (costMicros, conv) => (conv > 0 ? ((costMicros / 1e6) / conv).toFixed(2) : '—')

const STRENGTH_TOOLTIPS = {
    EXCELLENT: 'Doskonala jakość zasobów. Wszystkie kluczowe zasoby obecne i dobrze zoptymalizowane.',
    GOOD: 'Dobra jakość. Drobne usprawnienia mogą poprawić wynik.',
    AVERAGE: 'Przeciętna jakość. Dodaj więcej wariantów nagłówków, opisów lub obrazów.',
    POOR: 'Niska jakość. Brakuje kluczowych zasobów — uzupełnij jak najszybciej.',
}

const STRENGTH_ORDER = ['EXCELLENT', 'GOOD', 'AVERAGE', 'POOR']

const ROAS_COLOR = (roas) => {
    if (typeof roas !== 'number') return 'transparent'
    if (roas >= 4) return 'rgba(74,222,128,0.08)'
    if (roas >= 2) return 'rgba(251,191,36,0.06)'
    return 'rgba(248,113,113,0.06)'
}
const ROAS_BORDER = (roas) => {
    if (typeof roas !== 'number') return C.w04
    if (roas >= 4) return 'rgba(74,222,128,0.15)'
    if (roas >= 2) return 'rgba(251,191,36,0.12)'
    return 'rgba(248,113,113,0.12)'
}

function AdStrengthBadge({ strength }) {
    const color = AD_STRENGTH_COLOR[strength] || C.w40
    const tooltip = STRENGTH_TOOLTIPS[strength] || ''
    return (
        <span
            title={tooltip}
            style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 999,
                background: `${color}1A`, color,
                border: `1px solid ${color}33`,
                fontFamily: 'DM Sans, sans-serif', fontWeight: 600,
                cursor: tooltip ? 'help' : 'default',
            }}
        >
            {strength || '—'}
        </span>
    )
}

function PerformanceLabelBadge({ label }) {
    const colors = {
        BEST: C.success, GOOD: C.accentBlue, LOW: C.warning, LEARNING: C.w40,
    }
    const c = colors[label] || C.w30
    return (
        <span style={{
            fontSize: 10, padding: '1px 6px', borderRadius: 999,
            background: `${c}1A`, color: c,
            fontFamily: 'DM Sans, sans-serif', fontWeight: 500,
        }}>
            {label || '—'}
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

    // Asset Groups sorting & expand
    const [agSortBy, setAgSortBy] = useState('roas')
    const [agSortDir, setAgSortDir] = useState('desc')
    const [expandedAgId, setExpandedAgId] = useState(null)

    const toggleAgSort = (field) => {
        if (agSortBy === field) {
            setAgSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setAgSortBy(field)
            setAgSortDir('desc')
        }
    }

    const AgSortHeader = ({ field, children, align }) => (
        <th
            style={{ ...TH, textAlign: align || 'left', cursor: 'pointer', userSelect: 'none' }}
            onClick={() => toggleAgSort(field)}
        >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                {children}
                {agSortBy === field && (
                    agSortDir === 'asc'
                        ? <ChevronUp size={10} style={{ color: C.accentBlue }} />
                        : <ChevronDown size={10} style={{ color: C.accentBlue }} />
                )}
            </span>
        </th>
    )

    useEffect(() => {
        if (!selectedClientId) return
        setLoading(true)
        setExpandedAgId(null)
        Promise.all([
            getAssetGroupPerformance(selectedClientId, allParams).catch(() => ({ asset_groups: [] })),
            getPmaxChannels(selectedClientId, allParams).catch(() => []),
            getPmaxChannelTrends(selectedClientId, allParams).catch(() => []),
            getPmaxSearchThemes(selectedClientId, allParams).catch(() => []),
            getPmaxSearchCannibalization(selectedClientId, allParams).catch(() => null),
        ])
            .then(([ag, ch, , themes, cann]) => {
                const agList = ag?.asset_groups ?? (Array.isArray(ag) ? ag : [])
                setAssetGroups(agList)
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
        { label: 'Łączny koszt', value: `${totalCost.toFixed(2)} zł`, color: C.accentPurple },
        { label: 'Konwersje', value: fmt(totalConversions), color: C.success },
        { label: 'Kanały', value: String(channelCount), color: C.accentBlue },
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
                        <div style={{ fontSize: 11, fontWeight: 500, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>
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
                        <AlertTriangle size={16} style={{ color: C.danger }} />
                        <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: C.danger }}>
                            Wykryto kanibalizację słów kluczowych ({overlappingTerms.length} fraz)
                        </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {overlappingTerms.slice(0, 20).map((term, i) => (
                            <span key={i} style={{
                                fontSize: 11, padding: '3px 10px', borderRadius: 999,
                                background: 'rgba(248,113,113,0.12)', color: C.danger,
                                fontFamily: 'DM Sans, sans-serif',
                            }}>
                                {term.search_term || term.query || (typeof term === 'string' ? term : term.text || '—')}
                            </span>
                        ))}
                        {overlappingTerms.length > 20 && (
                            <span style={{ fontSize: 11, color: C.w30, fontFamily: 'DM Sans, sans-serif', alignSelf: 'center' }}>
                                +{overlappingTerms.length - 20} więcej
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Asset Groups — KPI Summary */}
            {assetGroups.length > 0 && (() => {
                const agCount = assetGroups.length
                const strengthCounts = {}
                STRENGTH_ORDER.forEach(s => { strengthCounts[s] = 0 })
                assetGroups.forEach(ag => {
                    const s = ag.ad_strength
                    if (s && strengthCounts[s] !== undefined) strengthCounts[s]++
                })
                const avgStrengthScore = (() => {
                    const scores = { EXCELLENT: 4, GOOD: 3, AVERAGE: 2, POOR: 1 }
                    const vals = assetGroups.map(ag => scores[ag.ad_strength] || 0).filter(v => v > 0)
                    return vals.length > 0 ? (vals.reduce((a, b) => a + b, 0) / vals.length) : 0
                })()
                const avgStrengthLabel = avgStrengthScore >= 3.5 ? 'EXCELLENT' : avgStrengthScore >= 2.5 ? 'GOOD' : avgStrengthScore >= 1.5 ? 'AVERAGE' : 'POOR'
                const topPerformer = [...assetGroups].sort((a, b) => (b.roas || 0) - (a.roas || 0))[0]
                const bottomPerformer = [...assetGroups].sort((a, b) => (a.roas || 0) - (b.roas || 0))[0]

                return (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                        {/* Total Groups */}
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 6 }}>
                                Grupy zasobów
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Layers size={16} style={{ color: C.accentBlue }} />
                                <span style={{ fontSize: 24, fontWeight: 700, fontFamily: 'Syne, sans-serif', color: C.accentBlue }}>{agCount}</span>
                            </div>
                        </div>

                        {/* Avg Ad Strength */}
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 6 }}>
                                Śr. Ad Strength
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Award size={16} style={{ color: AD_STRENGTH_COLOR[avgStrengthLabel] || '#fff' }} />
                                <AdStrengthBadge strength={avgStrengthLabel} />
                                <span style={{ fontSize: 11, color: C.w30, fontFamily: 'DM Sans, sans-serif' }}>({avgStrengthScore.toFixed(1)})</span>
                            </div>
                        </div>

                        {/* Top Performer */}
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 6 }}>
                                Najlepszy ROAS
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <TrendingUp size={16} style={{ color: C.success }} />
                                <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'Syne, sans-serif', color: C.success }}>{fmt(topPerformer?.roas)}</span>
                            </div>
                            <div style={{ fontSize: 11, color: C.w40, fontFamily: 'DM Sans, sans-serif', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {topPerformer?.name || '—'}
                            </div>
                        </div>

                        {/* Bottom Performer */}
                        <div className="v2-card" style={{ padding: '16px 20px' }}>
                            <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 6 }}>
                                Najsłabszy ROAS
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <TrendingDown size={16} style={{ color: C.danger }} />
                                <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'Syne, sans-serif', color: C.danger }}>{fmt(bottomPerformer?.roas)}</span>
                            </div>
                            <div style={{ fontSize: 11, color: C.w40, fontFamily: 'DM Sans, sans-serif', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {bottomPerformer?.name || '—'}
                            </div>
                        </div>
                    </div>
                )
            })()}

            {/* Asset Strength Distribution */}
            {assetGroups.length > 0 && (
                <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 24 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: C.w70, marginBottom: 12 }}>
                        Rozkład Ad Strength
                    </div>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                        {STRENGTH_ORDER.map(level => {
                            const count = assetGroups.filter(ag => ag.ad_strength === level).length
                            const pct = assetGroups.length > 0 ? ((count / assetGroups.length) * 100).toFixed(0) : 0
                            const color = AD_STRENGTH_COLOR[level]
                            return (
                                <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 140 }}>
                                    <span style={{
                                        fontSize: 11, padding: '2px 8px', borderRadius: 999,
                                        background: `${color}1A`, color, border: `1px solid ${color}33`,
                                        fontFamily: 'DM Sans, sans-serif', fontWeight: 600, minWidth: 70, textAlign: 'center',
                                    }}>
                                        {level}
                                    </span>
                                    <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'Syne, sans-serif', color }}>{count}</span>
                                    <div style={{ width: 48, height: 4, borderRadius: 999, background: C.w06, overflow: 'hidden' }}>
                                        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 999, transition: 'width 0.3s' }} />
                                    </div>
                                    <span style={{ fontSize: 10, color: C.w30, fontFamily: 'DM Sans, sans-serif' }}>{pct}%</span>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Asset Groups Table */}
            <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                <div style={{ padding: '16px 20px', borderBottom: B.card, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                        Grupy zasobów (Asset Groups)
                    </span>
                    {loading && <Loader2 size={16} style={{ color: C.accentBlue, animation: 'spin 1s linear infinite' }} />}
                </div>

                {loading && assetGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: C.w30, fontFamily: 'DM Sans, sans-serif' }}>
                        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
                        <div>Ładowanie danych...</div>
                    </div>
                ) : assetGroups.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: C.w30, fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak grup zasobów dla wybranego okresu
                    </div>
                ) : (() => {
                    const sorted = [...assetGroups].sort((a, b) => {
                        let av, bv
                        switch (agSortBy) {
                            case 'total_clicks': av = a.total_clicks || 0; bv = b.total_clicks || 0; break
                            case 'total_cost_micros': av = a.total_cost_micros || 0; bv = b.total_cost_micros || 0; break
                            case 'total_conversions': av = a.total_conversions || 0; bv = b.total_conversions || 0; break
                            case 'roas': av = a.roas || 0; bv = b.roas || 0; break
                            case 'cpa_micros': av = a.cpa_micros || 0; bv = b.cpa_micros || 0; break
                            case 'ad_strength': {
                                const order = { EXCELLENT: 4, GOOD: 3, AVERAGE: 2, POOR: 1 }
                                av = order[a.ad_strength] || 0; bv = order[b.ad_strength] || 0; break
                            }
                            case 'name': av = (a.name || '').toLowerCase(); bv = (b.name || '').toLowerCase(); break
                            default: av = a[agSortBy] ?? 0; bv = b[agSortBy] ?? 0
                        }
                        if (typeof av === 'string') return agSortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
                        return agSortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
                    })
                    return (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: B.card }}>
                                        <th style={{ ...TH, width: 28 }} />
                                        <AgSortHeader field="name">Nazwa</AgSortHeader>
                                        <AgSortHeader field="ad_strength">Ad Strength</AgSortHeader>
                                        <AgSortHeader field="total_clicks" align="right">Kliknięcia</AgSortHeader>
                                        <AgSortHeader field="total_cost_micros" align="right">Koszt (zł)</AgSortHeader>
                                        <AgSortHeader field="total_conversions" align="right">Konw.</AgSortHeader>
                                        <AgSortHeader field="cpa_micros" align="right">CPA (zł)</AgSortHeader>
                                        <AgSortHeader field="roas" align="right">ROAS</AgSortHeader>
                                    </tr>
                                </thead>
                                <tbody>
                                    {sorted.map((row, i) => {
                                        const roas = row.roas || 0
                                        const isExpanded = expandedAgId === (row.id ?? i)
                                        const roasColor = roas >= 4 ? C.success : roas >= 2 ? C.warning : C.danger
                                        return (
                                            <React.Fragment key={row.id ?? i}>
                                                <tr
                                                    style={{
                                                        borderBottom: isExpanded ? 'none' : `1px solid ${ROAS_BORDER(roas)}`,
                                                        background: ROAS_COLOR(roas),
                                                        transition: 'background 0.15s',
                                                        cursor: 'pointer',
                                                    }}
                                                    onClick={() => setExpandedAgId(prev => prev === (row.id ?? i) ? null : (row.id ?? i))}
                                                    onMouseEnter={(e) => { if (!isExpanded) e.currentTarget.style.background = C.w04 }}
                                                    onMouseLeave={(e) => { if (!isExpanded) e.currentTarget.style.background = ROAS_COLOR(roas) }}
                                                >
                                                    <td style={{ ...TD, width: 28, padding: '8px 4px 8px 12px' }}>
                                                        <ChevronRight
                                                            size={14}
                                                            style={{
                                                                color: C.w30,
                                                                transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                                                transition: 'transform 0.15s',
                                                            }}
                                                        />
                                                    </td>
                                                    <td style={{ ...TD, color: C.w70 }}>{row.name || '—'}</td>
                                                    <td style={TD}><AdStrengthBadge strength={row.ad_strength} /></td>
                                                    <td style={{ ...TD, textAlign: 'right' }}>{fmtInt(row.total_clicks)}</td>
                                                    <td style={{ ...TD, textAlign: 'right' }}>{fmtCost(row.total_cost_micros)}</td>
                                                    <td style={{ ...TD, textAlign: 'right' }}>{fmt(row.total_conversions)}</td>
                                                    <td style={{ ...TD, textAlign: 'right' }}>{fmtCpa(row.cpa_micros, 1)}</td>
                                                    <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: roasColor }}>{fmt(roas)}</td>
                                                </tr>
                                                {isExpanded && (
                                                    <tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: `1px solid ${ROAS_BORDER(roas)}` }}>
                                                        <td colSpan={8} style={{ padding: '0 20px 16px 40px' }}>
                                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8 }}>
                                                                {/* Assets */}
                                                                <div>
                                                                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>
                                                                        Zasoby ({row.asset_count || 0})
                                                                    </div>
                                                                    {row.assets && row.assets.length > 0 ? (
                                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                                            {row.assets.slice(0, 12).map((asset, ai) => (
                                                                                <div key={ai} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontFamily: 'DM Sans, sans-serif' }}>
                                                                                    <span style={{
                                                                                        fontSize: 9, padding: '1px 5px', borderRadius: 4,
                                                                                        background: C.infoBg, color: C.accentBlue,
                                                                                        fontWeight: 500, minWidth: 60, textAlign: 'center',
                                                                                    }}>
                                                                                        {asset.type}
                                                                                    </span>
                                                                                    <span style={{ color: C.w60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>
                                                                                        {asset.text || '(media)'}
                                                                                    </span>
                                                                                    {asset.performance_label && <PerformanceLabelBadge label={asset.performance_label} />}
                                                                                </div>
                                                                            ))}
                                                                            {row.assets.length > 12 && (
                                                                                <div style={{ fontSize: 10, color: C.w30, fontFamily: 'DM Sans, sans-serif' }}>
                                                                                    +{row.assets.length - 12} więcej
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    ) : (
                                                                        <div style={{ fontSize: 11, color: C.w25, fontFamily: 'DM Sans, sans-serif' }}>Brak danych o zasobach</div>
                                                                    )}
                                                                </div>

                                                                {/* Details */}
                                                                <div>
                                                                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'DM Sans, sans-serif', marginBottom: 8 }}>
                                                                        Szczegóły
                                                                    </div>
                                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11, fontFamily: 'DM Sans, sans-serif' }}>
                                                                        <div style={{ display: 'flex', gap: 8 }}>
                                                                            <span style={{ color: C.textMuted, minWidth: 80 }}>Status</span>
                                                                            <span style={{ color: C.w70 }}>{row.status || '—'}</span>
                                                                        </div>
                                                                        <div style={{ display: 'flex', gap: 8 }}>
                                                                            <span style={{ color: C.textMuted, minWidth: 80 }}>Impressions</span>
                                                                            <span style={{ color: C.w70 }}>{fmtInt(row.total_impressions)}</span>
                                                                        </div>
                                                                        <div style={{ display: 'flex', gap: 8 }}>
                                                                            <span style={{ color: C.textMuted, minWidth: 80 }}>CTR</span>
                                                                            <span style={{ color: C.w70 }}>
                                                                                {row.total_clicks && row.total_impressions
                                                                                    ? ((row.total_clicks / row.total_impressions) * 100).toFixed(2) + '%'
                                                                                    : '—'}
                                                                            </span>
                                                                        </div>
                                                                        <div style={{ display: 'flex', gap: 8 }}>
                                                                            <span style={{ color: C.textMuted, minWidth: 80 }}>Avg CPC</span>
                                                                            <span style={{ color: C.w70 }}>
                                                                                {row.total_clicks > 0 ? ((row.total_cost_micros || 0) / row.total_clicks / 1e6).toFixed(2) + ' zł' : '—'}
                                                                            </span>
                                                                        </div>
                                                                        {row.final_url && (
                                                                            <div style={{ display: 'flex', gap: 8 }}>
                                                                                <span style={{ color: C.textMuted, minWidth: 80 }}>URL</span>
                                                                                <span style={{ color: C.accentBlue, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 300 }}>
                                                                                    {row.final_url}
                                                                                </span>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                            </React.Fragment>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )
                })()}
            </div>

            {/* Channel Breakdown Table */}
            <div className="v2-card" style={{ padding: 0, marginBottom: 24 }}>
                <div style={{ padding: '16px 20px', borderBottom: B.card }}>
                    <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'Syne, sans-serif', color: 'rgba(255,255,255,0.9)' }}>
                        Rozkład kanałów
                    </span>
                </div>

                {channels.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: C.w30, fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak danych kanałów
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: B.card }}>
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
                                    const channelColor = CHANNEL_COLORS[network] || C.w50
                                    const costShare = row.cost_share_pct ?? null
                                    return (
                                        <tr
                                            key={i}
                                            style={{ borderBottom: `1px solid ${C.w04}`, transition: 'background 0.15s' }}
                                            onMouseEnter={(e) => (e.currentTarget.style.background = C.w03)}
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
                    <div style={{ color: C.w30, fontFamily: 'DM Sans, sans-serif', fontSize: 13 }}>
                        Brak motywów wyszukiwania dla wybranej kampanii
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {searchThemes.map((theme, i) => (
                            <span key={i} style={{
                                fontSize: 12, padding: '4px 12px', borderRadius: 999,
                                background: 'rgba(79,142,247,0.12)', color: C.accentBlue,
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
