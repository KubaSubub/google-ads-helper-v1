import { useState, useEffect, useCallback, useMemo } from 'react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import {
    AlertTriangle, CheckCircle, HelpCircle, ArrowRight, RefreshCw, Loader2,
    ChevronUp, ChevronDown, DollarSign, TrendingDown, Award, Download, ExternalLink
} from 'lucide-react'
import { getQualityScoreAudit } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import { useNavigateTo } from '../hooks/useNavigateTo'
import EmptyState from '../components/EmptyState'
import DarkSelect from '../components/DarkSelect'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const QS_COLORS = { low: C.danger, mid: C.warning, high: C.success }

function getQSColor(score) {
    if (score <= 3) return QS_COLORS.low
    if (score <= 6) return QS_COLORS.mid
    return QS_COLORS.high
}

const TH_STYLE = {
    padding: '10px 12px',
    fontSize: 10,
    fontWeight: 500,
    color: C.textMuted,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    whiteSpace: 'nowrap',
    textAlign: 'left',
    cursor: 'pointer',
    userSelect: 'none',
}

const SUBCOMP_LABELS = { 1: 'Poniżej średniej', 2: 'Średnia', 3: 'Powyżej średniej' }

function SubcomponentDot({ value, label }) {
    const color = value === 1 ? C.danger : value === 2 ? C.warning : value === 3 ? C.success : C.w15
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} title={`${label}: ${SUBCOMP_LABELS[value] || 'Brak danych'}`}>
            <div style={{
                width: 8, height: 8, borderRadius: '50%', background: color,
                boxShadow: value && value <= 2 ? `0 0 4px ${color}40` : 'none',
            }} />
        </div>
    )
}

const ISSUE_LABELS = {
    expected_ctr: { label: 'Oczekiwany CTR', color: C.accentBlue },
    ad_relevance: { label: 'Trafność reklamy', color: C.accentPurple },
    landing_page: { label: 'Strona docelowa', color: C.warning },
}

const QS_VIEWS = [
    { value: 'all', label: 'Wszystkie' },
    { value: 'low', label: 'Niski QS' },
    { value: 'high', label: 'Wysoki QS' },
]

export default function QualityScore() {
    const { selectedClientId } = useApp()
    const { filters } = useFilter()
    const navigateTo = useNavigateTo()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // Filters
    const [campaignId, setCampaignId] = useState('')
    const [matchType, setMatchType] = useState('')
    const [issueFilter, setIssueFilter] = useState('')
    const [qsView, setQsView] = useState('all')
    const [qsThreshold, setQsThreshold] = useState('5')
    const [groupByAg, setGroupByAg] = useState(false)

    // Sort
    const [sortBy, setSortBy] = useState('quality_score')
    const [sortDir, setSortDir] = useState('asc')

    const loadData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        setError(null)
        try {
            const params = {}
            if (campaignId) params.campaign_id = campaignId
            if (matchType) params.match_type = matchType
            if (qsThreshold && qsThreshold !== '5') params.qs_threshold = qsThreshold
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            const res = await getQualityScoreAudit(selectedClientId, params)
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [selectedClientId, campaignId, matchType, qsThreshold, filters.dateFrom, filters.dateTo])

    useEffect(() => { loadData() }, [loadData])

    // Reset filters when client changes
    useEffect(() => {
        setCampaignId('')
        setMatchType('')
        setIssueFilter('')
        setQsView('all')
        setQsThreshold('5')
    }, [selectedClientId])

    const toggleSort = (field) => {
        if (sortBy === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(field)
            setSortDir('asc')
        }
    }

    const SortHeader = ({ field, children, align }) => (
        <th
            style={{ ...TH_STYLE, textAlign: align || 'left' }}
            onClick={() => toggleSort(field)}
        >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                {children}
                {sortBy === field && (
                    sortDir === 'asc'
                        ? <ChevronUp size={10} style={{ color: C.accentBlue }} />
                        : <ChevronDown size={10} style={{ color: C.accentBlue }} />
                )}
            </span>
        </th>
    )

    // Filtered & sorted keywords
    const displayKeywords = useMemo(() => {
        if (!data?.keywords) return []
        let kws = [...data.keywords]

        // QS view filter
        if (qsView === 'low') kws = kws.filter(k => k.quality_score < (data.qs_threshold || 5))
        else if (qsView === 'high') kws = kws.filter(k => k.quality_score >= 8)

        // Issue filter (client-side)
        if (issueFilter) kws = kws.filter(k => k.primary_issue === issueFilter)

        // Sort
        kws.sort((a, b) => {
            const av = a[sortBy] ?? 0
            const bv = b[sortBy] ?? 0
            return sortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
        })

        return kws
    }, [data, qsView, issueFilter, sortBy, sortDir])

    // Ad group grouping
    const adGroupGroups = useMemo(() => {
        if (!groupByAg || !displayKeywords.length) return []
        const groups = {}
        for (const kw of displayKeywords) {
            const key = `${kw.campaign}||${kw.ad_group || 'Unknown'}`
            if (!groups[key]) groups[key] = { campaign: kw.campaign, ad_group: kw.ad_group || 'Unknown', keywords: [], totalQs: 0 }
            groups[key].keywords.push(kw)
            groups[key].totalQs += kw.quality_score
        }
        return Object.values(groups)
            .map(g => ({ ...g, avgQs: g.totalQs / g.keywords.length, count: g.keywords.length }))
            .sort((a, b) => a.avgQs - b.avgQs)
    }, [displayKeywords, groupByAg])

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    if (error) {
        return (
            <div style={{ maxWidth: 1200, padding: '40px 0', textAlign: 'center' }}>
                <div style={{ fontSize: 14, color: C.danger, marginBottom: 12 }}>Błąd: {error}</div>
                <button onClick={loadData} style={{ padding: '6px 16px', borderRadius: 7, fontSize: 12, background: C.accentBlue, color: 'white', border: 'none', cursor: 'pointer' }}>
                    Spróbuj ponownie
                </button>
            </div>
        )
    }

    if (loading || !data) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: C.accentBlue }} className="animate-spin" />
            </div>
        )
    }

    const chartData = Array.from({ length: 10 }, (_, i) => {
        const score = i + 1
        return {
            score: score.toString(),
            count: data.qs_distribution?.[`qs_${score}`] || 0,
            color: getQSColor(score),
        }
    })

    const campaignOptions = [
        { value: '', label: 'Wszystkie kampanie' },
        ...(data.available_campaigns || []).map(c => ({ value: String(c.id), label: c.name })),
    ]

    const matchTypeOptions = [
        { value: '', label: 'Wszystkie typy' },
        { value: 'EXACT', label: 'Dokładne' },
        { value: 'PHRASE', label: 'Do wyrażenia' },
        { value: 'BROAD', label: 'Przybliżone' },
    ]

    const issueOptions = [
        { value: '', label: 'Wszystkie problemy' },
        { value: 'expected_ctr', label: 'Oczekiwany CTR' },
        { value: 'ad_relevance', label: 'Trafność reklamy' },
        { value: 'landing_page', label: 'Strona docelowa' },
    ]

    const issueBreakdown = data.issue_breakdown || {}
    const maxIssueCount = Math.max(...Object.values(issueBreakdown), 1)

    return (
        <div style={{ maxWidth: 1200 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Audyt Quality Score
                    </h1>
                    <p style={{ fontSize: 12, color: C.textMuted, marginTop: 3 }}>
                        Analiza {data.total_keywords} słów kluczowych
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, background: C.w04, border: `1px solid ${C.w08}`, fontSize: 11, color: C.w40 }}>
                        <HelpCircle size={12} />
                        Cel: średni QS powyżej 7.0
                    </div>
                    <div className="flex items-center gap-1">
                        <button onClick={() => { window.location.href = `/api/v1/export/quality-score?client_id=${selectedClientId}&format=csv` }} style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: C.w04, border: B.medium, color: C.w50, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Download size={11} />CSV
                        </button>
                        <button onClick={() => { window.location.href = `/api/v1/export/quality-score?client_id=${selectedClientId}&format=xlsx` }} style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)', color: C.success, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Download size={11} />XLSX
                        </button>
                    </div>
                    <button
                        onClick={loadData}
                        style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, fontSize: 12, background: C.w05, border: B.medium, color: C.w60, cursor: 'pointer' }}
                        className="hover:border-white/20 hover:text-white/80"
                    >
                        <RefreshCw size={12} /> Odśwież
                    </button>
                </div>
            </div>

            {/* KPI Row — 5 cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
                {/* Średni QS */}
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #4F8EF7' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Średni QS
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: getQSColor(data.average_qs ?? 0), fontFamily: 'Syne' }}>
                        {data.average_qs != null ? data.average_qs.toFixed(1) : '—'}
                    </span>
                    <span style={{ fontSize: 13, color: C.w30, marginLeft: 4 }}>/10</span>
                </div>

                {/* Niski QS */}
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #F87171' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Niski QS (&lt;{data.qs_threshold})
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: C.danger, fontFamily: 'Syne' }}>
                        {data.low_qs_count}
                    </span>
                    <span style={{ fontSize: 11, color: 'rgba(248,113,113,0.5)', marginLeft: 6 }}>wymaga uwagi</span>
                </div>

                {/* Wysoki QS */}
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #4ADE80' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Wysoki QS (8-10)
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: C.success, fontFamily: 'Syne' }}>
                        {data.high_qs_count ?? 0}
                    </span>
                </div>

                {/* Wydatki na niski QS */}
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #FBBF24' }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        Wydatki na niski QS
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span style={{ fontSize: 22, fontWeight: 700, color: C.warning, fontFamily: 'Syne' }}>
                            {data.low_qs_spend_pct != null ? `${data.low_qs_spend_pct}%` : '—'}
                        </span>
                    </div>
                    <div style={{ fontSize: 10, color: C.w30, marginTop: 2 }}>
                        {data.low_qs_spend_usd != null ? `${data.low_qs_spend_usd.toFixed(2)} zł` : '—'} z budżetu
                    </div>
                </div>

                {/* IS utracony (ranking) */}
                <div className="v2-card" style={{ padding: '14px 18px', borderLeft: '3px solid #7B5CE0' }} title="Impression Share utracony z powodu niskiego rankingu reklamy (Quality Score + bid)">
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                        IS utracony (ranking)
                    </div>
                    <span style={{ fontSize: 26, fontWeight: 700, color: C.accentPurple, fontFamily: 'Syne' }}>
                        {data.avg_rank_lost_is != null ? `${data.avg_rank_lost_is}%` : '—'}
                    </span>
                    <div style={{ fontSize: 10, color: C.w30, marginTop: 2 }}>
                        średnia utrata z powodu QS + bid
                    </div>
                </div>
            </div>

            {/* Filter bar */}
            <div className="v2-card" style={{ padding: '12px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Filtry
                </div>
                <DarkSelect value={campaignId} onChange={setCampaignId} options={campaignOptions} style={{ minWidth: 180 }} />
                <DarkSelect value={matchType} onChange={setMatchType} options={matchTypeOptions} style={{ minWidth: 140 }} />
                <DarkSelect value={issueFilter} onChange={setIssueFilter} options={issueOptions} style={{ minWidth: 160 }} />
                <DarkSelect value={qsThreshold} onChange={setQsThreshold} options={[
                    { value: '3', label: 'QS < 3' },
                    { value: '4', label: 'QS < 4' },
                    { value: '5', label: 'QS < 5' },
                    { value: '6', label: 'QS < 6' },
                    { value: '7', label: 'QS < 7' },
                ]} style={{ minWidth: 100 }} />
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                    {QS_VIEWS.map(v => (
                        <button
                            key={v.value}
                            onClick={() => setQsView(v.value)}
                            style={{
                                padding: '5px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                                background: qsView === v.value ? C.infoBg : 'transparent',
                                color: qsView === v.value ? C.accentBlue : C.w40,
                                border: qsView === v.value ? '1px solid rgba(79,142,247,0.3)' : `1px solid ${C.w08}`,
                                cursor: 'pointer',
                            }}
                        >
                            {v.label}
                        </button>
                    ))}
                    <button
                        onClick={() => setGroupByAg(g => !g)}
                        style={{
                            padding: '5px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500,
                            background: groupByAg ? 'rgba(123,92,224,0.15)' : 'transparent',
                            color: groupByAg ? C.accentPurple : C.w40,
                            border: groupByAg ? '1px solid rgba(123,92,224,0.3)' : `1px solid ${C.w08}`,
                            cursor: 'pointer', marginLeft: 4,
                        }}
                    >
                        Grupuj
                    </button>
                </div>
            </div>

            {/* Charts row: QS Distribution + Issue Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                {/* QS Distribution chart */}
                <div className="v2-card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne', marginBottom: 16 }}>
                        Rozkład QS
                    </div>
                    <div style={{ height: 200 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis
                                    dataKey="score"
                                    tick={{ fill: C.w30, fontSize: 10 }}
                                    axisLine={false} tickLine={false}
                                />
                                <YAxis
                                    tick={{ fill: C.w30, fontSize: 10 }}
                                    axisLine={false} tickLine={false}
                                    allowDecimals={false} width={24}
                                />
                                <Tooltip
                                    cursor={{ fill: C.w03 }}
                                    contentStyle={{
                                        backgroundColor: C.surfaceElevated,
                                        borderColor: C.w12,
                                        borderRadius: '8px',
                                        color: C.textPrimary,
                                        fontSize: 12,
                                    }}
                                />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="flex justify-between" style={{ fontSize: 10, color: C.w25, marginTop: 8, padding: '0 4px' }}>
                        <span style={{ color: C.danger }}>Niski (1-3)</span>
                        <span style={{ color: C.warning }}>Średni (4-6)</span>
                        <span style={{ color: C.success }}>Wysoki (7-10)</span>
                    </div>
                </div>

                {/* Issue Breakdown */}
                <div className="v2-card" style={{ padding: '18px' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne', marginBottom: 16 }}>
                        Główne problemy
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: '8px 0' }}>
                        {Object.entries(ISSUE_LABELS).map(([key, cfg]) => {
                            const count = issueBreakdown[key] || 0
                            const pct = maxIssueCount > 0 ? (count / maxIssueCount) * 100 : 0
                            return (
                                <div key={key}>
                                    <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                                        <span style={{ fontSize: 12, color: C.w70, fontWeight: 500 }}>{cfg.label}</span>
                                        <span style={{ fontSize: 13, fontWeight: 700, color: cfg.color, fontFamily: 'Syne' }}>{count}</span>
                                    </div>
                                    <div style={{ height: 6, borderRadius: 3, background: C.w06, overflow: 'hidden' }}>
                                        <div style={{
                                            height: '100%', borderRadius: 3, background: cfg.color,
                                            width: `${pct}%`, transition: 'width 0.4s ease',
                                            opacity: 0.7,
                                        }} />
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                    <div style={{ fontSize: 10, color: C.w25, marginTop: 12 }}>
                        Słowa z subkomponentem poniżej średniej lub na średnim poziomie
                    </div>
                </div>
            </div>

            {/* Ad Group grouped view */}
            {groupByAg && adGroupGroups.length > 0 && (
                <div className="v2-card" style={{ overflow: 'hidden', marginBottom: 16 }}>
                    <div style={{ padding: '14px 18px', borderBottom: B.card }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                            Grupy reklam ({adGroupGroups.length})
                        </div>
                        <p style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
                            Średni QS per ad group — posortowane od najsłabszego
                        </p>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10, padding: 14 }}>
                        {adGroupGroups.map((g, i) => (
                            <div key={i} className="v2-card" style={{ padding: '12px 16px', borderLeft: `3px solid ${getQSColor(g.avgQs)}` }}>
                                <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                                    <div style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                        {g.ad_group}
                                    </div>
                                    <span style={{
                                        fontSize: 14, fontWeight: 700, color: getQSColor(g.avgQs), fontFamily: 'Syne',
                                    }}>
                                        {g.avgQs.toFixed(1)}
                                    </span>
                                </div>
                                <div style={{ fontSize: 10, color: C.w30, marginBottom: 4 }}>{g.campaign}</div>
                                <div style={{ fontSize: 11, color: C.w50 }}>
                                    {g.count} słów kluczowych
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Main table */}
            <div className="v2-card" style={{ overflow: 'hidden' }}>
                <div style={{ padding: '14px 18px', borderBottom: B.card }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                        Słowa kluczowe ({displayKeywords.length})
                    </div>
                    <p style={{ fontSize: 11, color: C.textMuted, marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                        Kliknij wiersz, aby przejść do zarządzania słowami kluczowymi
                        <span
                            onClick={() => navigateTo('keywords')}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11, color: C.accentBlue, cursor: 'pointer' }}
                        >
                            Słowa kluczowe <ArrowRight size={12} />
                        </span>
                    </p>
                </div>

                {displayKeywords.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center' }}>
                        <CheckCircle size={32} style={{ color: C.success, margin: '0 auto 10px' }} />
                        <div style={{ fontSize: 14, fontWeight: 500, color: C.textPrimary, marginBottom: 4 }}>Brak wyników</div>
                        <div style={{ fontSize: 12, color: C.textMuted }}>Zmień filtry, aby zobaczyć słowa kluczowe.</div>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
                            <thead>
                                <tr style={{ borderBottom: B.subtle }}>
                                    <SortHeader field="keyword">Słowo kluczowe</SortHeader>
                                    <SortHeader field="quality_score" align="center">QS</SortHeader>
                                    <th style={{ ...TH_STYLE, cursor: 'default', textAlign: 'center' }} title="Oczekiwany CTR / Trafność reklamy / Strona docelowa">
                                        <div style={{ display: 'flex', justifyContent: 'center', gap: 10 }}>
                                            <span style={{ fontSize: 9, color: C.w30 }}>CTR</span>
                                            <span style={{ fontSize: 9, color: C.w30 }}>Ad</span>
                                            <span style={{ fontSize: 9, color: C.w30 }}>LP</span>
                                        </div>
                                    </th>
                                    <SortHeader field="ctr_pct" align="right">CTR%</SortHeader>
                                    <SortHeader field="cost_usd" align="right">Koszt (zł)</SortHeader>
                                    <SortHeader field="impressions" align="right">Impr.</SortHeader>
                                    <SortHeader field="conversions" align="right">Konw.</SortHeader>
                                    <SortHeader field="search_rank_lost_is" align="right">IS lost</SortHeader>
                                    <th style={{ ...TH_STYLE, cursor: 'default' }}>Rekomendacja</th>
                                    <th style={{ ...TH_STYLE, cursor: 'default', textAlign: 'center', width: 36 }} title="Otwórz w Google Ads"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {displayKeywords.map((item, i) => (
                                    <tr key={item.keyword_id || i}
                                        style={{ borderBottom: `1px solid ${C.w04}`, transition: 'background 0.12s', cursor: 'pointer' }}
                                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        onClick={() => navigateTo('keywords')}
                                    >
                                        {/* Keyword + campaign */}
                                        <td style={{ padding: '10px 12px', maxWidth: 220 }}>
                                            <div style={{ fontSize: 13, fontWeight: 500, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {item.keyword}
                                            </div>
                                            <div style={{ fontSize: 10, color: C.w30, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {item.campaign} {item.ad_group && item.ad_group !== 'Unknown' && <span style={{ color: C.w20 }}>/ {item.ad_group}</span>}
                                                {item.match_type && <span style={{ marginLeft: 6, padding: '1px 5px', borderRadius: 3, background: C.w06, fontSize: 9 }}>{item.match_type}</span>}
                                            </div>
                                        </td>

                                        {/* QS badge */}
                                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                                            <span style={{
                                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                width: 30, height: 30, borderRadius: 8, fontWeight: 700, fontSize: 13,
                                                background: `${getQSColor(item.quality_score)}15`,
                                                color: getQSColor(item.quality_score),
                                            }}>
                                                {item.quality_score}
                                            </span>
                                        </td>

                                        {/* Subcomponent dots */}
                                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                                            <div style={{ display: 'flex', justifyContent: 'center', gap: 6 }}>
                                                <SubcomponentDot value={item.expected_ctr} label="CTR" />
                                                <SubcomponentDot value={item.ad_relevance} label="Reklama" />
                                                <SubcomponentDot value={item.landing_page} label="Strona" />
                                            </div>
                                        </td>

                                        {/* CTR% */}
                                        <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: C.w70 }}>
                                            {item.ctr_pct != null ? `${item.ctr_pct}%` : '—'}
                                        </td>

                                        {/* Cost */}
                                        <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: C.w70 }}>
                                            {item.cost_usd != null ? `${item.cost_usd.toFixed(2)}` : '—'}
                                        </td>

                                        {/* Impressions */}
                                        <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: C.w50 }}>
                                            {item.impressions?.toLocaleString() ?? '—'}
                                        </td>

                                        {/* Conversions */}
                                        <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: C.w70 }}>
                                            {item.conversions != null ? item.conversions : '—'}
                                        </td>

                                        {/* IS lost */}
                                        <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: item.search_rank_lost_is > 0.2 ? C.danger : C.w50 }}>
                                            {item.search_rank_lost_is != null ? `${(item.search_rank_lost_is * 100).toFixed(1)}%` : '—'}
                                        </td>

                                        {/* Recommendation */}
                                        <td style={{ padding: '10px 12px', maxWidth: 240 }}>
                                            {item.issues?.length > 0 ? (
                                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11, color: C.textSecondary, background: C.w03, padding: '6px 10px', borderRadius: 6, border: B.subtle }}>
                                                    <ArrowRight size={10} style={{ color: C.accentBlue, marginTop: 2, flexShrink: 0 }} />
                                                    <span>{item.recommendation}</span>
                                                </div>
                                            ) : (
                                                <CheckCircle size={14} style={{ color: 'rgba(74,222,128,0.4)' }} />
                                            )}
                                        </td>

                                        {/* Deep link to Google Ads */}
                                        <td style={{ padding: '10px 6px', textAlign: 'center' }}>
                                            {data.google_customer_id && item.google_keyword_id && (
                                                <a
                                                    href={`https://ads.google.com/aw/keywords?ocid=${data.google_customer_id}&keywordId=${item.google_keyword_id}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    onClick={e => e.stopPropagation()}
                                                    title="Otwórz w Google Ads"
                                                    style={{ color: C.w25, display: 'inline-flex' }}
                                                    className="hover:text-white/60"
                                                >
                                                    <ExternalLink size={12} />
                                                </a>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
