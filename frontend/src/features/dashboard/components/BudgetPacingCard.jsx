// BudgetPacingCard — compact total pacing bar + expandable per-campaign table
// Props:
//   data: { campaigns, days_elapsed, days_in_month } — from getBudgetPacing()
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { C, B } from '../../../constants/designTokens'

function statusLabel(s) {
    return s === 'on_track' ? 'Na torze'
         : s === 'overspend' ? 'Przekroczenie'
         : s === 'underspend' ? 'Niedostateczne'
         : '—'
}

function statusColor(s) {
    return s === 'on_track' ? C.success
         : s === 'overspend' ? C.danger
         : s === 'underspend' ? C.warning
         : C.w30
}

export default function BudgetPacingCard({ data }) {
    const navigate = useNavigate()
    const [expanded, setExpanded] = useState(false)

    if (!data?.campaigns?.length) return null

    const camps = data.campaigns
    const onTrack    = camps.filter(c => c.status === 'on_track').length
    const overspend  = camps.filter(c => c.status === 'overspend').length
    const underspend = camps.filter(c => c.status === 'underspend').length
    const totalActual   = camps.reduce((s, c) => s + (c.actual_spend_usd ?? 0), 0)
    const totalExpected = camps.reduce((s, c) => s + (c.expected_spend_usd ?? 0), 0)
    const totalMonthlyBudget = camps.reduce((s, c) => s + (c.monthly_budget_usd ?? 0), 0)
    const totalPct = totalExpected > 0 ? (totalActual / totalExpected * 100) : 0
    const barColor = totalPct > 115 ? C.danger : totalPct < 80 ? C.warning : C.success
    const barPct = Math.min(totalPct, 150)

    // End-of-month projection: extrapolate actual daily rate * days_in_month
    // Only show if we have enough days to be meaningful (> 2 days elapsed)
    const daysElapsed = data.days_elapsed || 0
    const daysInMonth = data.days_in_month || 30
    let projection = null
    if (daysElapsed >= 2 && totalMonthlyBudget > 0) {
        const projectedSpend = (totalActual / daysElapsed) * daysInMonth
        const projectedPct = (projectedSpend / totalMonthlyBudget) * 100
        const projColor = projectedPct > 115 ? C.danger
                        : projectedPct < 80 ? C.warning
                        : C.success
        projection = {
            spend: projectedSpend,
            pct: projectedPct,
            color: projColor,
            label: projectedPct > 115
                ? `Na tym tempie: ${projectedPct.toFixed(0)}% budżetu (przekroczenie)`
                : projectedPct < 80
                ? `Na tym tempie: ${projectedPct.toFixed(0)}% budżetu (niewykorzystanie)`
                : `Na tym tempie: ${projectedPct.toFixed(0)}% budżetu`,
        }
    }

    const sortedCamps = [...camps].sort((a, b) => {
        // Sort: overspend first, then underspend, then on_track — most urgent at top
        const order = { overspend: 0, underspend: 1, on_track: 2, no_data: 3 }
        return (order[a.status] ?? 9) - (order[b.status] ?? 9)
    })

    return (
        <div className="v2-card" style={{ marginBottom: 16, overflow: 'hidden' }}>
            {/* Header row — clickable to expand */}
            <div
                onClick={() => setExpanded(e => !e)}
                style={{ padding: '14px 20px', cursor: 'pointer', userSelect: 'none' }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                        Pacing budżetu ({daysElapsed}/{daysInMonth} dni)
                    </span>
                    <div style={{ display: 'flex', gap: 10, marginLeft: 'auto', fontSize: 11 }}>
                        <span style={{ color: C.success }}>● {onTrack} na torze</span>
                        {overspend > 0 && <span style={{ color: C.danger }}>● {overspend} przekroczenie</span>}
                        {underspend > 0 && <span style={{ color: C.warning }}>● {underspend} niedostateczne</span>}
                    </div>
                    <ChevronDown size={14} style={{ color: C.w40, transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ flex: 1, height: 8, borderRadius: 4, background: C.w06, overflow: 'hidden', position: 'relative' }}>
                        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(barPct / 150 * 100).toFixed(0)}%`, background: barColor, transition: 'width 0.3s' }} />
                        <div style={{ position: 'absolute', left: `${(100 / 150 * 100).toFixed(0)}%`, top: -2, bottom: -2, width: 1, background: 'rgba(255,255,255,0.25)' }} />
                    </div>
                    <span style={{ fontSize: 12, fontFamily: 'monospace', color: barColor, fontWeight: 600, minWidth: 50, textAlign: 'right' }}>
                        {totalPct.toFixed(0)}%
                    </span>
                    <span style={{ fontSize: 11, color: C.w40, fontFamily: 'monospace' }}>
                        {totalActual.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} / {totalExpected.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                    </span>
                </div>

                {/* End-of-month projection — subtle line below the bar */}
                {projection && (
                    <div style={{
                        marginTop: 8,
                        fontSize: 11,
                        color: projection.color,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                    }}>
                        <span style={{ fontSize: 10 }}>→</span>
                        <span style={{ fontWeight: 500 }}>{projection.label}</span>
                        <span style={{ color: C.w30, fontFamily: 'monospace', marginLeft: 4 }}>
                            (~{projection.spend.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł vs {totalMonthlyBudget.toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł)
                        </span>
                    </div>
                )}
            </div>

            {/* Expandable campaigns list */}
            {expanded && (
                <div style={{ borderTop: B.subtle, padding: '8px 0 12px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px 90px 110px 90px', gap: 12, padding: '6px 20px', fontSize: 9, fontWeight: 500, color: C.w30, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        <span>Kampania</span>
                        <span style={{ textAlign: 'right' }}>Budżet/mies.</span>
                        <span style={{ textAlign: 'right' }}>Wydano</span>
                        <span style={{ textAlign: 'right' }}>Pacing</span>
                        <span style={{ textAlign: 'right' }}>Status</span>
                    </div>
                    {sortedCamps.map(c => {
                        const campPct = Math.min(c.pacing_pct ?? 0, 150)
                        const campColor = statusColor(c.status)
                        return (
                            <div
                                key={c.campaign_id}
                                onClick={() => navigate(`/campaigns?campaign_id=${c.campaign_id}`)}
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 90px 90px 110px 90px',
                                    gap: 12,
                                    padding: '8px 20px',
                                    alignItems: 'center',
                                    cursor: 'pointer',
                                    fontSize: 12,
                                    borderTop: `1px solid ${C.w04}`,
                                    transition: 'background 0.12s',
                                }}
                                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.025)'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                            >
                                <span style={{ color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {c.campaign_name}
                                </span>
                                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: C.w60 }}>
                                    {(c.monthly_budget_usd ?? 0).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                                </span>
                                <span style={{ textAlign: 'right', fontFamily: 'monospace', color: C.w60 }}>
                                    {(c.actual_spend_usd ?? 0).toLocaleString('pl-PL', { maximumFractionDigits: 0 })} zł
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                                    <div style={{ flex: 1, maxWidth: 60, height: 4, borderRadius: 2, background: C.w06, overflow: 'hidden', position: 'relative' }}>
                                        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${(campPct / 150 * 100).toFixed(0)}%`, background: campColor }} />
                                    </div>
                                    <span style={{ fontFamily: 'monospace', color: campColor, fontWeight: 600, minWidth: 36, textAlign: 'right' }}>
                                        {(c.pacing_pct ?? 0).toFixed(0)}%
                                    </span>
                                </div>
                                <span style={{ textAlign: 'right', fontSize: 10, color: campColor, fontWeight: 500 }}>
                                    {statusLabel(c.status)}
                                </span>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
