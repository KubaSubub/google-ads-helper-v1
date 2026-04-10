// MiniKpiGrid — customizable KPI grid with ALL Google Ads metrics
// User picks which KPIs to display (persisted in localStorage)
import { useState, useMemo, useRef, useEffect } from 'react'
import {
    TrendingUp, TrendingDown, MousePointerClick, DollarSign, Target,
    BarChart3, Eye, Percent, ShoppingCart, Trash2, ArrowUpDown,
    Crosshair, Users, Layers, Award, Search, Settings2, X, Check,
    Banknote, Activity, TrendingUp as TrendUp2, Info,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

// ── Full KPI catalog ──────────────────────────────────────────────────────
const ALL_KPIS = [
    // Core Performance
    { id: 'clicks', title: 'Klikniecia', field: 'clicks', icon: MousePointerClick, color: '#4F8EF7', suffix: '', category: 'Wyniki',
      tooltip: 'Kliknięcia — liczba kliknięć w Twoje reklamy. Surowy wolumen ruchu sprowadzonego z reklam do witryny.' },
    { id: 'impressions', title: 'Wyswietlenia', field: 'impressions', icon: Eye, color: '#7B5CE0', suffix: '', category: 'Wyniki',
      tooltip: 'Wyświetlenia — ile razy reklama pojawiła się na ekranie użytkownika (niezależnie od kliknięcia). Mierzy zasięg kampanii.' },
    { id: 'cost_usd', title: 'Koszt', field: 'cost_usd', icon: DollarSign, color: '#7B5CE0', suffix: ' zl', invertChange: true, category: 'Koszty',
      tooltip: 'Koszt (Spend) — łączna kwota wydana na reklamy w wybranym okresie. Im niższy przy tej samej liczbie konwersji, tym lepiej.' },
    { id: 'conversions', title: 'Konwersje', field: 'conversions', icon: Target, color: '#4ADE80', suffix: '', category: 'Wyniki',
      tooltip: 'Konwersje — działania użytkowników uznane za wartościowe (zakup, formularz, telefon). Google raportuje ułamkowo, bo przypisuje konwersje proporcjonalnie do modelu atrybucji.' },
    { id: 'conversion_value_usd', title: 'Przychod', field: 'conversion_value_usd', icon: Banknote, color: '#4ADE80', suffix: ' zl', category: 'Wyniki',
      tooltip: 'Wartość konwersji (Conversion Value) — łączny przychód z wszystkich konwersji. Dla e-commerce to zwykle wartość zamówień.' },
    { id: 'ctr', title: 'CTR', field: 'ctr', icon: Percent, color: '#4F8EF7', suffix: '%', category: 'Wskazniki',
      tooltip: 'CTR — Click-Through Rate, stosunek kliknięć do wyświetleń (kliknięcia ÷ wyświetlenia). Mierzy trafność reklamy. Dla brand: >5%, dla non-brand: >2%.' },
    { id: 'cvr', title: 'CVR', field: 'cvr', icon: Activity, color: '#4ADE80', suffix: '%', category: 'Wskazniki',
      tooltip: 'CVR — Conversion Rate, procent kliknięć zakończonych konwersją (konwersje ÷ kliknięcia). Mierzy jakość ruchu i landing page.' },
    { id: 'roas', title: 'ROAS', field: 'roas', icon: BarChart3, color: '#FBBF24', suffix: 'x', category: 'Wskazniki',
      tooltip: 'ROAS — Return On Ad Spend, przychód na każdą wydaną złotówkę (wartość konwersji ÷ koszt). Np. 3.0× = 3 zł przychodu za 1 zł wydatku. Dla e-commerce >3× = dobrze, >4× = świetnie.' },
    { id: 'cpa', title: 'CPA', field: 'cpa', icon: ShoppingCart, color: '#F87171', suffix: ' zl', invertChange: true, category: 'Koszty',
      tooltip: 'CPA — Cost Per Acquisition, średni koszt pozyskania jednej konwersji (koszt ÷ konwersje). Kluczowa metryka efektywności. Niższy = lepiej.' },
    { id: 'avg_cpc_usd', title: 'Avg. CPC', field: 'avg_cpc_usd', icon: ArrowUpDown, color: '#F87171', suffix: ' zl', invertChange: true, category: 'Koszty',
      tooltip: 'CPC — Cost Per Click, średni koszt jednego kliknięcia (koszt ÷ kliknięcia). Zależy od konkurencji, Quality Score i strategii stawek.' },
    { id: 'wasted_spend', title: 'Wasted Spend', field: '_wasted_spend', icon: Trash2, color: '#F87171', suffix: ' zl', invertChange: true, category: 'Koszty',
      tooltip: 'Wasted Spend — wydatki na słowa kluczowe i frazy z 0 konwersji (>3 kliknięć). To budżet który nie przynosi żadnej wartości — kandydaci do wykluczenia lub pauzy. Klik → lista fraz do przejrzenia.',
      link: '/search-terms?segment=WASTE' },

    // Extended Conversions
    { id: 'all_conversions', title: 'Konw. (wszystkie)', field: 'all_conversions', icon: Target, color: '#4ADE80', suffix: '', category: 'Konwersje',
      tooltip: 'All Conversions — wszystkie konwersje łącznie z cross-device i view-through (widziana, ale nie kliknięta reklama). Daje pełniejszy obraz wpływu reklam.' },
    { id: 'all_conversions_value_usd', title: 'Przychod (wszystkie)', field: 'all_conversions_value_usd', icon: Banknote, color: '#4ADE80', suffix: ' zl', category: 'Konwersje',
      tooltip: 'All Conversions Value — łączna wartość wszystkich konwersji (w tym view-through i cross-device). Szersza miara ROI niż podstawowa wartość konwersji.' },
    { id: 'cross_device_conversions', title: 'Cross-device', field: 'cross_device_conversions', icon: Users, color: '#7B5CE0', suffix: '', category: 'Konwersje',
      tooltip: 'Cross-device Conversions — konwersje gdzie użytkownik kliknął reklamę na jednym urządzeniu (np. telefon), a skonwertował się na innym (np. laptop). Pokazuje prawdziwy wpływ reklam na zachowanie zakupowe.' },
    { id: 'value_per_conversion_usd', title: 'Wartosc/konw.', field: 'value_per_conversion_usd', icon: Award, color: '#FBBF24', suffix: ' zl', category: 'Konwersje',
      tooltip: 'Value Per Conversion — średnia wartość jednej konwersji (wartość konwersji ÷ konwersje). Innymi słowy: średnia wartość zamówienia. Rosnący trend = klienci kupują drożej.' },

    // Search Impression Share
    { id: 'search_impression_share', title: 'Search IS', field: 'search_impression_share', icon: Search, color: '#4F8EF7', suffix: '', category: 'Udzial',
      tooltip: 'Search Impression Share — procent aukcji które wygrałeś spośród wszystkich w których mogłeś się pokazać. 80% = tracisz 20% potencjału. Najważniejsza metryka pokrycia.', format: 'pct' },
    { id: 'search_top_impression_share', title: 'Top IS', field: 'search_top_impression_share', icon: Search, color: '#4F8EF7', suffix: '', category: 'Udzial',
      tooltip: 'Top IS — procent wyświetleń gdzie reklama pojawiła się nad wynikami organicznymi (top of page). Wysokie wartości = silna widoczność.', format: 'pct' },
    { id: 'search_abs_top_impression_share', title: 'Abs. Top IS', field: 'search_abs_top_impression_share', icon: Search, color: '#4F8EF7', suffix: '', category: 'Udzial',
      tooltip: 'Absolute Top IS — procent wyświetleń na absolutnej 1. pozycji (najwyższa reklama nad wynikami). Premium widoczność dla słów brand.', format: 'pct' },
    { id: 'search_budget_lost_is', title: 'Lost IS (budzet)', field: 'search_budget_lost_is', icon: DollarSign, color: '#F87171', suffix: '', invertChange: true, category: 'Udzial',
      tooltip: 'Lost IS (Budget) — procent aukcji które przegrałeś bo skończył się budżet. Jeśli rośnie a wydajesz 100% budżetu → dorzuć pieniądze. Wysoka wartość = market jest większy niż twój budżet.', format: 'pct' },
    { id: 'search_rank_lost_is', title: 'Lost IS (ranking)', field: 'search_rank_lost_is', icon: TrendUp2, color: '#F87171', suffix: '', invertChange: true, category: 'Udzial',
      tooltip: 'Lost IS (Rank) — procent aukcji przegranych bo Ad Rank był zbyt słaby (niska stawka, słaby Quality Score, brak rozszerzeń). Rośnie → trzeba podnieść stawki lub poprawić QS.', format: 'pct' },
    { id: 'search_click_share', title: 'Click Share', field: 'search_click_share', icon: MousePointerClick, color: '#4F8EF7', suffix: '', category: 'Udzial',
      tooltip: 'Search Click Share — procent wszystkich możliwych kliknięć w Twoim segmencie które zebrałeś. Podobnie do IS, ale dla kliknięć zamiast wyświetleń.', format: 'pct' },

    // Position metrics
    { id: 'abs_top_impression_pct', title: 'Abs. Top %', field: 'abs_top_impression_pct', icon: Layers, color: '#7B5CE0', suffix: '', category: 'Pozycja',
      tooltip: 'Abs Top % — procent Twoich wyświetleń które trafiły na absolutnie pierwszą pozycję (nad wszystkimi innymi reklamami). Różni się od Abs Top IS — bazuje na Twoich wyświetleniach, nie na całym rynku.', format: 'pct' },
    { id: 'top_impression_pct', title: 'Top %', field: 'top_impression_pct', icon: Layers, color: '#7B5CE0', suffix: '', category: 'Pozycja',
      tooltip: 'Top % — procent Twoich wyświetleń które pojawiły się nad wynikami organicznymi. Wysokie wartości = reklamy konkurują o premium placement.', format: 'pct' },

    // Account
    { id: 'active_campaigns', title: 'Aktywne kampanie', field: 'active_campaigns', icon: Crosshair, color: '#4ADE80', suffix: '', category: 'Konto',
      tooltip: 'Aktywne kampanie — liczba kampanii w statusie ENABLED. Nie obejmuje PAUSED ani REMOVED. Prosty wskaźnik skali konta.' },
]

const STORAGE_KEY = 'dashboard_kpi_selection'
const DEFAULT_SELECTION = [
    'clicks', 'cost_usd', 'conversions', 'roas',
    'conversion_value_usd', 'cvr', 'avg_cpc_usd', 'wasted_spend',
]

function getStoredSelection() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
            const parsed = JSON.parse(stored)
            if (Array.isArray(parsed) && parsed.length > 0) return parsed
        }
    } catch {}
    return DEFAULT_SELECTION
}

// ── Floating info tooltip for KPI cards ──────────────────────────────────
function KpiInfoTooltip({ title, content }) {
    const [visible, setVisible] = useState(false)
    const [coords, setCoords] = useState({ top: 0, left: 0 })
    const triggerRef = useRef(null)

    useEffect(() => {
        if (!visible || !triggerRef.current) return
        const rect = triggerRef.current.getBoundingClientRect()
        const width = 300
        let left = rect.left + rect.width / 2 - width / 2
        if (left < 8) left = 8
        if (left + width > window.innerWidth - 8) left = window.innerWidth - width - 8
        setCoords({ top: rect.bottom + 8, left })
    }, [visible])

    return (
        <span
            ref={triggerRef}
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
            onClick={e => e.stopPropagation()}
            style={{ display: 'inline-flex', alignItems: 'center', cursor: 'help', padding: 2 }}
        >
            <Info size={11} style={{ color: 'rgba(255,255,255,0.35)' }} />
            {visible && (
                <div
                    style={{
                        position: 'fixed',
                        top: coords.top,
                        left: coords.left,
                        width: 300,
                        padding: '12px 14px',
                        background: '#1a1d24',
                        border: '1px solid rgba(255,255,255,0.12)',
                        borderRadius: 8,
                        fontSize: 11,
                        lineHeight: 1.55,
                        color: 'rgba(255,255,255,0.75)',
                        zIndex: 9999,
                        pointerEvents: 'none',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                    }}
                >
                    <div style={{
                        fontWeight: 700,
                        color: '#4F8EF7',
                        marginBottom: 4,
                        fontSize: 10,
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        fontFamily: 'Syne',
                    }}>
                        {title}
                    </div>
                    {content}
                </div>
            )}
        </span>
    )
}

// ── Single KPI card ───────────────────────────────────────────────────────
function MiniKPI({ title, tooltip, value, change, suffix = '', icon: Icon, iconColor = '#4F8EF7', invertChange = false, onClick, format }) {
    const isUp = change > 0
    const isDown = change < 0
    const changeColor = invertChange
        ? (isUp ? '#F87171' : isDown ? '#4ADE80' : 'rgba(255,255,255,0.3)')
        : (isUp ? '#4ADE80' : isDown ? '#F87171' : 'rgba(255,255,255,0.3)')

    let display
    if (value == null) {
        display = '—'
    } else if (format === 'pct') {
        display = (value * 100).toFixed(1) + '%'
    } else if (typeof value === 'number') {
        display = value.toLocaleString('pl-PL', { maximumFractionDigits: 2 })
    } else {
        display = value
    }

    return (
        <div
            className="v2-card"
            style={{ padding: '14px 18px', cursor: onClick ? 'pointer' : 'default' }}
            onClick={onClick}
        >
            <div className="flex items-center justify-between mb-2">
                <span style={{
                    fontSize: 10, fontWeight: 500,
                    color: 'rgba(255,255,255,0.35)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                }}>
                    {title}
                    {tooltip && <KpiInfoTooltip title={title} content={tooltip} />}
                </span>
                {Icon && (
                    <div style={{ width: 26, height: 26, borderRadius: 6, background: `${iconColor}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Icon size={13} style={{ color: iconColor }} />
                    </div>
                )}
            </div>
            <div style={{ fontSize: 21, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1, marginBottom: 6 }}>
                {format === 'pct' ? display : <>{display}{suffix}</>}
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

// ── KPI Picker Modal ──────────────────────────────────────────────────────
function KpiPicker({ selected, onSave, onClose }) {
    const [sel, setSel] = useState(new Set(selected))

    const toggle = (id) => {
        const next = new Set(sel)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSel(next)
    }

    const categories = useMemo(() => {
        const map = {}
        ALL_KPIS.forEach(k => {
            if (!map[k.category]) map[k.category] = []
            map[k.category].push(k)
        })
        return map
    }, [])

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={onClose}>
            <div
                style={{
                    background: '#13151B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 16,
                    padding: '24px 28px', maxWidth: 620, width: '90%', maxHeight: '80vh', overflow: 'auto',
                }}
                onClick={e => e.stopPropagation()}
            >
                <div className="flex items-center justify-between" style={{ marginBottom: 20 }}>
                    <div>
                        <h3 style={{ fontSize: 16, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', margin: 0 }}>
                            Wybierz KPI
                        </h3>
                        <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', margin: '4px 0 0' }}>
                            Zaznacz metryki do wyswietlenia na dashboardzie ({sel.size} wybranych)
                        </p>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer' }}>
                        <X size={18} />
                    </button>
                </div>

                {Object.entries(categories).map(([cat, kpis]) => (
                    <div key={cat} style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
                            {cat}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                            {kpis.map(k => {
                                const active = sel.has(k.id)
                                return (
                                    <button
                                        key={k.id}
                                        onClick={() => toggle(k.id)}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: 8,
                                            padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                                            border: active ? `1px solid ${k.color}40` : '1px solid rgba(255,255,255,0.06)',
                                            background: active ? `${k.color}10` : 'rgba(255,255,255,0.02)',
                                            color: active ? '#F0F0F0' : 'rgba(255,255,255,0.5)',
                                            fontSize: 12, textAlign: 'left',
                                        }}
                                    >
                                        {active && <Check size={12} style={{ color: k.color, flexShrink: 0 }} />}
                                        <k.icon size={12} style={{ color: k.color, flexShrink: 0 }} />
                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{k.title}</span>
                                    </button>
                                )
                            })}
                        </div>
                    </div>
                ))}

                <div className="flex items-center justify-between" style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <button
                        onClick={() => setSel(new Set(DEFAULT_SELECTION))}
                        style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                        Przywroc domyslne
                    </button>
                    <button
                        onClick={() => { onSave([...sel]); onClose() }}
                        disabled={sel.size === 0}
                        style={{
                            padding: '8px 20px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                            background: '#4F8EF7', color: '#fff', border: 'none',
                            opacity: sel.size === 0 ? 0.4 : 1,
                        }}
                    >
                        Zapisz ({sel.size} KPI)
                    </button>
                </div>
            </div>
        </div>
    )
}

// ── Main Grid ─────────────────────────────────────────────────────────────
export default function MiniKpiGrid({ current, change_pct, wastedSpend }) {
    const navigate = useNavigate()
    const [selectedIds, setSelectedIds] = useState(getStoredSelection)
    const [pickerOpen, setPickerOpen] = useState(false)

    const handleSave = (ids) => {
        setSelectedIds(ids)
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
    }

    const kpiMap = useMemo(() => {
        const m = {}
        ALL_KPIS.forEach(k => { m[k.id] = k })
        return m
    }, [])

    // Resolve value + change for each selected KPI
    const resolveKpi = (kpiDef) => {
        if (kpiDef.id === 'wasted_spend') {
            return {
                value: wastedSpend?.total_waste_usd,
                change: wastedSpend?.waste_change_pct ?? null,
                dynamicColor: wastedSpend
                    ? (wastedSpend.waste_pct > 25 ? '#F87171' : wastedSpend.waste_pct > 15 ? '#FBBF24' : '#4ADE80')
                    : '#F87171',
            }
        }
        return {
            value: current?.[kpiDef.field],
            change: change_pct?.[kpiDef.field],
        }
    }

    const selectedKpis = selectedIds.map(id => kpiMap[id]).filter(Boolean)
    const cols = selectedKpis.length <= 4 ? selectedKpis.length : 4

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Gear button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    onClick={() => setPickerOpen(true)}
                    title="Dostosuj metryki KPI"
                    style={{
                        background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                        color: 'rgba(255,255,255,0.25)', display: 'flex', alignItems: 'center', gap: 4,
                    }}
                >
                    <Settings2 size={13} />
                    <span style={{ fontSize: 10 }}>Dostosuj KPI</span>
                </button>
            </div>

            {/* KPI cards in rows of 4 */}
            {Array.from({ length: Math.ceil(selectedKpis.length / cols) }, (_, rowIdx) => (
                <div key={rowIdx} style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 12 }}>
                    {selectedKpis.slice(rowIdx * cols, rowIdx * cols + cols).map(kpi => {
                        const { value, change, dynamicColor } = resolveKpi(kpi)
                        return (
                            <MiniKPI
                                key={kpi.id}
                                title={kpi.title}
                                tooltip={kpi.tooltip}
                                value={value}
                                change={change}
                                suffix={kpi.suffix}
                                icon={kpi.icon}
                                iconColor={dynamicColor || kpi.color}
                                invertChange={kpi.invertChange}
                                format={kpi.format}
                                onClick={kpi.link ? () => navigate(kpi.link) : undefined}
                            />
                        )
                    })}
                </div>
            ))}

            {selectedKpis.length === 0 && (
                <div className="v2-card" style={{ padding: 24, textAlign: 'center' }}>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                        Brak wybranych KPI. Kliknij "Dostosuj KPI" aby wybrac metryki.
                    </p>
                </div>
            )}

            {pickerOpen && (
                <KpiPicker
                    selected={selectedIds}
                    onSave={handleSave}
                    onClose={() => setPickerOpen(false)}
                />
            )}
        </div>
    )
}
