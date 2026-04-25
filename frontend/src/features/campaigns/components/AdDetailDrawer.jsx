import { useEffect, useState } from 'react'
import { X, ExternalLink, Pin, TrendingUp, TrendingDown } from 'lucide-react'
import { C, FONT } from '../../../constants/designTokens'
import { getAdDetail } from '../../../api'

// ─── Ad Detail Drawer ─────────────────────────────────────────────────────────
// Slide-in panel z prawej (600px) z 5 sekcjami:
//   1. Header — H1 preview, type, ad strength, approval, status
//   2. RSA Assets breakdown — full headlines + descriptions z pinned + perf label
//   3. Performance — 7 KPI grid
//   4. A/B vs grupa — diff_pct vs sibling ads avg
//   5. Akcje — link do Google Ads (RSA edit nie odtwarzamy)
//
// Props:
//   adId — null = closed; number = open + load
//   onClose — callback
//   onAdUpdated — callback po zmianie statusu (opcjonalne, na przyszlosc)

const STRENGTH_COLORS = {
    EXCELLENT: { color: C.success, label: 'Excellent' },
    GOOD: { color: C.success, label: 'Good' },
    AVERAGE: { color: C.warning, label: 'Average' },
    POOR: { color: C.danger, label: 'Poor' },
    UNRATED: { color: C.w40, label: 'Unrated' },
}

const APPROVAL_COLORS = {
    APPROVED: { color: C.success, label: 'Zatwierdzona' },
    APPROVED_LIMITED: { color: C.warning, label: 'Ograniczona' },
    DISAPPROVED: { color: C.danger, label: 'Odrzucona' },
    UNDER_REVIEW: { color: C.accentBlue, label: 'W weryfikacji' },
}

const PERFORMANCE_COLORS = {
    BEST: { color: C.success, label: 'BEST' },
    GOOD: { color: C.success, label: 'GOOD' },
    AVERAGE: { color: C.warning, label: 'AVG' },
    LOW: { color: C.danger, label: 'LOW' },
    PENDING: { color: C.w40, label: 'PENDING' },
    LEARNING: { color: C.accentBlue, label: 'LEARN' },
}

function StrengthGauge({ strength }) {
    const order = ['POOR', 'AVERAGE', 'GOOD', 'EXCELLENT']
    const idx = order.indexOf(strength)
    const segments = order.map((seg, i) => {
        const isFilled = idx >= 0 && i <= idx
        const cfg = STRENGTH_COLORS[seg] || { color: C.w40 }
        return (
            <div
                key={seg}
                style={{
                    flex: 1, height: 6, borderRadius: 3,
                    background: isFilled ? cfg.color : C.w06,
                }}
            />
        )
    })
    const cfg = STRENGTH_COLORS[strength] || STRENGTH_COLORS.UNRATED
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 10, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Ad strength</span>
                <span style={{ fontSize: 12, color: cfg.color, fontWeight: 600 }}>{cfg.label}</span>
            </div>
            <div style={{ display: 'flex', gap: 4 }}>{segments}</div>
        </div>
    )
}

function AssetRow({ entry, kind, index }) {
    if (!entry?.text) return null
    const perfCfg = PERFORMANCE_COLORS[entry.performance_label] || null
    return (
        <div style={{
            display: 'grid', gridTemplateColumns: '24px 1fr auto auto',
            gap: 10, alignItems: 'center',
            padding: '8px 10px', borderRadius: 6,
            background: C.w04, border: `1px solid ${C.w06}`,
        }}>
            <span style={{ fontSize: 10, color: C.w40, fontFamily: FONT.mono }}>
                {kind}{index + 1}
            </span>
            <span style={{ fontSize: 12, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {entry.text}
            </span>
            {entry.pinned_position != null && (
                <span title={`Pinned to position ${entry.pinned_position}`} style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 9, color: C.accentBlue }}>
                    <Pin size={10} /> {entry.pinned_position}
                </span>
            )}
            {!entry.pinned_position && <span></span>}
            {perfCfg ? (
                <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 999, color: perfCfg.color, border: `1px solid ${perfCfg.color}40` }}>
                    {perfCfg.label}
                </span>
            ) : (
                <span style={{ fontSize: 9, color: C.w30 }}>—</span>
            )}
        </div>
    )
}

function DiffBadge({ value, invert = false }) {
    if (value == null) return <span style={{ fontSize: 10, color: C.w30 }}>—</span>
    const isUp = value > 0
    const isDown = value < 0
    // For CPA — lower is better (invert color)
    const goodDirection = invert ? isDown : isUp
    const badDirection = invert ? isUp : isDown
    const color = goodDirection ? C.success : badDirection ? C.danger : C.w40
    const Icon = isUp ? TrendingUp : isDown ? TrendingDown : null
    return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 2, fontSize: 11, color, fontFamily: FONT.mono }}>
            {Icon && <Icon size={10} />}
            {value > 0 ? '+' : ''}{value.toFixed(1)}%
        </span>
    )
}

function MetricCard({ label, value, suffix = '', diff = null, invertDiff = false }) {
    return (
        <div className="v2-card" style={{ padding: '10px 12px' }}>
            <div style={{ fontSize: 9, color: C.w40, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                {label}
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, fontFamily: 'Syne', lineHeight: 1.1, marginBottom: 4 }}>
                {value}{suffix}
            </div>
            <div style={{ fontSize: 10, color: C.w30 }}>
                vs avg grupy: <DiffBadge value={diff} invert={invertDiff} />
            </div>
        </div>
    )
}

export default function AdDetailDrawer({ adId, onClose }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!adId) {
            setData(null)
            setError(null)
            return
        }
        setLoading(true)
        setError(null)
        getAdDetail(adId)
            .then(res => setData(res))
            .catch(err => setError(err.message || 'Blad ladowania reklamy'))
            .finally(() => setLoading(false))
    }, [adId])

    // ESC closes drawer
    useEffect(() => {
        if (!adId) return
        const handler = (e) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [adId, onClose])

    if (!adId) return null

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    zIndex: 999,
                }}
            />
            {/* Drawer */}
            <div style={{
                position: 'fixed', top: 0, right: 0, bottom: 0,
                width: 640, maxWidth: '90vw',
                background: '#0D0F14',
                borderLeft: `1px solid ${C.w10}`,
                boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
                zIndex: 1000,
                display: 'flex', flexDirection: 'column',
            }}>
                {/* Header bar */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '14px 20px',
                    borderBottom: `1px solid ${C.w06}`,
                    flexShrink: 0,
                }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                        Szczegóły reklamy
                    </div>
                    <button
                        onClick={onClose}
                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: C.w60, padding: 4 }}
                        title="Zamknij (ESC)"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
                    {loading && (
                        <div style={{ textAlign: 'center', padding: 40, color: C.w30, fontSize: 12 }}>
                            Ładowanie reklamy…
                        </div>
                    )}
                    {error && (
                        <div style={{ padding: 16, background: C.dangerBg, color: C.danger, borderRadius: 8, fontSize: 12 }}>
                            {error}
                        </div>
                    )}
                    {data && data.ad && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                            {/* 1. Header — H1 preview + meta */}
                            <section>
                                <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 4 }}>
                                    {data.ad.headlines?.[0]?.text || '(brak nagłówka)'}
                                </div>
                                {data.ad.headlines?.[1]?.text && (
                                    <div style={{ fontSize: 12, color: C.w60, marginBottom: 8 }}>
                                        {data.ad.headlines[1].text}
                                    </div>
                                )}
                                {data.ad.descriptions?.[0]?.text && (
                                    <div style={{ fontSize: 11, color: C.w40, marginBottom: 12, fontStyle: 'italic' }}>
                                        {data.ad.descriptions[0].text}
                                    </div>
                                )}
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: C.infoBg, color: C.accentBlue }}>
                                        {data.ad.ad_type || '—'}
                                    </span>
                                    {data.ad.status && (
                                        <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, background: data.ad.status === 'ENABLED' ? C.successBg : C.warningBg, color: data.ad.status === 'ENABLED' ? C.success : C.warning }}>
                                            ● {data.ad.status === 'ENABLED' ? 'Aktywna' : data.ad.status === 'PAUSED' ? 'Wstrzymana' : data.ad.status}
                                        </span>
                                    )}
                                    {data.ad.approval_status && (() => {
                                        const ac = APPROVAL_COLORS[data.ad.approval_status] || { color: C.w40, label: data.ad.approval_status }
                                        return (
                                            <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 999, color: ac.color, border: `1px solid ${ac.color}40` }}>
                                                {ac.label}
                                            </span>
                                        )
                                    })()}
                                </div>
                                <StrengthGauge strength={data.ad.ad_strength || 'UNRATED'} />
                            </section>

                            {/* 2. RSA Assets breakdown */}
                            <section>
                                <div style={{ fontSize: 11, fontWeight: 600, color: C.w60, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                                    Nagłówki ({data.ad.headlines_count})
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    {data.ad.headlines?.length > 0
                                        ? data.ad.headlines.map((h, i) => <AssetRow key={i} entry={h} kind="H" index={i} />)
                                        : <div style={{ fontSize: 11, color: C.w30, padding: 8 }}>Brak nagłówków</div>
                                    }
                                </div>
                                <div style={{ fontSize: 11, fontWeight: 600, color: C.w60, textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 16, marginBottom: 8 }}>
                                    Opisy ({data.ad.descriptions_count})
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    {data.ad.descriptions?.length > 0
                                        ? data.ad.descriptions.map((d, i) => <AssetRow key={i} entry={d} kind="D" index={i} />)
                                        : <div style={{ fontSize: 11, color: C.w30, padding: 8 }}>Brak opisów</div>
                                    }
                                </div>
                                {(data.ad.long_headline || data.ad.business_name) && (
                                    <div style={{ marginTop: 12, fontSize: 11, color: C.w60 }}>
                                        {data.ad.business_name && <div><span style={{ color: C.w40 }}>Brand:</span> {data.ad.business_name}</div>}
                                        {data.ad.long_headline && <div><span style={{ color: C.w40 }}>Long headline:</span> {data.ad.long_headline}</div>}
                                    </div>
                                )}
                            </section>

                            {/* 3. Performance + 4. A/B vs grupa (combined w 1 grid) */}
                            <section>
                                <div style={{ fontSize: 11, fontWeight: 600, color: C.w60, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                                    Wyniki vs grupa reklam ({data.comparison?.siblings_count || 0} sąsiadów)
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                                    <MetricCard
                                        label="Kliknięcia"
                                        value={(data.ad.clicks || 0).toLocaleString('pl-PL')}
                                        diff={data.comparison?.diff_pct?.clicks}
                                    />
                                    <MetricCard
                                        label="Wyświetlenia"
                                        value={(data.ad.impressions || 0).toLocaleString('pl-PL')}
                                        diff={data.comparison?.diff_pct?.impressions}
                                    />
                                    <MetricCard
                                        label="CTR"
                                        value={(data.ad.ctr || 0).toFixed(2)}
                                        suffix="%"
                                        diff={data.comparison?.diff_pct?.ctr}
                                    />
                                    <MetricCard
                                        label="Koszt"
                                        value={(data.ad.cost || 0).toFixed(0)}
                                        suffix=" zł"
                                        diff={data.comparison?.diff_pct?.cost}
                                    />
                                    <MetricCard
                                        label="Konwersje"
                                        value={(data.ad.conversions || 0).toFixed(1)}
                                        diff={data.comparison?.diff_pct?.conversions}
                                    />
                                    <MetricCard
                                        label="CPA"
                                        value={data.ad.cpa ? data.ad.cpa.toFixed(2) : '—'}
                                        suffix={data.ad.cpa ? ' zł' : ''}
                                        diff={data.comparison?.diff_pct?.cpa}
                                        invertDiff={true}
                                    />
                                </div>
                            </section>

                            {/* 5. Akcje */}
                            <section>
                                <div style={{ fontSize: 11, fontWeight: 600, color: C.w60, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                                    Akcje
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {data.ad.final_url && (
                                        <a
                                            href={data.ad.final_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 6,
                                                padding: '8px 12px', borderRadius: 8,
                                                background: C.w04, border: `1px solid ${C.w10}`,
                                                color: C.accentBlue, fontSize: 12, textDecoration: 'none',
                                            }}
                                        >
                                            <ExternalLink size={12} /> Otwórz Final URL
                                            <span style={{ marginLeft: 'auto', fontSize: 10, color: C.w40, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>
                                                {data.ad.final_url}
                                            </span>
                                        </a>
                                    )}
                                    <div style={{ fontSize: 10, color: C.w30, padding: '4px 0' }}>
                                        Edycja RSA assets dostępna tylko w Google Ads UI (zbyt wiele pól dla helpera).
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}
