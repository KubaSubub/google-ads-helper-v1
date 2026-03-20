import { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, List, Loader2, Minus, PauseCircle, Plus, Shield, Trash2, TrendingDown, TrendingUp, X } from 'lucide-react'

import EmptyState from '../components/EmptyState'
import { MetricTooltip } from '../components/MetricTooltip'
import { ErrorMessage, StatusBadge, TH_STYLE, MODAL_OVERLAY, MODAL_BOX } from '../components/UI'
import {
    getKeywords,
    getNegativeKeywords, addNegativeKeyword, removeNegativeKeyword,
    getNegativeKeywordLists, createNegativeKeywordList, getNegativeKeywordListDetail,
    deleteNegativeKeywordList, addToNegativeKeywordList, removeFromNegativeKeywordList,
    applyNegativeKeywordList,
    getCampaigns, getAdGroups,
} from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'

const MATCH_COLORS = {
    EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
    PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
    BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
}

const SCOPE_LABELS = { CAMPAIGN: 'Kampania', AD_GROUP: 'Grupa reklam' }
const SOURCE_LABELS = { LOCAL_ACTION: 'Reczne', GOOGLE_ADS_SYNC: 'Google Ads' }

const SERVING_STATUS_CONFIG = {
    LOW_SEARCH_VOLUME: { label: 'Malo zapytan', color: '#FBBF24' },
    BELOW_FIRST_PAGE_BID: { label: 'Bid za niski', color: '#F87171' },
    RARELY_SERVED: { label: 'Rzadko', color: '#FBBF24' },
}


const PILL_STYLE = (active, color) => ({
    padding: '4px 11px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: active ? 500 : 400,
    border: `1px solid ${active ? (color || '#4F8EF7') : 'rgba(255,255,255,0.1)'}`,
    background: active ? `${color || '#4F8EF7'}18` : 'transparent',
    color: active ? (color || 'white') : 'rgba(255,255,255,0.4)',
    cursor: 'pointer',
})

const TAB_STYLE = (active) => ({
    padding: '7px 16px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: active ? 600 : 400,
    border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
    background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
    color: active ? '#4F8EF7' : 'rgba(255,255,255,0.45)',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
})

const INPUT_STYLE = {
    width: '100%', padding: '8px 12px', borderRadius: 8, fontSize: 13,
    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
    color: '#F0F0F0', outline: 'none',
}
const SELECT_STYLE = { ...INPUT_STYLE, cursor: 'pointer' }
const BTN_PRIMARY = {
    padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 600,
    background: '#4F8EF7', border: 'none', color: 'white', cursor: 'pointer',
}
const BTN_SECONDARY = {
    padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 500,
    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.6)', cursor: 'pointer',
}
const BTN_DANGER = {
    ...BTN_PRIMARY, background: 'rgba(248,113,113,0.15)', color: '#F87171',
    border: '1px solid rgba(248,113,113,0.3)',
}

/* ========================================================================
   Helper components
   ======================================================================== */

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

/* ========================================================================
   TAB: Positive keywords
   ======================================================================== */

function PositiveKeywordsTab({ selectedClientId, showToast, filters, searchParams, setSearchParams }) {
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
            setPage(1)
            // loadData will fire on the next render when page is 1
            return
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
                    {data.total} slow kluczowych
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
                        Pokaz usuniete
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
                                        <tr><td colSpan={14} style={{ padding: '32px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>Brak slow kluczowych dla wybranych filtrow.</td></tr>
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
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{keyword.clicks?.toLocaleString() ?? '-'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{keyword.impressions?.toLocaleString() ?? '-'}</td>
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

/* ========================================================================
   TAB: Negative keywords (Wykluczenia)
   ======================================================================== */

function NegativeKeywordsTab({ selectedClientId, showToast }) {
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [scopeFilter, setScopeFilter] = useState('')
    const [matchFilter, setMatchFilter] = useState('')
    const [search, setSearch] = useState('')
    const [includeRemoved, setIncludeRemoved] = useState(false)
    const [showAddModal, setShowAddModal] = useState(false)

    const loadData = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const params = { client_id: selectedClientId, page, page_size: 50, include_removed: includeRemoved }
            if (scopeFilter) params.negative_scope = scopeFilter
            if (matchFilter) params.match_type = matchFilter
            if (search) params.search = search
            const res = await getNegativeKeywords(params)
            setData(res)
        } catch { /* ignore */ } finally { setLoading(false) }
    }, [selectedClientId, page, scopeFilter, matchFilter, search, includeRemoved])

    useEffect(() => { loadData() }, [loadData])
    useEffect(() => { setPage(1) }, [scopeFilter, matchFilter, search, includeRemoved, selectedClientId])

    async function handleDelete(id) {
        try {
            await removeNegativeKeyword(id)
            showToast('Wykluczenie usuniete', 'success')
            loadData()
        } catch { showToast('Blad usuwania', 'error') }
    }

    const totalPages = Math.max(1, data.total_pages || 1)

    return (
        <>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{data.total} wykluczonych hasel</p>
                <div className="flex items-center gap-3 flex-wrap">
                    {/* Scope pills */}
                    <div className="flex items-center gap-1">
                        {[['', 'Wszystkie'], ['CAMPAIGN', 'Kampania'], ['AD_GROUP', 'Grupa reklam']].map(([val, label]) => (
                            <button key={val} onClick={() => setScopeFilter(val)} style={PILL_STYLE(scopeFilter === val, '#7B5CE0')}>{label}</button>
                        ))}
                    </div>
                    {/* Match pills */}
                    <div className="flex items-center gap-1">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(m => (
                            <button key={m || 'ALL'} onClick={() => setMatchFilter(m)}
                                style={PILL_STYLE(matchFilter === m, m ? MATCH_COLORS[m]?.color : null)}>
                                {m || 'Wszystkie'}
                            </button>
                        ))}
                    </div>
                    <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Szukaj..."
                        style={{ ...INPUT_STYLE, width: 160, padding: '5px 10px', fontSize: 11 }} />
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 10px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.1)', background: includeRemoved ? 'rgba(248,113,113,0.08)' : 'rgba(255,255,255,0.03)', color: includeRemoved ? '#FCA5A5' : 'rgba(255,255,255,0.55)', fontSize: 11, cursor: 'pointer' }}>
                        <input type="checkbox" checked={includeRemoved} onChange={e => setIncludeRemoved(e.target.checked)} /> Usuniete
                    </label>
                    <button onClick={() => setShowAddModal(true)} style={{ ...BTN_PRIMARY, display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '6px 14px' }}>
                        <Plus size={12} /> Dodaj wykluczenie
                    </button>
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
                                        <th style={TH_STYLE}>Fraza</th>
                                        <th style={TH_STYLE}>Dopasowanie</th>
                                        <th style={TH_STYLE}>Zakres</th>
                                        <th style={TH_STYLE}>Kampania</th>
                                        <th style={TH_STYLE}>Grupa reklam</th>
                                        <th style={TH_STYLE}>Status</th>
                                        <th style={TH_STYLE}>Zrodlo</th>
                                        <th style={TH_STYLE}>Dodano</th>
                                        <th style={TH_STYLE}>Akcje</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.items.length === 0 && (
                                        <tr><td colSpan={9} style={{ padding: '32px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>Brak wykluczonych hasel.</td></tr>
                                    )}
                                    {data.items.map((neg, i) => (
                                        <tr key={neg.id || i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
                                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}>
                                            <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0' }}>{neg.text}</td>
                                            <td style={{ padding: '10px 12px' }}><MatchBadge matchType={neg.match_type} /></td>
                                            <td style={{ padding: '10px 12px' }}>
                                                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: neg.negative_scope === 'AD_GROUP' ? 'rgba(123,92,224,0.1)' : 'rgba(79,142,247,0.1)', color: neg.negative_scope === 'AD_GROUP' ? '#7B5CE0' : '#4F8EF7', border: `1px solid ${neg.negative_scope === 'AD_GROUP' ? 'rgba(123,92,224,0.25)' : 'rgba(79,142,247,0.25)'}` }}>
                                                    {SCOPE_LABELS[neg.negative_scope] || neg.negative_scope}
                                                </span>
                                            </td>
                                            <td style={{ padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{neg.campaign_name || '-'}</td>
                                            <td style={{ padding: '10px 12px', fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>{neg.ad_group_name || '-'}</td>
                                            <td style={{ padding: '10px 12px' }}><StatusBadge status={neg.status} /></td>
                                            <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>{SOURCE_LABELS[neg.source] || neg.source}</td>
                                            <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{neg.created_at ? new Date(neg.created_at).toLocaleDateString('pl') : '-'}</td>
                                            <td style={{ padding: '10px 12px' }}>
                                                {neg.status !== 'REMOVED' && (
                                                    <button onClick={() => handleDelete(neg.id)} title="Usun" style={{ padding: '3px 6px', borderRadius: 6, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <Pagination page={page} totalPages={totalPages} setPage={setPage} />
                    </>
                )}
            </div>

            {showAddModal && <AddNegativeModal clientId={selectedClientId} onClose={() => setShowAddModal(false)} onDone={() => { setShowAddModal(false); loadData() }} showToast={showToast} />}
        </>
    )
}

/* Add negative keyword modal */
function AddNegativeModal({ clientId, onClose, onDone, showToast }) {
    const [texts, setTexts] = useState('')
    const [matchType, setMatchType] = useState('PHRASE')
    const [scope, setScope] = useState('CAMPAIGN')
    const [campaignId, setCampaignId] = useState('')
    const [adGroupId, setAdGroupId] = useState('')
    const [campaigns, setCampaigns] = useState([])
    const [adGroups, setAdGroups] = useState([])
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        getCampaigns(clientId).then(r => {
            const items = r.items || r
            setCampaigns(items.filter(c => c.status !== 'REMOVED'))
        }).catch(() => {})
    }, [clientId])

    useEffect(() => {
        if (scope === 'AD_GROUP' && campaignId) {
            getAdGroups({ client_id: clientId, campaign_id: campaignId }).then(r => {
                setAdGroups(Array.isArray(r) ? r : r.data || [])
            }).catch(() => {})
        }
    }, [scope, campaignId, clientId])

    async function handleSubmit() {
        const lines = texts.split('\n').map(l => l.trim()).filter(Boolean)
        if (!lines.length) { showToast('Wpisz przynajmniej jedna fraze', 'error'); return }
        if (scope === 'CAMPAIGN' && !campaignId) { showToast('Wybierz kampanie', 'error'); return }
        if (scope === 'AD_GROUP' && !adGroupId) { showToast('Wybierz grupe reklam', 'error'); return }
        setSubmitting(true)
        try {
            const body = { client_id: clientId, texts: lines, match_type: matchType, negative_scope: scope }
            if (campaignId) body.campaign_id = Number(campaignId)
            if (scope === 'AD_GROUP' && adGroupId) body.ad_group_id = Number(adGroupId)
            await addNegativeKeyword(body)
            showToast(`Dodano ${lines.length} wykluczenie(-a)`, 'success')
            onDone()
        } catch { showToast('Blad dodawania', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Dodaj wykluczenia</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Frazy (po jednej na linie)</label>
                        <textarea value={texts} onChange={e => setTexts(e.target.value)} rows={5} style={{ ...INPUT_STYLE, resize: 'vertical' }} placeholder="darmowe&#10;za darmo&#10;DIY" />
                    </div>
                    <div className="flex gap-3">
                        <div style={{ flex: 1 }}>
                            <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Typ dopasowania</label>
                            <select value={matchType} onChange={e => setMatchType(e.target.value)} style={SELECT_STYLE}>
                                <option value="PHRASE">PHRASE</option>
                                <option value="EXACT">EXACT</option>
                                <option value="BROAD">BROAD</option>
                            </select>
                        </div>
                        <div style={{ flex: 1 }}>
                            <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Zakres</label>
                            <select value={scope} onChange={e => { setScope(e.target.value); setAdGroupId('') }} style={SELECT_STYLE}>
                                <option value="CAMPAIGN">Kampania</option>
                                <option value="AD_GROUP">Grupa reklam</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Kampania</label>
                        <select value={campaignId} onChange={e => { setCampaignId(e.target.value); setAdGroupId('') }} style={SELECT_STYLE}>
                            <option value="">-- wybierz --</option>
                            {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                    </div>
                    {scope === 'AD_GROUP' && (
                        <div>
                            <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Grupa reklam</label>
                            <select value={adGroupId} onChange={e => setAdGroupId(e.target.value)} style={SELECT_STYLE}>
                                <option value="">-- wybierz --</option>
                                {adGroups.map(ag => <option key={ag.id} value={ag.id}>{ag.name}</option>)}
                            </select>
                        </div>
                    )}
                    <div className="flex justify-end gap-2" style={{ marginTop: 8 }}>
                        <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                        <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                            {submitting ? 'Dodawanie...' : 'Dodaj'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* ========================================================================
   TAB: Negative keyword lists (Listy wykluczeń)
   ======================================================================== */

function NegativeKeywordListsTab({ selectedClientId, showToast }) {
    const [lists, setLists] = useState([])
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [expandedListId, setExpandedListId] = useState(null)
    const [expandedData, setExpandedData] = useState(null)
    const [showApplyModal, setShowApplyModal] = useState(null) // list id
    const [showAddItemsModal, setShowAddItemsModal] = useState(null) // list id

    const loadLists = useCallback(async () => {
        if (!selectedClientId) return
        setLoading(true)
        try {
            const res = await getNegativeKeywordLists({ client_id: selectedClientId })
            setLists(Array.isArray(res) ? res : res.data || [])
        } catch { /* ignore */ } finally { setLoading(false) }
    }, [selectedClientId])

    useEffect(() => { loadLists() }, [loadLists])

    async function handleExpand(listId) {
        if (expandedListId === listId) { setExpandedListId(null); setExpandedData(null); return }
        setExpandedListId(listId)
        try {
            const res = await getNegativeKeywordListDetail(listId)
            setExpandedData(res)
        } catch { showToast('Blad ladowania listy', 'error') }
    }

    async function handleDeleteList(listId) {
        try {
            await deleteNegativeKeywordList(listId)
            showToast('Lista usunieta', 'success')
            if (expandedListId === listId) { setExpandedListId(null); setExpandedData(null) }
            loadLists()
        } catch { showToast('Blad usuwania', 'error') }
    }

    async function handleDeleteItem(listId, itemId) {
        try {
            await removeFromNegativeKeywordList(listId, itemId)
            showToast('Slowo usuniete z listy', 'success')
            const res = await getNegativeKeywordListDetail(listId)
            setExpandedData(res)
            loadLists()
        } catch { showToast('Blad usuwania', 'error') }
    }

    return (
        <>
            <div className="flex items-center justify-between flex-wrap gap-3" style={{ marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{lists.length} list wykluczajacych</p>
                <button onClick={() => setShowCreateModal(true)} style={{ ...BTN_PRIMARY, display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '6px 14px' }}>
                    <Plus size={12} /> Nowa lista
                </button>
            </div>

            {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
                    <Loader2 size={24} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            ) : lists.length === 0 ? (
                <div className="v2-card" style={{ padding: 32, textAlign: 'center', color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>
                    Brak list. Utworz pierwsza liste klikajac "Nowa lista".
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {lists.map(list => {
                        const isExpanded = expandedListId === list.id
                        return (
                            <div key={list.id} className="v2-card" style={{ overflow: 'hidden' }}>
                                <div className="flex items-center justify-between" style={{ padding: '14px 16px', cursor: 'pointer' }} onClick={() => handleExpand(list.id)}>
                                    <div className="flex items-center gap-3">
                                        <List size={16} style={{ color: '#7B5CE0' }} />
                                        <div>
                                            <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>{list.name}</div>
                                            {list.description && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{list.description}</div>}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.04)', padding: '3px 10px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.08)' }}>
                                            {list.item_count} slow
                                        </span>
                                        <button onClick={e => { e.stopPropagation(); setShowAddItemsModal(list.id) }} title="Dodaj slowa" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.2)', color: '#4F8EF7', cursor: 'pointer' }}>
                                            <Plus size={12} />
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); setShowApplyModal(list.id) }} title="Zastosuj" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ADE80', cursor: 'pointer' }}>
                                            <Shield size={12} />
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); handleDeleteList(list.id) }} title="Usun liste" style={{ padding: '4px 8px', borderRadius: 6, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                </div>

                                {isExpanded && expandedData && (
                                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '0' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                                    <th style={TH_STYLE}>Fraza</th>
                                                    <th style={TH_STYLE}>Dopasowanie</th>
                                                    <th style={TH_STYLE}>Dodano</th>
                                                    <th style={{ ...TH_STYLE, width: 50 }}></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(expandedData.items || []).length === 0 && (
                                                    <tr><td colSpan={4} style={{ padding: '20px 12px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Lista pusta.</td></tr>
                                                )}
                                                {(expandedData.items || []).map(item => (
                                                    <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                        <td style={{ padding: '8px 12px', fontSize: 13, color: '#F0F0F0' }}>{item.text}</td>
                                                        <td style={{ padding: '8px 12px' }}><MatchBadge matchType={item.match_type} /></td>
                                                        <td style={{ padding: '8px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{item.created_at ? new Date(item.created_at).toLocaleDateString('pl') : '-'}</td>
                                                        <td style={{ padding: '8px 12px' }}>
                                                            <button onClick={() => handleDeleteItem(list.id, item.id)} style={{ padding: '2px 5px', borderRadius: 5, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}>
                                                                <Minus size={10} />
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}

            {showCreateModal && <CreateListModal clientId={selectedClientId} onClose={() => setShowCreateModal(false)} onDone={() => { setShowCreateModal(false); loadLists() }} showToast={showToast} />}
            {showAddItemsModal && <AddItemsModal listId={showAddItemsModal} onClose={() => setShowAddItemsModal(null)} onDone={async () => { setShowAddItemsModal(null); loadLists(); if (expandedListId) { const res = await getNegativeKeywordListDetail(expandedListId); setExpandedData(res) } }} showToast={showToast} />}
            {showApplyModal && <ApplyListModal listId={showApplyModal} clientId={selectedClientId} onClose={() => setShowApplyModal(null)} onDone={() => { setShowApplyModal(null) }} showToast={showToast} />}
        </>
    )
}

/* Create list modal */
function CreateListModal({ clientId, onClose, onDone, showToast }) {
    const [name, setName] = useState('')
    const [description, setDescription] = useState('')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit() {
        if (!name.trim()) { showToast('Podaj nazwe listy', 'error'); return }
        setSubmitting(true)
        try {
            await createNegativeKeywordList({ client_id: clientId, name: name.trim(), description: description.trim() || null })
            showToast('Lista utworzona', 'success')
            onDone()
        } catch { showToast('Blad tworzenia listy', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Nowa lista wykluczajaca</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Nazwa</label>
                        <input value={name} onChange={e => setName(e.target.value)} style={INPUT_STYLE} placeholder="np. Ogolne wykluczenia" />
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Opis (opcjonalny)</label>
                        <input value={description} onChange={e => setDescription(e.target.value)} style={INPUT_STYLE} placeholder="Opis listy..." />
                    </div>
                    <div className="flex justify-end gap-2" style={{ marginTop: 8 }}>
                        <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                        <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                            {submitting ? 'Tworzenie...' : 'Utworz'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* Add items to list modal */
function AddItemsModal({ listId, onClose, onDone, showToast }) {
    const [texts, setTexts] = useState('')
    const [matchType, setMatchType] = useState('PHRASE')
    const [submitting, setSubmitting] = useState(false)

    async function handleSubmit() {
        const lines = texts.split('\n').map(l => l.trim()).filter(Boolean)
        if (!lines.length) { showToast('Wpisz przynajmniej jedno slowo', 'error'); return }
        setSubmitting(true)
        try {
            await addToNegativeKeywordList(listId, { texts: lines, match_type: matchType })
            showToast(`Dodano ${lines.length} slow`, 'success')
            onDone()
        } catch { showToast('Blad dodawania', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Dodaj slowa do listy</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Slowa (po jednym na linie)</label>
                        <textarea value={texts} onChange={e => setTexts(e.target.value)} rows={6} style={{ ...INPUT_STYLE, resize: 'vertical' }} placeholder="darmowe&#10;za darmo&#10;tanie" />
                    </div>
                    <div>
                        <label style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 4, display: 'block' }}>Typ dopasowania</label>
                        <select value={matchType} onChange={e => setMatchType(e.target.value)} style={SELECT_STYLE}>
                            <option value="PHRASE">PHRASE</option>
                            <option value="EXACT">EXACT</option>
                            <option value="BROAD">BROAD</option>
                        </select>
                    </div>
                    <div className="flex justify-end gap-2" style={{ marginTop: 8 }}>
                        <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                        <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                            {submitting ? 'Dodawanie...' : 'Dodaj'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/* Apply list to campaigns/ad groups modal */
function ApplyListModal({ listId, clientId, onClose, onDone, showToast }) {
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaigns, setSelectedCampaigns] = useState([])
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        getCampaigns(clientId).then(r => {
            const items = r.items || r
            setCampaigns(items.filter(c => c.status !== 'REMOVED'))
        }).catch(() => {})
    }, [clientId])

    function toggleCampaign(id) {
        setSelectedCampaigns(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
    }

    async function handleSubmit() {
        if (!selectedCampaigns.length) { showToast('Wybierz przynajmniej jedna kampanie', 'error'); return }
        setSubmitting(true)
        try {
            const res = await applyNegativeKeywordList(listId, { campaign_ids: selectedCampaigns })
            const data = res.data || res
            showToast(`Zastosowano: ${data.created} nowych, ${data.skipped} pominieto (duplikaty)`, 'success')
            onDone()
        } catch { showToast('Blad stosowania listy', 'error') } finally { setSubmitting(false) }
    }

    return (
        <div style={MODAL_OVERLAY} onClick={onClose}>
            <div style={MODAL_BOX} onClick={e => e.stopPropagation()}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 16 }}>Zastosuj liste do kampanii</h3>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 12 }}>Wybierz kampanie, do ktorych chcesz dodac wykluczenia z tej listy:</p>
                <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 16 }}>
                    {campaigns.map(c => (
                        <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', borderRadius: 8, background: selectedCampaigns.includes(c.id) ? 'rgba(79,142,247,0.1)' : 'transparent', border: `1px solid ${selectedCampaigns.includes(c.id) ? 'rgba(79,142,247,0.3)' : 'rgba(255,255,255,0.06)'}`, cursor: 'pointer', fontSize: 12, color: '#F0F0F0' }}>
                            <input type="checkbox" checked={selectedCampaigns.includes(c.id)} onChange={() => toggleCampaign(c.id)} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                            <span style={{ marginLeft: 'auto', fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{c.campaign_type}</span>
                        </label>
                    ))}
                </div>
                <div className="flex justify-end gap-2">
                    <button onClick={onClose} style={BTN_SECONDARY}>Anuluj</button>
                    <button onClick={handleSubmit} disabled={submitting} style={{ ...BTN_PRIMARY, opacity: submitting ? 0.5 : 1 }}>
                        {submitting ? 'Stosowanie...' : `Zastosuj do ${selectedCampaigns.length} kampanii`}
                    </button>
                </div>
            </div>
        </div>
    )
}

/* ========================================================================
   Main component with tabs
   ======================================================================== */

export default function Keywords() {
    const { selectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [searchParams, setSearchParams] = useSearchParams()
    const [activeTab, setActiveTab] = useState('positive')

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    return (
        <div style={{ maxWidth: 1480 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                    Slowa kluczowe
                </h1>
                <div className="flex items-center gap-2">
                    <button onClick={() => setActiveTab('positive')} style={TAB_STYLE(activeTab === 'positive')}>
                        Slowa kluczowe
                    </button>
                    <button onClick={() => setActiveTab('negative')} style={TAB_STYLE(activeTab === 'negative')}>
                        <Shield size={13} /> Wykluczenia
                    </button>
                    <button onClick={() => setActiveTab('lists')} style={TAB_STYLE(activeTab === 'lists')}>
                        <List size={13} /> Listy
                    </button>
                </div>
            </div>

            {activeTab === 'positive' && <PositiveKeywordsTab selectedClientId={selectedClientId} showToast={showToast} filters={filters} searchParams={searchParams} setSearchParams={setSearchParams} />}
            {activeTab === 'negative' && <NegativeKeywordsTab selectedClientId={selectedClientId} showToast={showToast} />}
            {activeTab === 'lists' && <NegativeKeywordListsTab selectedClientId={selectedClientId} showToast={showToast} />}
        </div>
    )
}
