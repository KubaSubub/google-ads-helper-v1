import {
    MousePointerClick, DollarSign, Target, TrendingUp, TrendingDown,
    Eye, Percent, ArrowUpRight, Crosshair, Wallet, Activity, BarChart3,
} from 'lucide-react'

// ─── CampaignKpiRow ───────────────────────────────────────────────────────────
// Props:
//   kpis         — object { current, change_pct } from getCampaignKPIs
//   campaignType — string e.g. 'SEARCH', 'PERFORMANCE_MAX', …
export default function CampaignKpiRow({ kpis, campaignType }) {
    if (!kpis) return null
    const { current, change_pct } = kpis

    // Core metrics (always shown)
    const coreItems = [
        { label: 'Kliknięcia', key: 'clicks', icon: MousePointerClick, color: '#4F8EF7' },
        { label: 'Wyświetlenia', key: 'impressions', icon: Eye, color: '#4F8EF7' },
        { label: 'Koszt', key: 'cost', suffix: ' zł', icon: DollarSign, color: '#7B5CE0' },
        { label: 'Konwersje', key: 'conversions', icon: Target, color: '#4ADE80' },
        { label: 'Wartość konw.', key: 'conversion_value', suffix: ' zł', icon: Wallet, color: '#4ADE80' },
        { label: 'CTR', key: 'ctr', suffix: '%', icon: Percent, color: '#FBBF24', tooltip: 'Click-Through Rate' },
        { label: 'Avg CPC', key: 'avg_cpc', suffix: ' zł', icon: DollarSign, color: '#7B5CE0', tooltip: 'Średni koszt kliknięcia' },
        { label: 'CPA', key: 'cpa', suffix: ' zł', icon: Crosshair, color: '#F87171', tooltip: 'Koszt za konwersję', invertChange: true },
        { label: 'CVR', key: 'conversion_rate', suffix: '%', icon: Activity, color: '#4ADE80', tooltip: 'Conversion Rate' },
        { label: 'ROAS', key: 'roas', suffix: '×', icon: BarChart3, color: '#FBBF24', tooltip: 'Return On Ad Spend' },
    ]

    // IS metrics (SEARCH only)
    const isItems = campaignType === 'SEARCH' ? [
        { label: 'Impr. Share', key: 'search_impression_share', isPct: true, icon: ArrowUpRight, color: '#4F8EF7', tooltip: 'Udział w wyświetleniach' },
        { label: 'Top IS', key: 'search_top_impression_share', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: 'Wyśw. na górze strony' },
        { label: 'Abs Top IS', key: 'search_abs_top_impression_share', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: 'Wyśw. na samej górze' },
        { label: 'Budget Lost IS', key: 'search_budget_lost_is', isPct: true, icon: Wallet, color: '#F87171', tooltip: 'Utracone — budżet', invertChange: true },
        { label: 'Rank Lost IS', key: 'search_rank_lost_is', isPct: true, icon: TrendingDown, color: '#FBBF24', tooltip: 'Utracone — ranking', invertChange: true },
        { label: 'Click Share', key: 'search_click_share', isPct: true, icon: MousePointerClick, color: '#4F8EF7', tooltip: 'Udział w kliknięciach' },
        { label: 'Abs Top %', key: 'abs_top_impression_pct', isPct: true, icon: ArrowUpRight, color: '#4F8EF7', tooltip: '% wyśw. na 1. pozycji' },
        { label: 'Top Impr %', key: 'top_impression_pct', isPct: true, icon: ArrowUpRight, color: '#7B5CE0', tooltip: '% wyśw. na górze' },
    ] : []

    const allItems = [...coreItems, ...isItems]

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 16 }}>
            {allItems.map(({ label, key, suffix = '', icon: Icon, color, tooltip, isPct, invertChange }) => {
                const raw = current?.[key]
                // IS values from backend are 0.0-1.0 scale, display as percentage
                const value = isPct && raw != null ? +(raw * 100).toFixed(1) : raw
                const displaySuffix = isPct ? '%' : suffix
                const rawChange = change_pct?.[key]
                // For CPA and lost IS, lower is better — invert the color
                const changeForColor = invertChange ? -(rawChange || 0) : (rawChange || 0)
                const isUp = changeForColor > 0
                const isDown = changeForColor < 0

                return (
                    <div key={key} className="v2-card" style={{ padding: '10px 12px' }}>
                        <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                            <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', lineHeight: 1.2 }} title={tooltip || undefined}>{label}</span>
                            <div style={{ width: 20, height: 20, borderRadius: 5, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Icon size={10} style={{ color }} />
                            </div>
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1 }}>
                            {value != null ? value.toLocaleString('pl-PL', { maximumFractionDigits: 2 }) : '—'}{value != null ? displaySuffix : ''}
                        </div>
                        {rawChange !== undefined && rawChange !== null && (
                            <div style={{ marginTop: 3, fontSize: 10, color: isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: 2 }}>
                                {isUp ? <TrendingUp size={9} /> : isDown ? <TrendingDown size={9} /> : null}
                                {rawChange > 0 ? '+' : ''}{rawChange.toFixed(1)}%
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}
