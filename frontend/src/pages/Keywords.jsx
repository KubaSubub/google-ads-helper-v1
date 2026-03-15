import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Loader2, PauseCircle, TrendingDown, TrendingUp, X } from 'lucide-react'

import EmptyState from '../components/EmptyState'
import { MetricTooltip } from '../components/MetricTooltip'
import { ErrorMessage, StatusBadge } from '../components/UI'
import { getKeywords } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'

const MATCH_COLORS = {
    EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
    PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
    BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
}

const SERVING_STATUS_CONFIG = {
    LOW_SEARCH_VOLUME: { label: 'Malo zapytan', color: '#FBBF24' },
    BELOW_FIRST_PAGE_BID: { label: 'Bid za niski', color: '#F87171' },
    RARELY_SERVED: { label: 'Rzadko', color: '#FBBF24' },
}

const TH_STYLE = {
    padding: '10px 12px',
    fontSize: 10,
    fontWeight: 500,
    color: 'rgba(255,255,255,0.35)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    whiteSpace: 'nowrap',
    textAlign: 'left',
}

function QSBadge({ score }) {
    if (score == null) return <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 11 }}>-</span>
    const color = score <= 3 ? '#F87171' : score <= 6 ? '#FBBF24' : '#4ADE80'
    const bg = score <= 3 ? 'rgba(248,113,113,0.1)' : score <= 6 ? 'rgba(251,191,36,0.1)' : 'rgba(74,222,128,0.1)'
    return (
        <span style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '2px 7px',
            borderRadius: 999,
            background: bg,
            color,
        }}>
            {score}/10
        </span>
    )
}

function ServingStatusBadge({ status }) {
    if (!status || status === 'ELIGIBLE') return null
    const config = SERVING_STATUS_CONFIG[status] || { label: status, color: 'rgba(255,255,255,0.4)' }
    return (
        <span
            title={`Problem emisji: ${config.label}`}
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                fontSize: 9,
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 999,
                background: `${config.color}15`,
                color: config.color,
                border: `1px solid ${config.color}30`,
            }}
        >
            {config.label}
        </span>
    )
}

function KeywordAction({ icon: Icon, label, color, bg, border, title, onClick }) {
    return (
        <button
            onClick={onClick}
            title={title}
            aria-label={label}
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                fontSize: 10,
                fontWeight: 600,
                padding: '3px 8px',
                borderRadius: 6,
                background: bg,
                color,
                border: `1px solid ${border}`,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
            }}
        >
            <Icon size={10} />
            {label}
        </button>
    )
}

function getKeywordHint(keyword) {
    const cost = keyword.cost || 0
    const conversions = keyword.conversions || 0
    const clicks = keyword.clicks || 0

    if (cost > 50 && conversions === 0 && clicks >= 10) {
        return {
            type: 'pause',
            label: 'Pauzuj',
            title: 'Koszt przekroczyl 50 zl, brak konwersji i jest co najmniej 10 klikniec. Rozwaz wstrzymanie hasla.',
            icon: PauseCircle,
            color: '#F87171',
            bg: 'rgba(248,113,113,0.08)',
            border: 'rgba(248,113,113,0.2)',
        }
    }

    if (conversions >= 5 && clicks > 0) {
        const conversionRate = conversions / clicks * 100
        if (conversionRate > 5) {
            return {
                type: 'bid_up',
                label: 'Podnies',
                title: 'Haslo ma co najmniej 5 konwersji i wspolczynnik konwersji powyzej 5%. To sygnal do rozwazenia wyzszej stawki.',
                icon: TrendingUp,
                color: '#4ADE80',
                bg: 'rgba(74,222,128,0.08)',
                border: 'rgba(74,222,128,0.2)',
            }
        }
    }

    if (conversions > 0 && cost > 100) {
        const cpa = cost / conversions
        if (cpa > 50) {
            return {
                type: 'bid_down',
                label: 'Obniz',
                title: 'Koszt przekroczyl 100 zl, a CPA jest powyzej 50 zl. To sygnal do rozwazenia nizszej stawki.',
                icon: TrendingDown,
                color: '#FBBF24',
                bg: 'rgba(251,191,36,0.08)',
                border: 'rgba(251,191,36,0.2)',
            }
        }
    }

    return null
}

function KeywordCell({ keyword }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0 }}>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {keyword.text}
            </span>
            <div className="flex items-center gap-2 flex-wrap">
                <ServingStatusBadge status={keyword.serving_status} />
            </div>
        </div>
    )
}

function CampaignCell({ keyword }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
            <span style={{ fontSize: 12, color: '#F0F0F0', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {keyword.campaign_name || '-'}
            </span>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {keyword.ad_group_name || '-'}
            </span>
        </div>
    )
}

export default function Keywords() {
    const { selectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [searchParams, setSearchParams] = useSearchParams()
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

    useEffect(() => {
        setPage(1)
    }, [selectedClientId, campaignId, filters.campaignType, filters.status, filters.dateFrom, filters.dateTo, matchFilter, includeRemoved])

    useEffect(() => {
        if (selectedClientId) {
            loadData()
        }
    }, [page, matchFilter, sortBy, sortOrder, selectedClientId, campaignId, filters.campaignType, filters.status, filters.dateFrom, filters.dateTo, includeRemoved])

    async function loadData() {
        setLoading(true)
        setError(null)
        try {
            const params = {
                page,
                page_size: 50,
                sort_by: sortBy,
                sort_order: sortOrder,
                client_id: selectedClientId,
                include_removed: includeRemoved,
            }
            if (campaignId) params.campaign_id = campaignId
            if (matchFilter) params.match_type = matchFilter
            if (filters.campaignType !== 'ALL') params.campaign_type = filters.campaignType
            if (filters.status !== 'ALL') params.campaign_status = filters.status
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            const response = await getKeywords(params)
            setData(response)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function clearCampaignFilter() {
        const nextParams = new URLSearchParams(searchParams)
        nextParams.delete('campaign_id')
        nextParams.delete('campaign_name')
        setSearchParams(nextParams)
        setPage(1)
    }

    function handleSort(field) {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
            return
        }
        setSortBy(field)
        setSortOrder('desc')
    }

    function handleExport(format) {
        const params = new URLSearchParams({
            client_id: String(selectedClientId),
            format,
            include_removed: includeRemoved ? 'true' : 'false',
        })
        if (campaignId) params.set('campaign_id', campaignId)
        window.location.href = `/api/v1/export/keywords?${params.toString()}`
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    const totalPages = Math.max(1, data.total_pages || 1)

    return (
        <div style={{ maxWidth: 1480 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Slowa kluczowe
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {data.total} slow kluczowych
                        {campaignName && (
                            <span style={{
                                marginLeft: 8,
                                padding: '2px 8px',
                                borderRadius: 999,
                                fontSize: 11,
                                background: 'rgba(79,142,247,0.12)',
                                border: '1px solid rgba(79,142,247,0.25)',
                                color: '#4F8EF7',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                            }}>
                                {decodeURIComponent(campaignName)}
                                <X size={10} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={clearCampaignFilter} />
                            </span>
                        )}
                    </p>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-1 flex-wrap">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(match => {
                            const active = matchFilter === match
                            const config = match ? MATCH_COLORS[match] : null
                            return (
                                <button
                                    key={match || 'ALL_MATCHES'}
                                    onClick={() => {
                                        setMatchFilter(match)
                                        setPage(1)
                                    }}
                                    style={{
                                        padding: '4px 11px',
                                        borderRadius: 999,
                                        fontSize: 11,
                                        fontWeight: active ? 500 : 400,
                                        border: `1px solid ${active ? (config?.color || '#4F8EF7') : 'rgba(255,255,255,0.1)'}`,
                                        background: active ? (config ? config.bg : 'rgba(79,142,247,0.18)') : 'transparent',
                                        color: active ? (config?.color || 'white') : 'rgba(255,255,255,0.4)',
                                        cursor: 'pointer',
                                    }}
                                >
                                    {match || 'Wszystkie'}
                                </button>
                            )
                        })}
                    </div>

                    <label
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 8,
                            padding: '5px 10px',
                            borderRadius: 999,
                            border: '1px solid rgba(255,255,255,0.1)',
                            background: includeRemoved ? 'rgba(248,113,113,0.08)' : 'rgba(255,255,255,0.03)',
                            color: includeRemoved ? '#FCA5A5' : 'rgba(255,255,255,0.55)',
                            fontSize: 11,
                            cursor: 'pointer',
                        }}
                    >
                        <input
                            type="checkbox"
                            checked={includeRemoved}
                            onChange={(event) => setIncludeRemoved(event.target.checked)}
                        />
                        Pokaz usuniete
                    </label>

                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => handleExport('csv')}
                            title="Eksportuj CSV"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 5,
                                padding: '5px 10px',
                                borderRadius: 7,
                                fontSize: 11,
                                background: 'rgba(255,255,255,0.04)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.5)',
                                cursor: 'pointer',
                            }}
                            className="hover:border-white/20 hover:text-white/70"
                        >
                            <Download size={12} /> CSV
                        </button>
                        <button
                            onClick={() => handleExport('xlsx')}
                            title="Eksportuj Excel"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 5,
                                padding: '5px 10px',
                                borderRadius: 7,
                                fontSize: 11,
                                background: 'rgba(74,222,128,0.06)',
                                border: '1px solid rgba(74,222,128,0.2)',
                                color: '#4ADE80',
                                cursor: 'pointer',
                            }}
                            className="hover:bg-green-500/10"
                        >
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
                                        <tr>
                                            <td colSpan={14} style={{ padding: '32px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>
                                                Brak slow kluczowych dla wybranych filtrow.
                                            </td>
                                        </tr>
                                    )}
                                    {data.items.map((keyword, index) => {
                                        const matchConfig = MATCH_COLORS[keyword.match_type]
                                        const hint = getKeywordHint(keyword)
                                        return (
                                            <tr
                                                key={keyword.id || index}
                                                style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                                onMouseEnter={(event) => { event.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
                                                onMouseLeave={(event) => { event.currentTarget.style.background = 'transparent' }}
                                            >
                                                <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 280 }}>
                                                    <KeywordCell keyword={keyword} />
                                                </td>
                                                <td style={{ padding: '10px 12px', maxWidth: 260 }}>
                                                    <CampaignCell keyword={keyword} />
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    {matchConfig ? (
                                                        <span style={{
                                                            fontSize: 10,
                                                            fontWeight: 600,
                                                            padding: '2px 7px',
                                                            borderRadius: 999,
                                                            background: matchConfig.bg,
                                                            color: matchConfig.color,
                                                            border: `1px solid ${matchConfig.border}`,
                                                        }}>
                                                            {keyword.match_type}
                                                        </span>
                                                    ) : (
                                                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{keyword.match_type || '-'}</span>
                                                    )}
                                                </td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.clicks?.toLocaleString() ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.impressions?.toLocaleString() ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.cost != null ? `${keyword.cost.toFixed(2)} zl` : '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.conversions?.toFixed(1) ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.ctr != null ? `${keyword.ctr.toFixed(2)}%` : '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.avg_cpc != null ? `${keyword.avg_cpc.toFixed(2)} zl` : '-'}</td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <QSBadge score={keyword.quality_score} />
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <StatusBadge status={keyword.status} />
                                                </td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>
                                                    {keyword.roas != null ? keyword.roas.toFixed(2) : '-'}
                                                </td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>
                                                    {keyword.search_impression_share != null ? `${(keyword.search_impression_share * 100).toFixed(1)}%` : '-'}
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    {hint ? (
                                                        <KeywordAction
                                                            icon={hint.icon}
                                                            label={hint.label}
                                                            color={hint.color}
                                                            bg={hint.bg}
                                                            border={hint.border}
                                                            title={hint.title}
                                                            onClick={() => showToast(`\"${keyword.text}\" -> przejdz do Rekomendacje`, 'info')}
                                                        />
                                                    ) : null}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>

                        <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                Strona {data.page || page} z {totalPages}
                            </span>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                                    disabled={page <= 1}
                                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page <= 1 ? 0.3 : 1 }}
                                >
                                    <ChevronLeft size={14} />
                                </button>
                                <button
                                    onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
                                    disabled={page >= totalPages}
                                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page >= totalPages ? 0.3 : 1 }}
                                >
                                    <ChevronRight size={14} />
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
