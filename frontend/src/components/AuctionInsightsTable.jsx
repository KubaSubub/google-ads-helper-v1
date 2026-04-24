import { useMemo } from 'react'
import { C, TH, TD, TD_DIM } from '../constants/designTokens'
import EmptyState from './EmptyState'

// ─── Reusable Auction Insights Table ─────────────────────────────────────────
// Wyciagniete z features/competitive/CompetitivePage.jsx — teraz reusable dla Campaigns.
// Props:
//   rows — tablica { display_domain, is_self, impression_share, overlap_rate,
//                     position_above_rate, outranking_share, top_of_page_rate,
//                     abs_top_of_page_rate }
//   compact — gdy true, ukrywa niektore kolumny (dla widoku Campaigns)
//   limit — ile wierszy pokazac (default: wszystkie)

function fmtPct(val) {
    if (val == null) return '—'
    return (Number(val) * 100).toFixed(1) + '%'
}

function pctVal(val) {
    if (val == null) return 0
    return Number(val) * 100
}

function MetricBar({ value, maxValue, color }) {
    if (value == null || maxValue <= 0) return <span style={{ color: C.w30 }}>—</span>
    const pct = Number(value) * 100
    const widthPct = Math.min((pct / maxValue) * 100, 100)
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
            <span style={{ fontSize: 12, fontFamily: 'monospace', color: C.w80, minWidth: 44, textAlign: 'right' }}>
                {pct.toFixed(1)}%
            </span>
            <div style={{ width: 60, height: 6, borderRadius: 3, background: C.w06, overflow: 'hidden', flexShrink: 0 }}>
                <div style={{ width: `${widthPct}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s ease' }} />
            </div>
        </div>
    )
}

function ImpressionShareBar({ value, maxValue, isSelf }) {
    if (value == null) return <span style={{ color: C.w30 }}>—</span>
    const pct = Number(value) * 100
    const widthPct = maxValue > 0 ? Math.min((pct / maxValue) * 100, 100) : 0
    const color = isSelf ? C.accentBlue : pct >= 30 ? C.success : pct >= 15 ? C.warning : C.danger
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
            <span style={{ fontSize: 12, fontFamily: 'monospace', color, fontWeight: isSelf ? 700 : 500, minWidth: 44, textAlign: 'right' }}>
                {pct.toFixed(1)}%
            </span>
            <div style={{ width: 60, height: 6, borderRadius: 3, background: C.w06, overflow: 'hidden', flexShrink: 0 }}>
                <div style={{ width: `${widthPct}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s ease' }} />
            </div>
        </div>
    )
}

export default function AuctionInsightsTable({ rows = [], compact = false, limit = null, emptyMessage = 'Brak danych Auction Insights' }) {
    const sorted = useMemo(() => {
        return [...(rows || [])].sort((a, b) => {
            const aVal = a.impression_share != null ? Number(a.impression_share) : -1
            const bVal = b.impression_share != null ? Number(b.impression_share) : -1
            return bVal - aVal
        })
    }, [rows])

    const displayed = limit ? sorted.slice(0, limit) : sorted

    const maxImprShare = useMemo(() => Math.max(...(rows || []).map(r => pctVal(r.impression_share)), 1), [rows])
    const maxOverlap = useMemo(() => Math.max(...(rows || []).map(r => pctVal(r.overlap_rate)), 1), [rows])
    const maxOutranking = useMemo(() => Math.max(...(rows || []).map(r => pctVal(r.outranking_share)), 1), [rows])

    if (!rows || rows.length === 0) {
        return <EmptyState message={emptyMessage} />
    }

    return (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
                <tr>
                    <th style={{ ...TH, width: 32 }}>#</th>
                    <th style={TH}>Domena / Konkurent</th>
                    <th style={{ ...TH, textAlign: 'right' }}>Impression Share</th>
                    {!compact && <th style={{ ...TH, textAlign: 'right' }}>Overlap</th>}
                    {!compact && <th style={{ ...TH, textAlign: 'right' }}>Position Above</th>}
                    <th style={{ ...TH, textAlign: 'right' }}>Outranking</th>
                    {!compact && <th style={{ ...TH, textAlign: 'right' }}>Top of page</th>}
                    {!compact && <th style={{ ...TH, textAlign: 'right' }}>Abs. top</th>}
                </tr>
            </thead>
            <tbody>
                {displayed.map((row, i) => {
                    const isSelf = row.is_self === true || row.is_self === 1
                    const rankInSorted = sorted.findIndex(r => r === row)
                    const rank = rankInSorted >= 0 ? rankInSorted + 1 : i + 1
                    return (
                        <tr key={i} style={{
                            borderTop: `1px solid ${C.w05}`,
                            background: isSelf ? 'rgba(79,142,247,0.08)' : 'transparent',
                        }}>
                            <td style={{ ...TD_DIM, textAlign: 'center', fontSize: 11, fontWeight: 500 }}>{rank}</td>
                            <td style={{ ...TD_DIM, fontWeight: isSelf ? 700 : 400, color: isSelf ? C.accentBlue : TD_DIM.color }}>
                                {row.display_domain || '—'}
                                {isSelf && (
                                    <span style={{
                                        marginLeft: 8, fontSize: 10, fontWeight: 600, color: C.accentBlue,
                                        background: C.infoBg, borderRadius: 4, padding: '1px 6px', verticalAlign: 'middle',
                                    }}>Ty</span>
                                )}
                            </td>
                            <td style={{ ...TD, textAlign: 'right' }}>
                                <ImpressionShareBar value={row.impression_share} maxValue={maxImprShare} isSelf={isSelf} />
                            </td>
                            {!compact && (
                                <td style={{ ...TD, textAlign: 'right' }}>
                                    <MetricBar value={row.overlap_rate} maxValue={maxOverlap} color="#7B5CE0" />
                                </td>
                            )}
                            {!compact && (
                                <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.position_above_rate)}</td>
                            )}
                            <td style={{ ...TD, textAlign: 'right' }}>
                                <MetricBar value={row.outranking_share} maxValue={maxOutranking} color="#4ADE80" />
                            </td>
                            {!compact && <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.top_of_page_rate)}</td>}
                            {!compact && <td style={{ ...TD, textAlign: 'right' }}>{fmtPct(row.abs_top_of_page_rate)}</td>}
                        </tr>
                    )
                })}
            </tbody>
        </table>
    )
}
