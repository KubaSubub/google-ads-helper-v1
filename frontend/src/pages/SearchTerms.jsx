import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../components/UI'
import { getSearchTerms, getSegmentedSearchTerms } from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import EmptyState from '../components/EmptyState'
import {
    Search, ArrowUpDown, ChevronLeft, ChevronRight, Download,
    TrendingUp, AlertTriangle, XCircle, LayoutGrid,
    List, Loader2, X, PlusCircle, MinusCircle,
} from 'lucide-react'
import FilterBar from '../components/FilterBar'
import { MetricTooltip } from '../components/MetricTooltip'

const SEGMENT_CONFIG = {
    HIGH_PERFORMER: { label: 'Top Performerzy', icon: TrendingUp,    color: '#4ADE80', bg: 'rgba(74,222,128,0.1)',   border: 'rgba(74,222,128,0.2)'  },
    WASTE:          { label: 'Waste',            icon: AlertTriangle, color: '#F87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.2)' },
    IRRELEVANT:     { label: 'Nieistotne',       icon: XCircle,       color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)' },
    OTHER:          { label: 'Inne',             icon: LayoutGrid,    color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)',  border: 'rgba(79,142,247,0.2)'  },
}

const TH_STYLE = {
    padding: '10px 12px',
    fontSize: 10, fontWeight: 500,
    color: 'rgba(255,255,255,0.35)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    whiteSpace: 'nowrap',
    textAlign: 'left',
}

function SegmentBadge({ seg }) {
    const conf = SEGMENT_CONFIG[seg] || SEGMENT_CONFIG.OTHER
    const Icon = conf.icon
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
            background: conf.bg, color: conf.color, border: `1px solid ${conf.border}`,
        }}>
            <Icon size={9} />{conf.label}
        </span>
    )
}

function InlineAction({ icon: Icon, label, color, bg, border, onClick }) {
    return (
        <button
            onClick={onClick}
            style={{
                display: 'inline-flex', alignItems: 'center', gap: 3,
                fontSize: 10, fontWeight: 500, padding: '3px 8px', borderRadius: 6,
                background: bg, color, border: `1px solid ${border}`,
                cursor: 'pointer', whiteSpace: 'nowrap',
            }}
        >
            <Icon size={10} />{label}
        </button>
    )
}

export default function SearchTerms() {
    const { selectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [searchParams, setSearchParams] = useSearchParams()
    const campaignId = searchParams.get('campaign_id')
    const campaignName = searchParams.get('campaign_name')
    const [viewMode, setViewMode] = useState(campaignId ? 'list' : 'segments')
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [segData, setSegData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [search, setSearch] = useState('')
    const [sortBy, setSortBy] = useState('cost')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [activeSegment, setActiveSegment] = useState('ALL')

    useEffect(() => {
        if (!selectedClientId) return
        if (viewMode === 'list') loadListData()
        else loadSegmentedData()
    }, [viewMode, page, search, sortBy, sortOrder, selectedClientId, campaignId, filters.dateFrom, filters.dateTo, filters.campaignType, filters.status])

    async function loadListData() {
        setLoading(true); setError(null)
        try {
            const params = { page, page_size: 50, search, sort_by: sortBy, sort_order: sortOrder, client_id: selectedClientId }
            if (campaignId) params.campaign_id = campaignId
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            if (filters.campaignType !== 'ALL') params.campaign_type = filters.campaignType
            if (filters.status !== 'ALL') params.campaign_status = filters.status
            const res = await getSearchTerms(params)
            setData(res)
        } catch (err) { setError(err.message) }
        finally { setLoading(false) }
    }

    function clearCampaignFilter() {
        searchParams.delete('campaign_id')
        searchParams.delete('campaign_name')
        setSearchParams(searchParams)
        setPage(1)
    }

    async function loadSegmentedData() {
        setLoading(true); setError(null)
        try {
            const params = {}
            if (filters.dateFrom) params.date_from = filters.dateFrom
            if (filters.dateTo) params.date_to = filters.dateTo
            if (filters.campaignType !== 'ALL') params.campaign_type = filters.campaignType
            if (filters.status !== 'ALL') params.campaign_status = filters.status
            const res = await getSegmentedSearchTerms(selectedClientId, params)
            setSegData(res)
        } catch (err) { setError(err.message) }
        finally { setLoading(false) }
    }

    function handleSort(field) {
        if (sortBy === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        else { setSortBy(field); setSortOrder('desc') }
    }

    function handleSearch(e) {
        e.preventDefault(); setPage(1)
        if (viewMode === 'list') loadListData()
    }

    function handleExport(format) {
        const params = new URLSearchParams({ client_id: selectedClientId, format })
        window.location.href = `/api/v1/export/search-terms?${params.toString()}`
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={() => viewMode === 'list' ? loadListData() : loadSegmentedData()} />

    const segmentItems = segData && activeSegment !== 'ALL'
        ? segData.segments?.[activeSegment] || []
        : segData ? Object.values(segData.segments || {}).flat() : []

    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Wyszukiwane frazy
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {viewMode === 'segments' ? `${segData?.summary?.total || 0} wyszukiwań` : `${data.total} wyszukiwań`}
                        {campaignName && (
                            <span style={{
                                marginLeft: 8, padding: '2px 8px', borderRadius: 999, fontSize: 11,
                                background: 'rgba(123,92,224,0.12)', border: '1px solid rgba(123,92,224,0.25)',
                                color: '#7B5CE0', display: 'inline-flex', alignItems: 'center', gap: 4,
                            }}>
                                {decodeURIComponent(campaignName)}
                                <X size={10} style={{ cursor: 'pointer', opacity: 0.7 }} onClick={clearCampaignFilter} />
                            </span>
                        )}
                    </p>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                    <FilterBar hidePeriod />
                    {/* View mode toggle */}
                    <div className="flex items-center gap-1">
                        {[{ v: 'segments', label: 'Segmenty', icon: LayoutGrid }, { v: 'list', label: 'Lista', icon: List }].map(({ v, label, icon: Icon }) => {
                            const active = viewMode === v
                            return (
                                <button key={v} onClick={() => setViewMode(v)} style={{
                                    display: 'flex', alignItems: 'center', gap: 5,
                                    padding: '5px 12px', borderRadius: 7, fontSize: 12, fontWeight: active ? 500 : 400,
                                    border: `1px solid ${active ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                                    background: active ? 'rgba(79,142,247,0.18)' : 'transparent',
                                    color: active ? 'white' : 'rgba(255,255,255,0.45)', cursor: 'pointer',
                                }}>
                                    <Icon size={12} />{label}
                                </button>
                            )
                        })}
                    </div>

                    {viewMode === 'list' && (
                        <form onSubmit={handleSearch} className="flex items-center gap-2">
                            <div style={{ position: 'relative' }}>
                                <Search size={12} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.3)' }} />
                                <input
                                    type="text" value={search}
                                    onChange={e => setSearch(e.target.value)}
                                    placeholder="Szukaj frazy..."
                                    style={{
                                        paddingLeft: 30, paddingRight: 12, paddingTop: 6, paddingBottom: 6,
                                        borderRadius: 7, background: 'rgba(255,255,255,0.04)',
                                        border: '1px solid rgba(255,255,255,0.1)', color: '#F0F0F0',
                                        fontSize: 12, width: 200, outline: 'none',
                                    }}
                                />
                            </div>
                            <button type="submit" style={{
                                padding: '6px 12px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                                background: '#4F8EF7', color: 'white', border: 'none', cursor: 'pointer',
                            }}>Szukaj</button>
                        </form>
                    )}

                    {/* Export */}
                    <div className="flex items-center gap-1">
                        <button onClick={() => handleExport('csv')} title="CSV" style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Download size={11} />CSV
                        </button>
                        <button onClick={() => handleExport('xlsx')} title="Excel" style={{ padding: '5px 10px', borderRadius: 7, fontSize: 11, background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ADE80', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Download size={11} />XLSX
                        </button>
                    </div>
                </div>
            </div>

            {/* ===== SEGMENTS VIEW ===== */}
            {viewMode === 'segments' && (
                <>
                    {/* Summary cards */}
                    {segData?.summary && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 16 }}>
                            {Object.entries(SEGMENT_CONFIG).map(([key, conf]) => {
                                const count = segData.summary.counts?.[key] || 0
                                const active = activeSegment === key
                                const Icon = conf.icon
                                return (
                                    <button
                                        key={key}
                                        onClick={() => setActiveSegment(active ? 'ALL' : key)}
                                        style={{
                                            padding: '12px 14px', borderRadius: 10, textAlign: 'left', cursor: 'pointer',
                                            background: conf.bg, border: `1px solid ${active ? conf.color : conf.border}`,
                                            outline: active ? `2px solid ${conf.color}40` : 'none',
                                            transition: 'all 0.15s',
                                        }}
                                    >
                                        <div className="flex items-center gap-2" style={{ marginBottom: 4 }}>
                                            <Icon size={12} style={{ color: conf.color }} />
                                            <span style={{ fontSize: 11, fontWeight: 500, color: conf.color }}>{conf.label}</span>
                                        </div>
                                        <span style={{ fontSize: 22, fontWeight: 700, color: conf.color, fontFamily: 'Syne' }}>{count}</span>
                                    </button>
                                )
                            })}
                        </div>
                    )}

                    {/* Waste callout */}
                    {segData?.summary?.waste_cost > 0 && (
                        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 10, padding: '12px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                            <AlertTriangle size={15} style={{ color: '#F87171', flexShrink: 0 }} />
                            <div>
                                <span style={{ fontSize: 12, fontWeight: 600, color: '#F87171' }}>
                                    Zmarnowany budżet: {segData.summary.waste_cost.toFixed(2)} zł
                                </span>
                                <span style={{ fontSize: 11, color: 'rgba(248,113,113,0.6)', marginLeft: 8 }}>
                                    Rozważ dodanie fraz WASTE jako wykluczenia.
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Table */}
                    <div className="v2-card" style={{ overflow: 'hidden' }}>
                        {loading ? (
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
                                <Loader2 size={24} style={{ color: '#4F8EF7' }} className="animate-spin" />
                            </div>
                        ) : (
                            <div style={{ overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                            <th style={TH_STYLE}>Segment</th>
                                            <th style={TH_STYLE}>Fraza</th>
                                            <th style={TH_STYLE}>Kampania</th>
                                            <th style={TH_STYLE}>Kliknięcia</th>
                                            <th style={TH_STYLE}>Koszt</th>
                                            <th style={TH_STYLE}>Konwersje</th>
                                            <th style={TH_STYLE}><MetricTooltip term="CVR" inline>CVR</MetricTooltip></th>
                                            <th style={TH_STYLE}>Powód</th>
                                            <th style={TH_STYLE}>Akcje</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {segmentItems.length === 0 ? (
                                            <tr><td colSpan={9} style={{ padding: '32px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>Brak wyników</td></tr>
                                        ) : segmentItems.map((t, i) => {
                                            let seg = 'OTHER'
                                            for (const [key, items] of Object.entries(segData?.segments || {})) {
                                                if (items.some(item => item.id === t.id)) { seg = key; break }
                                            }
                                            const showAddKw = seg === 'HIGH_PERFORMER'
                                            const showAddNeg = seg === 'WASTE' || seg === 'IRRELEVANT'
                                            return (
                                                <tr key={t.id || i}
                                                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                                >
                                                    <td style={{ padding: '10px 12px' }}><SegmentBadge seg={seg} /></td>
                                                    <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 280 }}>
                                                        <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.text}</span>
                                                    </td>
                                                    <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)', maxWidth: 160 }}>
                                                        <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.campaign_name || '—'}</span>
                                                    </td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.clicks?.toLocaleString() ?? '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.cost != null ? `${t.cost.toFixed(2)} zł` : '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.conversions?.toFixed(1) ?? '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>{t.cvr != null ? `${t.cvr.toFixed(2)}%` : '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 11, color: 'rgba(255,255,255,0.4)', maxWidth: 200 }}>
                                                        <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.segment_reason || '—'}</span>
                                                    </td>
                                                    <td style={{ padding: '10px 12px' }}>
                                                        <div className="flex items-center gap-1">
                                                            {showAddKw && (
                                                                <InlineAction
                                                                    icon={PlusCircle} label="Dodaj słowo"
                                                                    color="#4ADE80" bg="rgba(74,222,128,0.08)" border="rgba(74,222,128,0.2)"
                                                                    onClick={() => showToast(`"${t.text}" → przejdź do Rekomendacje, aby zastosować`, 'info')}
                                                                />
                                                            )}
                                                            {showAddNeg && (
                                                                <InlineAction
                                                                    icon={MinusCircle} label="Wyklucz"
                                                                    color="#F87171" bg="rgba(248,113,113,0.08)" border="rgba(248,113,113,0.2)"
                                                                    onClick={() => showToast(`"${t.text}" → przejdź do Rekomendacje, aby wykluczyć`, 'info')}
                                                                />
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* ===== LIST VIEW ===== */}
            {viewMode === 'list' && (
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
                                            {[
                                                { f: 'text', label: 'Fraza' },
                                                { f: 'clicks', label: 'Kliknięcia' },
                                                { f: 'impressions', label: 'Wyświetlenia' },
                                                { f: 'cost', label: 'Koszt' },
                                                { f: 'conversions', label: 'Konwersje' },
                                                { f: 'ctr', label: 'CTR', metric: 'CTR' },
                                                { f: null, label: 'Koszt/konw.', metric: 'CPA' },
                                            ].map(({ f, label, metric }) => (
                                                <th key={label}
                                                    style={{ ...TH_STYLE, cursor: f ? 'pointer' : 'default' }}
                                                    onClick={() => f && handleSort(f)}
                                                >
                                                    <span className="flex items-center gap-1">
                                                        {metric ? <MetricTooltip term={metric} inline>{label}</MetricTooltip> : label}
                                                        {f && sortBy === f && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}
                                                    </span>
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.items.map((t, i) => {
                                            const isWaste = t.cost > 20 && t.conversions === 0
                                            return (
                                                <tr key={t.id || i}
                                                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: isWaste ? 'rgba(248,113,113,0.03)' : 'transparent', transition: 'background 0.12s' }}
                                                    onMouseEnter={e => e.currentTarget.style.background = isWaste ? 'rgba(248,113,113,0.06)' : 'rgba(255,255,255,0.025)'}
                                                    onMouseLeave={e => e.currentTarget.style.background = isWaste ? 'rgba(248,113,113,0.03)' : 'transparent'}
                                                >
                                                    <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 320 }}>
                                                        <span className="flex items-center gap-2">
                                                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.text}</span>
                                                            {isWaste && <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 999, background: 'rgba(248,113,113,0.15)', color: '#F87171', flexShrink: 0 }}>WASTE</span>}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.clicks?.toLocaleString()}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>{t.impressions?.toLocaleString()}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.cost?.toFixed(2)} zł</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.conversions?.toFixed(1)}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>{t.ctr?.toFixed(2)}%</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>
                                                        {t.conversions > 0 ? `${(t.cost / t.conversions).toFixed(2)} zł` : '—'}
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            {/* Pagination */}
                            <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>Strona {data.page} z {data.total_pages} ({data.total} wyników)</span>
                                <div className="flex items-center gap-1">
                                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page <= 1 ? 0.3 : 1 }}><ChevronLeft size={13} /></button>
                                    <button onClick={() => setPage(p => Math.min(data.total_pages, p + 1))} disabled={page >= data.total_pages} style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page >= data.total_pages ? 0.3 : 1 }}><ChevronRight size={13} /></button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    )
}
