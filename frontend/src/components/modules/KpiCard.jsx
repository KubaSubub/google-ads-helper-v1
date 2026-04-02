import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

function DeltaIndicator({ value, invertColor = false }) {
    if (value === null || value === undefined) return <span style={{ color: 'rgba(255,255,255,0.3)' }}>—</span>
    const isPositive = value > 0
    const isGood = invertColor ? !isPositive : isPositive
    const color = Math.abs(value) < 1 ? 'rgba(255,255,255,0.4)' : isGood ? '#4ADE80' : '#F87171'
    const Icon = value > 0 ? TrendingUp : value < 0 ? TrendingDown : Minus
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color, fontSize: 12, fontWeight: 500 }}>
            <Icon size={12} />
            {value > 0 ? '+' : ''}{value}%
        </span>
    )
}

export default function KpiCard({
    label,
    current,
    previous,
    delta,
    prefix = '',
    suffix = '',
    invertColor = false,
    size = 'md',
}) {
    // size="sm" → compact chip (DailyAudit style)
    // size="md" → standard card (Reports style)
    const isSm = size === 'sm'

    // Compute delta from current/previous when delta not provided explicitly
    const computedDelta = delta !== undefined ? delta
        : (previous != null && previous > 0)
            ? +((current - previous) / previous * 100).toFixed(1)
            : null

    const cardStyle = isSm
        ? { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 12, padding: '12px 16px', flex: '1 1 140px', minWidth: 120 }
        : { padding: '14px 16px', flex: '1 1 0' }

    const valueFormatted = isSm
        ? `${prefix}${typeof current === 'number' ? current.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}${suffix}`
        : (typeof current === 'string' ? current : `${prefix}${current}${suffix}`)

    return (
        <div className={isSm ? undefined : 'v2-card'} style={cardStyle}>
            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: isSm ? '0.08em' : '0.05em', marginBottom: 6 }}>
                {label}
            </div>
            <div style={{ fontSize: isSm ? 20 : 22, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0', lineHeight: isSm ? 1 : undefined }}>
                {valueFormatted}
            </div>
            {isSm ? (
                // DailyAudit chip style: trend icon + "X% vs poprz. okres"
                computedDelta != null && previous != null && previous > 0 && (
                    <div style={{ fontSize: 10, marginTop: 4, display: 'flex', alignItems: 'center', gap: 3,
                        color: computedDelta > 0 ? '#4ADE80' : computedDelta < 0 ? '#F87171' : 'rgba(255,255,255,0.25)' }}>
                        {computedDelta > 0 ? <TrendingUp size={10} /> : computedDelta < 0 ? <TrendingDown size={10} /> : null}
                        <span>{Math.abs(computedDelta).toFixed(1)}% vs poprz. okres</span>
                    </div>
                )
            ) : (
                // Reports card style: DeltaIndicator + "vs {previous}"
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <DeltaIndicator value={computedDelta} invertColor={invertColor} />
                    {previous !== undefined && (
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                            vs {previous}
                        </span>
                    )}
                </div>
            )}
        </div>
    )
}

export { DeltaIndicator }
