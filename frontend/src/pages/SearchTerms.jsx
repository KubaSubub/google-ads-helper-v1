import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ErrorMessage, TH_STYLE } from '../components/UI'
import { getSearchTerms, getSegmentedSearchTerms, getSearchTermTrends, getCloseVariants } from '../api'
import api from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import EmptyState from '../components/EmptyState'
import {
    Search, ArrowUpDown, ChevronLeft, ChevronRight, Download,
    TrendingUp, TrendingDown, AlertTriangle, XCircle, LayoutGrid,
    List, Loader2, X, PlusCircle, MinusCircle, CheckSquare, Square,
    BarChart3, GitCompare,
} from 'lucide-react'
import { MetricTooltip } from '../components/MetricTooltip'

// ─── Bulk actions API ───
const bulkAddNegative = (data) => api.post('/search-terms/bulk-add-negative', data)
const bulkAddKeyword = (data) => api.post('/search-terms/bulk-add-keyword', data)

const SEGMENT_CONFIG = {
    HIGH_PERFORMER: { label: 'Top Performerzy', icon: TrendingUp,    color: '#4ADE80', bg: 'rgba(74,222,128,0.1)',   border: 'rgba(74,222,128,0.2)'  },
    WASTE:          { label: 'Strata',           icon: AlertTriangle, color: '#F87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.2)' },
    IRRELEVANT:     { label: 'Nieistotne',       icon: XCircle,       color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.1)' },
    OTHER:          { label: 'Inne',             icon: LayoutGrid,    color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)',  border: 'rgba(79,142,247,0.2)'  },
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

// ─── Bulk Action Bar ───
function BulkActionBar({ selectedCount, onAddNegative, onAddKeyword, onClear, loading: bulkLoading }) {
    if (selectedCount === 0) return null
    return (
        <div style={{
            position: 'sticky', top: 0, zIndex: 20,
            background: 'rgba(13,15,20,0.95)', backdropFilter: 'blur(12px)',
            border: '1px solid rgba(79,142,247,0.3)', borderRadius: 10,
            padding: '10px 16px', marginBottom: 12,
            display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#4F8EF7' }}>
                {selectedCount} zaznaczonych
            </span>
            <div style={{ flex: 1 }} />
            <button onClick={onAddNegative} disabled={bulkLoading} style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '5px 14px', borderRadius: 7, fontSize: 11, fontWeight: 500,
                background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)',
                color: '#F87171', cursor: 'pointer', opacity: bulkLoading ? 0.5 : 1,
            }}>
                {bulkLoading ? <Loader2 size={11} className="animate-spin" /> : <MinusCircle size={11} />}
                Dodaj jako negatywy (EXACT)
            </button>
            <button onClick={onAddKeyword} disabled={bulkLoading} style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '5px 14px', borderRadius: 7, fontSize: 11, fontWeight: 500,
                background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)',
                color: '#4ADE80', cursor: 'pointer', opacity: bulkLoading ? 0.5 : 1,
            }}>
                {bulkLoading ? <Loader2 size={11} className="animate-spin" /> : <PlusCircle size={11} />}
                Dodaj jako slowa kluczowe
            </button>
            <button onClick={onClear} style={{
                padding: '5px 10px', borderRadius: 7, fontSize: 11,
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
            }}>
                <X size={11} />
            </button>
        </div>
    )
}

export default function SearchTerms() {
    const { selectedClientId, showToast } = useApp()
    const { filters, allParams } = useFilter()
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
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [bulkLoading, setBulkLoading] = useState(false)
    const [trendsData, setTrendsData] = useState(null)
    const [variantsData, setVariantsData] = useState(null)
    const [trendsLoading, setTrendsLoading] = useState(false)
    const [variantsLoading, setVariantsLoading] = useState(false)

    const toggleSelect = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    const toggleSelectAll = (items) => {
        const ids = items.map(t => t.id).filter(Boolean)
        const allSelected = ids.every(id => selectedIds.has(id))
        if (allSelected) {
            setSelectedIds(prev => {
                const next = new Set(prev)
                ids.forEach(id => next.delete(id))
                return next
            })
        } else {
            setSelectedIds(prev => {
                const next = new Set(prev)
                ids.forEach(id => next.add(id))
                return next
            })
        }
    }

    const handleBulkAddNegative = async () => {
        if (selectedIds.size === 0) return
        setBulkLoading(true)
        try {
            const res = await bulkAddNegative({
                search_term_ids: [...selectedIds],
                level: 'campaign',
                match_type: 'EXACT',
                client_id: selectedClientId,
            })
            showToast(`Dodano ${res.added} negatywow, pominito ${res.skipped_duplicates} duplikatow`, 'success')
            setSelectedIds(new Set())
        } catch (err) { showToast(`Blad: ${err.message}`, 'error') }
        finally { setBulkLoading(false) }
    }

    const handleBulkAddKeyword = async () => {
        if (selectedIds.size === 0) return
        showToast('Wybierz grupe reklam w oknie dialogowym aby dodac slowa kluczowe', 'info')
    }

    useEffect(() => {
        if (!selectedClientId) return
        if (viewMode === 'list') loadListData()
        else if (viewMode === 'trends') loadTrendsData()
        else if (viewMode === 'variants') loadVariantsData()
        else loadSegmentedData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

    async function loadTrendsData() {
        setTrendsLoading(true); setError(null)
        try {
            const res = await getSearchTermTrends(selectedClientId, allParams)
            setTrendsData(res)
        } catch (err) { setError(err.message) }
        finally { setTrendsLoading(false) }
    }

    async function loadVariantsData() {
        setVariantsLoading(true); setError(null)
        try {
            const res = await getCloseVariants(selectedClientId, allParams)
            setVariantsData(res)
        } catch (err) { setError(err.message) }
        finally { setVariantsLoading(false) }
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

    // Pre-compute id → segment key map to avoid O(n²) lookup in render
    const segmentMap = useMemo(() => {
        const map = {}
        if (segData?.segments) {
            for (const [key, items] of Object.entries(segData.segments)) {
                for (const item of items) { if (item.id) map[item.id] = key }
            }
        }
        return map
    }, [segData])

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
                    {/* View mode toggle */}
                    <div className="flex items-center gap-1">
                        {[
                            { v: 'segments', label: 'Segmenty', icon: LayoutGrid },
                            { v: 'list', label: 'Lista', icon: List },
                            { v: 'trends', label: 'Trendy', icon: BarChart3 },
                            { v: 'variants', label: 'Warianty', icon: GitCompare },
                        ].map(({ v, label, icon: Icon }) => {
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

                    {/* Bulk action bar */}
                    <BulkActionBar
                        selectedCount={selectedIds.size}
                        onAddNegative={handleBulkAddNegative}
                        onAddKeyword={handleBulkAddKeyword}
                        onClear={() => setSelectedIds(new Set())}
                        loading={bulkLoading}
                    />

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
                                            <th style={{ ...TH_STYLE, width: 36, textAlign: 'center' }}>
                                                <button onClick={() => toggleSelectAll(segmentItems)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'rgba(255,255,255,0.3)' }}>
                                                    {segmentItems.length > 0 && segmentItems.every(t => selectedIds.has(t.id))
                                                        ? <CheckSquare size={13} style={{ color: '#4F8EF7' }} />
                                                        : <Square size={13} />}
                                                </button>
                                            </th>
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
                                            <tr><td colSpan={10} style={{ padding: '32px', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>Brak wyników</td></tr>
                                        ) : segmentItems.map((t, i) => {
                                            const seg = segmentMap[t.id] || 'OTHER'
                                            const showAddKw = seg === 'HIGH_PERFORMER'
                                            const showAddNeg = seg === 'WASTE' || seg === 'IRRELEVANT'
                                            const isSelected = selectedIds.has(t.id)
                                            return (
                                                <tr key={t.id || i}
                                                    style={{
                                                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                                                        transition: 'background 0.12s',
                                                        background: isSelected ? 'rgba(79,142,247,0.06)' : 'transparent',
                                                    }}
                                                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.025)' }}
                                                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent' }}
                                                >
                                                    <td style={{ padding: '10px 6px', textAlign: 'center', width: 36 }}>
                                                        <button onClick={() => toggleSelect(t.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'rgba(255,255,255,0.3)' }}>
                                                            {isSelected ? <CheckSquare size={13} style={{ color: '#4F8EF7' }} /> : <Square size={13} />}
                                                        </button>
                                                    </td>
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
                                            const isWaste = t.cost_usd > 20 && (t.conversions == null || t.conversions < 0.01)
                                            return (
                                                <tr key={t.id || i}
                                                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: isWaste ? 'rgba(248,113,113,0.03)' : 'transparent', transition: 'background 0.12s' }}
                                                    onMouseEnter={e => e.currentTarget.style.background = isWaste ? 'rgba(248,113,113,0.06)' : 'rgba(255,255,255,0.025)'}
                                                    onMouseLeave={e => e.currentTarget.style.background = isWaste ? 'rgba(248,113,113,0.03)' : 'transparent'}
                                                >
                                                    <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 320 }}>
                                                        <span className="flex items-center gap-2">
                                                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.text}</span>
                                                            {isWaste && <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 999, background: 'rgba(248,113,113,0.15)', color: '#F87171', flexShrink: 0 }}>STRATA</span>}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.clicks?.toLocaleString()}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>{t.impressions?.toLocaleString()}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.cost_usd != null ? `${t.cost_usd.toFixed(2)} zł` : '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)' }}>{t.conversions != null ? t.conversions.toFixed(1) : '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>{t.ctr != null ? `${t.ctr.toFixed(2)}%` : '—'}</td>
                                                    <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>
                                                        {t.cost_per_conversion_usd > 0 ? `${t.cost_per_conversion_usd.toFixed(2)} zł` : '—'}
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

            {/* ===== TRENDS VIEW ===== */}
            {viewMode === 'trends' && (
                <div>
                    {error && <ErrorMessage message={error} />}
                    {trendsLoading ? (
                        <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={20} className="animate-spin" style={{ color: '#4F8EF7' }} /></div>
                    ) : trendsData ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>
                                {trendsData.total_terms} unikalnych fraz w ostatnich {trendsData.period_days} dniach
                            </div>

                            {/* Rising */}
                            {trendsData.rising?.length > 0 && (
                                <div className="v2-card" style={{ padding: 16 }}>
                                    <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#4ADE80', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <TrendingUp size={16} /> Rosnące frazy ({trendsData.rising.length})
                                    </div>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                        <thead>
                                            <tr>
                                                {['Fraza', 'Kliknięcia (wcześniej)', 'Kliknięcia (ostatnio)', 'Zmiana', 'Koszt', 'Konw.'].map(h => (
                                                    <th key={h} style={{ ...TH_STYLE, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trendsData.rising.slice(0, 15).map((t, i) => (
                                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                    <td style={{ padding: '8px 12px', color: '#F0F0F0', fontWeight: 500 }}>{t.text}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{t.clicks_early}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F0F0F0' }}>{t.clicks_recent}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#4ADE80', fontWeight: 600 }}>+{t.change_pct}%</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{t.total_cost_usd} zł</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{t.conversions}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {/* Declining */}
                            {trendsData.declining?.length > 0 && (
                                <div className="v2-card" style={{ padding: 16 }}>
                                    <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#F87171', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <TrendingDown size={16} /> Spadające frazy ({trendsData.declining.length})
                                    </div>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                        <thead>
                                            <tr>
                                                {['Fraza', 'Kliknięcia (wcześniej)', 'Kliknięcia (ostatnio)', 'Zmiana', 'Koszt', 'Konw.'].map(h => (
                                                    <th key={h} style={{ ...TH_STYLE, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trendsData.declining.slice(0, 15).map((t, i) => (
                                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                    <td style={{ padding: '8px 12px', color: '#F0F0F0', fontWeight: 500 }}>{t.text}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{t.clicks_early}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F0F0F0' }}>{t.clicks_recent}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F87171', fontWeight: 600 }}>{t.change_pct}%</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{t.total_cost_usd} zł</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{t.conversions}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {/* New terms */}
                            {trendsData.new_terms?.length > 0 && (
                                <div className="v2-card" style={{ padding: 16 }}>
                                    <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#4F8EF7', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <PlusCircle size={16} /> Nowe frazy ({trendsData.new_terms.length})
                                    </div>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                        <thead>
                                            <tr>
                                                {['Fraza', 'Kliknięcia', 'Koszt', 'Konwersje'].map(h => (
                                                    <th key={h} style={{ ...TH_STYLE, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trendsData.new_terms.slice(0, 15).map((t, i) => (
                                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                    <td style={{ padding: '8px 12px', color: '#F0F0F0', fontWeight: 500 }}>{t.text}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F0F0F0' }}>{t.clicks}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{t.cost_usd} zł</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{t.conversions}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {!trendsData.rising?.length && !trendsData.declining?.length && !trendsData.new_terms?.length && (
                                <EmptyState message="Brak danych o trendach" />
                            )}
                        </div>
                    ) : <EmptyState message="Brak danych" />}
                </div>
            )}

            {/* ===== VARIANTS VIEW ===== */}
            {viewMode === 'variants' && (
                <div>
                    {error && <ErrorMessage message={error} />}
                    {variantsLoading ? (
                        <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={20} className="animate-spin" style={{ color: '#4F8EF7' }} /></div>
                    ) : variantsData ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            {/* Summary */}
                            {variantsData.summary && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
                                    {[
                                        { label: 'Wyszukiwania', value: variantsData.summary.total_search_terms },
                                        { label: 'Dokładne dopasowania', value: variantsData.summary.exact_matches },
                                        { label: 'Bliskie warianty', value: variantsData.summary.close_variants },
                                        { label: 'Koszt wariantów', value: `${variantsData.summary.variant_cost_usd} zł` },
                                    ].map(({ label, value }) => (
                                        <div key={label} className="v2-card" style={{ padding: '12px 14px' }}>
                                            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                                            <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0' }}>{value}</div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Variants table */}
                            {variantsData.variants?.length > 0 ? (
                                <div className="v2-card" style={{ padding: 16 }}>
                                    <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'Syne', color: '#fff', marginBottom: 12 }}>
                                        Bliskie warianty wg kosztu
                                    </div>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                        <thead>
                                            <tr>
                                                {['Wyszukiwana fraza', 'Dopasowane słowo', 'Typ', 'Kliknięcia', 'Koszt', 'Konw.', 'CTR'].map(h => (
                                                    <th key={h} style={{ ...TH_STYLE, textAlign: h === 'Wyszukiwana fraza' || h === 'Dopasowane słowo' ? 'left' : 'right' }}>{h}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {variantsData.variants.slice(0, 25).map((v, i) => (
                                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                                    <td style={{ padding: '8px 12px', color: '#F0F0F0', fontWeight: 500, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.search_term}</td>
                                                    <td style={{ padding: '8px 12px', color: 'rgba(255,255,255,0.6)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.matched_keyword}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                                        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: 'rgba(79,142,247,0.1)', color: '#4F8EF7', border: '1px solid rgba(79,142,247,0.2)' }}>{v.match_type}</span>
                                                    </td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#F0F0F0' }}>{v.clicks}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{v.cost_usd} zł</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.7)' }}>{v.conversions}</td>
                                                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>{v.ctr}%</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <EmptyState message="Brak bliskich wariantów" />}
                        </div>
                    ) : <EmptyState message="Brak danych" />}
                </div>
            )}
        </div>
    )
}
