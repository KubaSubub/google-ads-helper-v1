import { useState, useEffect } from 'react'
import { ErrorMessage } from '../components/UI'
import { getKeywords } from '../api'
import { useApp } from '../contexts/AppContext'
import EmptyState from '../components/EmptyState'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Loader2 } from 'lucide-react'

const MATCH_COLORS = {
    EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
    PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
    BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
}

function QSBadge({ score }) {
    if (score == null) return <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 11 }}>—</span>
    const color = score <= 3 ? '#F87171' : score <= 6 ? '#FBBF24' : '#4ADE80'
    const bg = score <= 3 ? 'rgba(248,113,113,0.1)' : score <= 6 ? 'rgba(251,191,36,0.1)' : 'rgba(74,222,128,0.1)'
    return (
        <span style={{
            fontSize: 11, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
            background: bg, color,
        }}>
            {score}/10
        </span>
    )
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

export default function Keywords() {
    const { selectedClientId } = useApp()
    const [data, setData] = useState({ items: [], total: 0, page: 1, total_pages: 0 })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [sortBy, setSortBy] = useState('cost')
    const [sortOrder, setSortOrder] = useState('desc')
    const [page, setPage] = useState(1)
    const [matchFilter, setMatchFilter] = useState('')

    useEffect(() => {
        if (selectedClientId) loadData()
    }, [page, matchFilter, sortBy, sortOrder, selectedClientId])

    async function loadData() {
        setLoading(true)
        setError(null)
        try {
            const params = {
                page,
                page_size: 50,
                sort_by: sortBy,
                sort_order: sortOrder,
                client_id: selectedClientId
            }
            if (matchFilter) params.match_type = matchFilter
            const res = await getKeywords(params)
            setData(res)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function handleSort(field) {
        if (sortBy === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        else { setSortBy(field); setSortOrder('desc') }
    }

    function handleExport(format) {
        const params = new URLSearchParams({ client_id: selectedClientId, format })
        window.location.href = `/api/v1/export/keywords?${params.toString()}`
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={loadData} />

    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Słowa kluczowe
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        {data.total} słów kluczowych
                    </p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    {/* Match type filter */}
                    <div className="flex items-center gap-1">
                        {['', 'EXACT', 'PHRASE', 'BROAD'].map(m => {
                            const active = matchFilter === m
                            const cfg = m ? MATCH_COLORS[m] : null
                            return (
                                <button
                                    key={m}
                                    onClick={() => { setMatchFilter(m); setPage(1) }}
                                    style={{
                                        padding: '4px 11px', borderRadius: 999, fontSize: 11, fontWeight: active ? 500 : 400,
                                        border: `1px solid ${active ? (cfg?.color || '#4F8EF7') : 'rgba(255,255,255,0.1)'}`,
                                        background: active ? (cfg ? cfg.bg : 'rgba(79,142,247,0.18)') : 'transparent',
                                        color: active ? (cfg?.color || 'white') : 'rgba(255,255,255,0.4)',
                                        cursor: 'pointer',
                                    }}
                                >
                                    {m || 'Wszystkie'}
                                </button>
                            )
                        })}
                    </div>

                    {/* Export buttons */}
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => handleExport('csv')}
                            title="Eksportuj CSV"
                            style={{
                                display: 'flex', alignItems: 'center', gap: 5,
                                padding: '5px 10px', borderRadius: 7, fontSize: 11,
                                background: 'rgba(255,255,255,0.04)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
                            }}
                            className="hover:border-white/20 hover:text-white/70"
                        >
                            <Download size={12} /> CSV
                        </button>
                        <button
                            onClick={() => handleExport('xlsx')}
                            title="Eksportuj Excel"
                            style={{
                                display: 'flex', alignItems: 'center', gap: 5,
                                padding: '5px 10px', borderRadius: 7, fontSize: 11,
                                background: 'rgba(74,222,128,0.06)',
                                border: '1px solid rgba(74,222,128,0.2)',
                                color: '#4ADE80', cursor: 'pointer',
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
                                        <th style={TH_STYLE}>Słowo kluczowe</th>
                                        <th style={TH_STYLE}>Dopasowanie</th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('clicks')}>
                                            <span className="flex items-center gap-1">Kliknięcia {sortBy === 'clicks' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('impressions')}>
                                            <span className="flex items-center gap-1">Wyświetlenia {sortBy === 'impressions' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('cost')}>
                                            <span className="flex items-center gap-1">Koszt {sortBy === 'cost' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('conversions')}>
                                            <span className="flex items-center gap-1">Konwersje {sortBy === 'conversions' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('ctr')}>
                                            <span className="flex items-center gap-1">CTR {sortBy === 'ctr' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={{ ...TH_STYLE, cursor: 'pointer' }} onClick={() => handleSort('avg_cpc')}>
                                            <span className="flex items-center gap-1">Avg CPC {sortBy === 'avg_cpc' && <ArrowUpDown size={10} style={{ color: '#4F8EF7' }} />}</span>
                                        </th>
                                        <th style={TH_STYLE}>QS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.items.map((k, i) => {
                                        const mc = MATCH_COLORS[k.match_type]
                                        return (
                                            <tr
                                                key={k.id || i}
                                                style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.12s' }}
                                                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                            >
                                                <td style={{ padding: '10px 12px', fontSize: 13, fontWeight: 500, color: '#F0F0F0', maxWidth: 280 }}>
                                                    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        {k.text}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    {mc ? (
                                                        <span style={{
                                                            fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                                            background: mc.bg, color: mc.color, border: `1px solid ${mc.border}`,
                                                        }}>
                                                            {k.match_type}
                                                        </span>
                                                    ) : (
                                                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{k.match_type}</span>
                                                    )}
                                                </td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{k.clicks?.toLocaleString() ?? '—'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{k.impressions?.toLocaleString() ?? '—'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{k.cost != null ? `${k.cost.toFixed(2)} zł` : '—'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }}>{k.conversions?.toFixed(1) ?? '—'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{k.ctr != null ? `${(k.ctr / 10000).toFixed(2)}%` : '—'}</td>
                                                <td style={{ padding: '10px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>{k.avg_cpc != null ? `${k.avg_cpc.toFixed(2)} zł` : '—'}</td>
                                                <td style={{ padding: '10px 12px' }}>
                                                    <QSBadge score={k.quality_score} />
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center justify-between" style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                Strona {data.page} z {data.total_pages}
                            </span>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page <= 1}
                                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page <= 1 ? 0.3 : 1 }}
                                >
                                    <ChevronLeft size={14} />
                                </button>
                                <button
                                    onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                                    disabled={page >= data.total_pages}
                                    style={{ padding: '5px 8px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', opacity: page >= data.total_pages ? 0.3 : 1 }}
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
