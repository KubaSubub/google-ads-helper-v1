// MiniKpiGrid — two rows of mini KPI cards (clicks, cost, conversions, ROAS, impressions, CTR, CPA, wasted spend)
import { TrendingUp, TrendingDown, MousePointerClick, DollarSign, Target, BarChart3, Eye, Percent, ShoppingCart, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

function MiniKPI({ title, tooltip, value, change, suffix = '', prefix = '', icon: Icon, iconColor = '#4F8EF7', invertChange = false }) {
    const isUp = change > 0
    const isDown = change < 0
    const changeColor = invertChange
        ? (isUp ? '#F87171' : isDown ? '#4ADE80' : 'rgba(255,255,255,0.3)')
        : (isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)')
    const display = typeof value === 'number'
        ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 })
        : (value ?? '—')

    return (
        <div className="v2-card" style={{ padding: '14px 18px' }}>
            <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.1em' }} title={tooltip || undefined}>
                    {title}
                </span>
                {Icon && (
                    <div style={{ width: 26, height: 26, borderRadius: 6, background: `${iconColor}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Icon size={13} style={{ color: iconColor }} />
                    </div>
                )}
            </div>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1, marginBottom: 6 }}>
                {prefix}{display}{suffix}
            </div>
            {change !== undefined && change !== null && (
                <div style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 3, color: changeColor }}>
                    {isUp ? <TrendingUp size={11} /> : isDown ? <TrendingDown size={11} /> : null}
                    <span>{Math.abs(change).toFixed(1)}%</span>
                    <span style={{ color: 'rgba(255,255,255,0.25)' }}>vs poprz.</span>
                </div>
            )}
        </div>
    )
}

export default function MiniKpiGrid({ current, change_pct, wastedSpend }) {
    const navigate = useNavigate()

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <MiniKPI
                    title="Kliknięcia"
                    value={current?.clicks}
                    change={change_pct?.clicks}
                    icon={MousePointerClick}
                    iconColor="#4F8EF7"
                />
                <MiniKPI
                    title="Koszt"
                    value={current?.cost_usd}
                    change={change_pct?.cost_usd}
                    suffix=" zł"
                    icon={DollarSign}
                    iconColor="#7B5CE0"
                    invertChange
                />
                <MiniKPI
                    title="Konwersje"
                    value={current?.conversions}
                    change={change_pct?.conversions}
                    icon={Target}
                    iconColor="#4ADE80"
                />
                <MiniKPI
                    title="ROAS"
                    tooltip="Return On Ad Spend — przychód na każdą wydaną złotówkę"
                    value={current?.roas}
                    change={change_pct?.roas}
                    suffix="×"
                    icon={BarChart3}
                    iconColor="#FBBF24"
                />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <MiniKPI
                    title="Wyświetlenia"
                    value={current?.impressions}
                    change={change_pct?.impressions}
                    icon={Eye}
                    iconColor="#7B5CE0"
                />
                <MiniKPI
                    title="CTR"
                    tooltip="Click-Through Rate — stosunek kliknięć do wyświetleń"
                    value={current?.ctr}
                    change={change_pct?.ctr}
                    suffix="%"
                    icon={Percent}
                    iconColor="#4F8EF7"
                />
                <MiniKPI
                    title="CPA"
                    tooltip="Cost Per Acquisition — koszt pozyskania konwersji"
                    value={current?.cpa}
                    change={change_pct?.cpa}
                    suffix=" zł"
                    icon={ShoppingCart}
                    iconColor="#F87171"
                    invertChange
                />
                {wastedSpend && (
                    <div onClick={() => navigate('/search-terms?segment=WASTE')} style={{ cursor: 'pointer' }}>
                        <MiniKPI
                            title="Wasted Spend"
                            tooltip="Wydatki bez konwersji — kliknij aby zobaczyć waste terms"
                            value={wastedSpend.total_waste_usd}
                            suffix=" zł"
                            icon={Trash2}
                            iconColor={wastedSpend.waste_pct > 25 ? '#F87171' : wastedSpend.waste_pct > 15 ? '#FBBF24' : '#4ADE80'}
                        />
                    </div>
                )}
            </div>
        </div>
    )
}
