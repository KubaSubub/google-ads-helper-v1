import PacingProgressBar from './PacingProgressBar'
import { getPacingColor, getPacingBg, getPacingLabel, getTableBarColor } from './pacing-utils'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../../constants/designTokens'

// ─── Cards variant (Dashboard grid, single-campaign Campaigns view) ───
function PacingCards({ campaigns, month, title, linkTo, onNavigate }) {
    return (
        <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                    {title || `Pacing budżetu${month ? ` (${month})` : ''}`}
                </span>
                {linkTo && onNavigate && (
                    <span onClick={() => onNavigate(linkTo)} style={{ fontSize: 11, color: C.accentBlue, cursor: 'pointer' }}>
                        Wszystkie →
                    </span>
                )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                {campaigns.map(c => {
                    const color = getPacingColor(c.status)
                    const bg = getPacingBg(c.status)
                    const label = getPacingLabel(c.status)
                    return (
                        <div key={c.campaign_id} className="v2-card" style={{ padding: '12px 14px' }}>
                            <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                                <span style={{ fontSize: 12, fontWeight: 500, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }}>
                                    {c.campaign_name}
                                </span>
                                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: bg, color, border: `1px solid ${color}30` }}>
                                    {label}
                                </span>
                            </div>
                            <PacingProgressBar pct={Math.min(c.pacing_pct, 150)} color={color} height={4} style={{ marginBottom: 6 }} />
                            <div className="flex items-center justify-between" style={{ fontSize: 11, color: C.w40 }}>
                                <span>{c.actual_spend_usd?.toFixed(0) ?? '—'} / {c.expected_spend_usd?.toFixed(0) ?? '—'} zł</span>
                                <span style={{ color }}>{c.pacing_pct}%</span>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

// ─── Single-campaign detail (Campaigns page detail view) ───
function PacingSingle({ campaign, title }) {
    const c = campaign
    const color = getPacingColor(c.status)
    const bg = getPacingBg(c.status)
    const label = getPacingLabel(c.status)
    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 10, fontFamily: 'Syne' }}>
                {title || 'Pacing budżetu'}
            </div>
            <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: C.w50 }}>
                    {c.actual_spend_usd?.toFixed(0)} / {c.expected_spend_usd?.toFixed(0)} zł (proj. {c.projected_spend_usd?.toFixed(0)} zł)
                </span>
                <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: bg, color, border: `1px solid ${color}30` }}>
                    {label}
                </span>
            </div>
            <PacingProgressBar pct={Math.min(c.pacing_pct, 100)} color={color} height={6} />
            <div className="flex items-center justify-between" style={{ marginTop: 4, fontSize: 10, color: C.textMuted }}>
                <span>Dzień {c.days_elapsed} / {c.days_in_month}</span>
                <span style={{ color }}>{c.pacing_pct}%</span>
            </div>
        </div>
    )
}

// ─── Table variant (DailyAudit) ───
const LEGEND_ITEMS = [
    { color: C.danger, label: '< 50% — niedostateczne wydawanie' },
    { color: C.warning, label: '50–80% — umiarkowane' },
    { color: C.success, label: '80–120% — zgodnie z planem' },
    { color: C.danger, label: '> 120% — przekroczenie budżetu' },
]

function PacingTable({ campaigns, showLegend }) {
    const referenceDate = campaigns[0]?.reference_date
    return (
        <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, fontWeight: 500, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
                <span>Pacing budżetu kampanii</span>
                {referenceDate && (
                    <span style={{ fontSize: 10, color: C.w20, fontStyle: 'italic', textTransform: 'none', letterSpacing: 0 }}>
                        (dane z {referenceDate})
                    </span>
                )}
            </div>
            <div className="v2-card" style={{ overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: B.subtle }}>
                                {['Kampania', 'Budżet dzienny', 'Wydane', 'Pacing', 'Status'].map(h => (
                                    <th key={h} style={{
                                        padding: '8px 12px', fontSize: 10, fontWeight: 500,
                                        color: C.textMuted, textTransform: 'uppercase',
                                        letterSpacing: '0.08em', textAlign: 'left',
                                    }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {campaigns.map((c, i) => {
                                const pct = c.pacing_pct || 0
                                const barColor = getTableBarColor(pct)
                                return (
                                    <tr key={i} style={{ borderBottom: `1px solid ${C.w04}` }}>
                                        <td style={{ padding: '8px 12px', fontSize: 12, color: C.textPrimary, fontWeight: 500, maxWidth: 250 }}>
                                            <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</span>
                                        </td>
                                        <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: C.w60 }}>
                                            {c.daily_budget?.toFixed(2)} zł
                                        </td>
                                        <td style={{ padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: C.w60 }}>
                                            {(c.spent ?? c.spent_today)?.toFixed(2)} zł
                                        </td>
                                        <td style={{ padding: '8px 12px', width: 160 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <div style={{ flex: 1 }}>
                                                    <PacingProgressBar pct={pct} color={barColor} height={4} />
                                                </div>
                                                <span style={{ fontSize: 10, color: barColor, fontWeight: 600, minWidth: 32, textAlign: 'right' }}>{pct.toFixed(0)}%</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '8px 12px' }}>
                                            {c.is_limited && (
                                                <span style={{
                                                    fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 999,
                                                    background: 'rgba(251,191,36,0.12)', color: C.warning,
                                                    border: '1px solid rgba(251,191,36,0.25)',
                                                }}>
                                                    LIMITED
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
                {showLegend && (
                    <div style={{
                        padding: '8px 12px', borderTop: `1px solid ${C.w04}`,
                        display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center',
                    }}>
                        {LEGEND_ITEMS.map((item, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                                <div style={{ width: 8, height: 8, borderRadius: 2, background: item.color, flexShrink: 0 }} />
                                <span style={{ fontSize: 9, color: C.w30 }}>{item.label}</span>
                            </div>
                        ))}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 4px', borderRadius: 3, background: 'rgba(251,191,36,0.12)', color: C.warning }}>LIMITED</span>
                            <span style={{ fontSize: 9, color: C.w30 }}>— kampania traci IS z powodu budżetu</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

// ─── Main export ───
export default function BudgetPacingModule({
    campaigns,
    month,
    variant = 'cards',
    title,
    linkTo,
    onNavigate,
    showLegend = false,
}) {
    if (!campaigns || campaigns.length === 0) return null

    if (variant === 'table') {
        return <PacingTable campaigns={campaigns} showLegend={showLegend} />
    }

    // Single campaign → detail view (Campaigns page)
    if (campaigns.length === 1 && !linkTo) {
        return <PacingSingle campaign={campaigns[0]} title={title} />
    }

    return <PacingCards campaigns={campaigns} month={month} title={title} linkTo={linkTo} onNavigate={onNavigate} />
}
