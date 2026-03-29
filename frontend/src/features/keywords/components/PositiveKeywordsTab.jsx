import { useEffect, useState, useRef } from 'react'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Loader2, PauseCircle, TrendingDown, TrendingUp, X } from 'lucide-react'

import { MetricTooltip } from '../../../components/MetricTooltip'
import { ErrorMessage, StatusBadge, TH_STYLE } from '../../../components/UI'
import { getKeywords } from '../../../api'
import {
    MATCH_COLORS,
    PILL_STYLE,
    SERVING_STATUS_CONFIG,
} from './shared'

/* ── Helper components ── */

function QSBadge({ score }) {
    if (score == null) return <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 11 }}>-</span>
    const color = score <= 3 ? '#F87171' : score <= 6 ? '#FBBF24' : '#4ADE80'
    const bg = score <= 3 ? 'rgba(248,113,113,0.1)' : score <= 6 ? 'rgba(251,191,36,0.1)' : 'rgba(74,222,128,0.1)'
    return (
        <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: bg, color }}>
            {score}/10
        </span>
    )
}

function ServingStatusBadge({ status }) {
    if (!status || status === 'ELIGIBLE') return null
    const config = SERVING_STATUS_CONFIG[status] || { label: status, color: 'rgba(255,255,255,0.4)' }
    return (
        <span title={`Problem emisji: ${config.label}`} style={{
            display: 'inline-flex', alignItems: 'center', fontSize: 9, fontWeight: 600,
            padding: '2px 6px', borderRadius: 999,
            background: `${config.color}15`, color: config.color, border: `1px solid ${config.color}30`,
        }}>
            {config.label}
        </span>
    )
}

function KeywordAction({ icon: Icon, label, color, bg, border, title, onClick }) {
    return (
        <button onClick={onClick} title={title} aria-label={label} style={{
            display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 600,
            padding: '3px 8px', borderRadius: 6, background: bg, color, border: `1px solid ${border}`, cursor: 'pointer', whiteSpace: 'nowrap',
        }}>
            <Icon size={10} />{label}
        </button>
    )
}

function getKeywordHint(keyword) {
    const cost = keyword.cost || 0
    const conversions = keyword.conversions || 0
    const clicks = keyword.clicks || 0
    if (cost > 50 && conversions === 0 && clicks >= 10) {
        return { type: 'pause', label: 'Pauzuj', title: 'Koszt > 50 zl, brak konwersji, >= 10 klikniec.', icon: PauseCircle, color: '#F87171', bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.2)' }
    }
    if (conversions >= 5 && clicks > 0 && (conversions / clicks * 100) > 5) {
        return { type: 'bid_up', label: 'Podnies', title: '>= 5 konwersji, CVR > 5%.', icon: TrendingUp, color: '#4ADE80', bg: 'rgba(74,222,128,0.08)', border: 'rgba(74,222,128,0.2)' }
    }
    if (conversions > 0 && cost > 100 && (cost / conversions) > 50) {
        return { type: 'bid_down', label: 'Obniz', title: 'CPA > 50 zl.', icon: TrendingDown, color: '#FBBF24', bg: 'rgba(251,191,36,0.08)', border: 'rgba(251,191,36,0.2)' }
    }
    return null
}

function KeywordCell({ keyword }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{keyword.text}</span>
            <div className="flex items-center gap-2 flex-wrap"><ServingStatusBadge status={keyword.serving_status} /></div>
        </div>
    )
}

function CampaignCell({ keyword }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
            <span style={{ fontSize: 12, color: '#F0F0F0', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{keyword.campaign_name || '-'}</span>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{keyword.ad_group_name || '-'}</span>
        </div>
    )
}

function MatchBadge({ matchType }) {
    const config = MATCH_COLORS[matchType]
    if (!config) return <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{matchType || '-'}</span>
    return (
        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: config.bg, color: config.color, border: `1px solid ${config.border}` }}>
            {matchType}
        </span>
    )
}

function Pagination({ page, totalPages, setPage }) {
    return (
        <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>Strona {page} z {totalPages}</span>
            <div className="flex items-center gap-1">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page <= 1 ? 0.3 : 1 }}>
                    <ChevronLeft size={14} />
                </button>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page >= totalPages ? 0.3 : 1 }}>
                    <ChevronRight size={14} />
                </button>
            </div>
        </div>
    )
}

/* ── Main component ── */

export default function PositiveKeywordsTab({ selectedClientId, showToast, filters, searchParams, setSearchParams }) {
    const campaignId = searchParams.get('campaign_id')
    const campaignName = searchParams.get('campaign_name')

    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [sortBy, setSortBy] = useState('cost')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [matchFilter, setMatchFilter] = useState('')
    const [includeRemoved, setIncludeRemoved] = useState(false)

    // Reset page and fetch data in a single effect to avoid double requests
    const filterKey = `${selectedClientId}-${campaignId}-${filters.campaignType}-${filters.status}-${filters.dateFrom}-${filters.dateTo}-${matchFilter}-${includeRemoved}`
    const prevFilterKey = useRef(filterKey)

    useEffect(() => {
        if (!selectedClientId) return
        if (prevFilterKey.current !== filterKey) {
            prevFilterKey.current = filterKey
            if (page !== 1) {
                setPage(1)
                // loadData will fire on the next render when page changes to 1
                return
            }
        }
        loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [page, sortBy, sortOrder, filterKey])

    async function loadData() {
        setLoading(true); setError(null)
        try {
            const params = { page, page_size: 50, sort_by: sortBy, sort_order: sortOrder, client_id: selectedClientId, include_removed: includeRemoved }
            if (campaignId) params.campaign_id = campaignId
            if (matchFilter) params.match_type = matchFilter
            if (filters.campaignType !== 'ALL') params.campaign_type = filters.campaignType
            if (filters.status !== 'ALL') params.campaign_status = filters.status
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            const response = await getKeywords(params)
            setData(response)
        } catch (err) { setError(err.message) } finally { setLoading(false) }
    }

    function clearCampaignFilter() {
        const nextParams = new URLSearchParams(searchParams)
        nextParams.delete('campaign_id'); nextParams.delete('campaign_name')
        setSearchParams(nextParams); setPage(1)
    }
    function handleSort(field) {
        if (sortBy === field) { setSortOrder(o => o === 'asc' ? 'desc' : 'asc'); return }
        setSortBy(field); setSortOrder('desc')
    }
    function handleExport(format) {
        const params = new URLSearchParams({ client_id: String(selectedClientId), format, include_removed: includeRemoved ? 'true' : 'false' })
        if (campaignId) params.set('campaign_id', campaignId)
        window.location.href = `/api/v1/export/keywords?${params.toString()}`
    }

    if (error) return <ErrorMessage message={error} onRetry={loadData} />
    const totalPages = Math.max(1, data.total_pages || 1)

    return (
        <>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
                    {data.total} słów kluczowych
                    {campaignName && (
                        <span style={{ marginLeft: 8, padding: '2px 8px', borderRadius: 999, fontSize: 11, background: 'rgba(79,142,247,0.12)', border: '1px solid rgba(79,142,247,0.25)', color: '#4F8EF7', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            {decodeURIComponent(campaignName)}
                            <X size={10} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={clearCampaignFilter} />
                        </span>
                    )}
                </p>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-1 flex-wrap">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(match => (
                            <button key={match || 'ALL'} onClick={() => { setMatchFilter(match); setPage(1) }}
                                style={PILL_STYLE(matchFilter === match, match ? MATCH_COLORS[match]?.color : null)}>
                                {match || 'Wszystkie'}
                            </button>
                        ))}
                    </div>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 10px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.1)', background: includeRemoved ? 'rgba(248,113,113,0.08)' : 'rgba(255,255,255,0.03)', color: includeRemoved ? '#FCA5A5' : 'rgba(255,255,255,0.55)', fontSize: 11, cursor: 'pointer' }}>
                        <input type="checkbox" checked={includeRemoved} onChange={e => setIncludeRemoved(e.target.checked)} />
                        Pokaż usunięte
                    </label>
                    <div className="flex items-center gap-1">
                        <button onClick={() => handleExport('csv')} title="Eksportuj CSV" style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}>
                            <Download size={12} /> CSV
                        </button>
                        <button onClick={() => handleExport('xlsx')} title="Eksportuj Excel" style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ADE80', cursor: 'pointer' }}>
                            <Download size={12} /> XLSX
                        </button>
                    </div>
                </div>
            </div>

            <div className="v2-card" style={{ overflow: 'hidden' }}>
                {loading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
                        <Loader2 size={24} style={{ color: '#4F8EF7' }} className="animate-spin" />
                    </div>
                ) : (
                    <>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                        <th style={TH_STYLE}>Slowo kluczowe</th>
                                        <th style={TH_STYLE}>Kampania</th>
                                        <th style={TH_STYLE}>Dopasowanie</th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('clicks')}>
                                            <span className="flex items-center gap-1">Klikniecia {sortBy === 'clicks' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('impressions')}>
                                            <span className="flex items-center gap-1">Wyswietlenia {sortBy === 'impressions' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('cost')}>
                                            <span className="flex items-center gap-1">Koszt {sortBy === 'cost' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('conversions')}>
                                            <span className="flex items-center gap-1">Konwersje {sortBy === 'conversions' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('ctr')}>
                                            <span className="flex items-center gap-1"><MetricTooltip term="CTR" inline>CTR</MetricTooltip> {sortBy === 'ctr' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('avg_cpc')}>
                                            <span className="flex items-center gap-1"><MetricTooltip term="CPC" inline>Avg CPC</MetricTooltip> {sortBy === 'avg_cpc' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={TH_STYLE}><MetricTooltip term="QS" inline>QS</MetricTooltip></th>
                                        <th style={TH_STYLE}>Status</th>
                                        <th style={TH_STYLE}><MetricTooltip term="ROAS" inline>ROAS</MetricTooltip></th>
                                        <th style={TH_STYLE}><MetricTooltip term="Impression Share" inline>IS %</MetricTooltip></th>
                                        <th style={TH_STYLE}>Akcje</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.items.length === 0 && (
                                        <tr><td colSpan={14} style={{ padding: '32px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>Brak słów kluczowych dla wybranych filtrów.</td></tr>
                                    )}
                                    {data.items.map((keyword, index) => {
                                        const hint = getKeywordHint(keyword)
                                        return (
                                            <tr key={keyword.id || index} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
                                                onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
                                                <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 280 }}><KeywordCell keyword={keyword} /></td>
                                                <td style={{ padding: '10px 12px', maxWidth: 260 }}><CampaignCell keyword={keyword} /></td>
                                                <td style={{ padding: '10px 12px' }}><MatchBadge matchType={keyword.match_type} /></td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.clicks?.toLocaleString('pl-PL') ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.impressions?.toLocaleString('pl-PL') ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.cost != null ? `${keyword.cost.toFixed(2)} zl` : '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.conversions?.toFixed(1) ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.ctr != null ? `${keyword.ctr.toFixed(2)}%` : '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.avg_cpc != null ? `${keyword.avg_cpc.toFixed(2)} zl` : '-'}</td>
                                                <td style={{ padding: '10px 12px' }}><QSBadge score={keyword.quality_score} /></td>
                                                <td style={{ padding: '10px 12px' }}><StatusBadge status={keyword.status} /></td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.roas != null ? keyword.roas.toFixed(2) : '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.search_impression_share != null ? `${(keyword.search_impression_share * 100).toFixed(1)}%` : '-'}</td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    {hint && <KeywordAction icon={hint.icon} label={hint.label} color={hint.color} bg={hint.bg} border={hint.border} title={hint.title} onClick={() => showToast(`"${keyword.text}" -> przejdz do Rekomendacje`, 'info')} />}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                        <Pagination page={page} totalPages={totalPages} setPage={setPage} />
                    </>
                )}
            </div>
        </>
    )
}
