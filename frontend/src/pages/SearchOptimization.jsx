import { useState, useEffect } from 'react'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import EmptyState from '../components/EmptyState'
import { ErrorMessage } from '../components/UI'
import {
    getDayparting, getRsaAnalysis, getNgramAnalysis,
    getMatchTypeAnalysis, getLandingPages, getWastedSpend,
    getAccountStructure, getBiddingAdvisor, getHourlyDayparting,
} from '../api'
import {
    Loader2, CalendarDays, FileText, Hash, Layers, Globe, AlertTriangle,
    ChevronDown, ChevronRight, ExternalLink, TrendingDown, TrendingUp,
    GitBranch, Target, Clock,
} from 'lucide-react'

const SECTION_STYLE = { marginBottom: 24 }
const CARD = 'v2-card'
const TH = {
    padding: '8px 12px', fontSize: 10, fontWeight: 500,
    color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase',
    letterSpacing: '0.08em', whiteSpace: 'nowrap', textAlign: 'left',
}
const TD = { padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', color: 'rgba(255,255,255,0.8)' }
const TD_DIM = { ...TD, color: 'rgba(255,255,255,0.45)' }

function SectionHeader({ icon: Icon, title, subtitle, open, onToggle }) {
    return (
        <button
            onClick={onToggle}
            style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                padding: '12px 16px', cursor: 'pointer',
                background: 'transparent', border: 'none', textAlign: 'left',
            }}
        >
            <Icon size={16} style={{ color: '#4F8EF7', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#F0F0F0' }}>{title}</span>
                {subtitle && <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginLeft: 8 }}>{subtitle}</span>}
            </div>
            {open ? <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.3)' }} /> : <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />}
        </button>
    )
}

function MetricPill({ label, value, color }) {
    return (
        <div style={{
            display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
            padding: '8px 14px', borderRadius: 10,
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
        }}>
            <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 2 }}>{label}</span>
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'Syne', color: color || '#F0F0F0' }}>{value}</span>
        </div>
    )
}

function MatchBadge({ type }) {
    const colors = {
        EXACT: { color: '#4ADE80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
        PHRASE: { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)', border: 'rgba(79,142,247,0.2)' },
        BROAD: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
    }
    const c = colors[type] || { color: 'rgba(255,255,255,0.5)', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)' }
    return (
        <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999, background: c.bg, color: c.color, border: `1px solid ${c.border}` }}>
            {type}
        </span>
    )
}

// ─────────────────────────────────────────────────────────
// 1. WASTED SPEND
// ─────────────────────────────────────────────────────────
function WastedSpendSection({ data }) {
    if (!data) return null
    const { total_waste_usd, total_spend_usd, waste_pct, categories } = data
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
                <MetricPill label="Zmarnowany budżet" value={`${total_waste_usd.toFixed(0)} zł`} color="#F87171" />
                <MetricPill label="Całkowity spend" value={`${total_spend_usd.toFixed(0)} zł`} />
                <MetricPill label="% Waste" value={`${waste_pct}%`} color={waste_pct > 15 ? '#F87171' : waste_pct > 8 ? '#FBBF24' : '#4ADE80'} />
            </div>
            {['keywords', 'search_terms', 'ads'].map(cat => {
                const c = categories[cat]
                if (!c || c.count === 0) return null
                const labels = { keywords: 'Słowa kluczowe', search_terms: 'Frazy wyszukiwania', ads: 'Reklamy' }
                return (
                    <div key={cat} style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.5)', marginBottom: 6 }}>
                            {labels[cat]} ({c.count}) — {c.waste_usd.toFixed(2)} zł
                        </div>
                        {c.top_items?.slice(0, 5).map((item, i) => (
                            <div key={i} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '4px 8px', borderRadius: 6,
                                background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                            }}>
                                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.text}</span>
                                <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#F87171' }}>{item.cost_usd.toFixed(2)} zł</span>
                            </div>
                        ))}
                    </div>
                )
            })}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 2. DAYPARTING
// ─────────────────────────────────────────────────────────
function DaypartingSection({ data }) {
    if (!data?.days?.length) return null
    const maxClicks = Math.max(...data.days.map(d => d.clicks))
    const maxConv = Math.max(...data.days.map(d => d.conversions))
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8 }}>
                {data.days.map(d => {
                    const barH = maxClicks > 0 ? (d.clicks / maxClicks * 48) : 0
                    const convBarH = maxConv > 0 ? (d.conversions / maxConv * 48) : 0
                    const isWeekend = d.day_of_week >= 5
                    return (
                        <div key={d.day_of_week} style={{
                            padding: 10, borderRadius: 8, textAlign: 'center',
                            background: isWeekend ? 'rgba(248,113,113,0.05)' : 'rgba(255,255,255,0.03)',
                            border: `1px solid ${isWeekend ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.07)'}`,
                        }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: isWeekend ? '#F87171' : '#F0F0F0', marginBottom: 8 }}>
                                {d.day_name}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: 3, height: 52, alignItems: 'flex-end', marginBottom: 8 }}>
                                <div style={{ width: 14, height: barH, background: '#4F8EF7', borderRadius: 3, minHeight: 2 }} title={`Kliknięcia: ${d.clicks}`} />
                                <div style={{ width: 14, height: convBarH, background: '#4ADE80', borderRadius: 3, minHeight: 2 }} title={`Konwersje: ${d.conversions}`} />
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>{d.avg_clicks} klik/dz</div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>{d.avg_conversions.toFixed(1)} conv/dz</div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>CPA {d.cpa.toFixed(0)} zł</div>
                        </div>
                    )
                })}
            </div>
            <div className="flex items-center gap-4" style={{ marginTop: 10, fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: '#4F8EF7' }} /> Kliknięcia
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: '#4ADE80' }} /> Konwersje
                </span>
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 3. MATCH TYPE ANALYSIS
// ─────────────────────────────────────────────────────────
function MatchTypeSection({ data }) {
    if (!data?.match_types?.length) return null
    return (
        <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>Dopasowanie</th>
                        <th style={TH}>Słów kl.</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CTR</th>
                        <th style={TH}>CPC</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>ROAS</th>
                        <th style={TH}>Udział %</th>
                    </tr>
                </thead>
                <tbody>
                    {data.match_types.map(mt => (
                        <tr key={mt.match_type} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit' }}><MatchBadge type={mt.match_type} /></td>
                            <td style={TD_DIM}>{mt.keyword_count}</td>
                            <td style={TD}>{mt.clicks.toLocaleString()}</td>
                            <td style={TD}>{mt.cost_usd.toFixed(2)} zł</td>
                            <td style={TD}>{mt.conversions.toFixed(1)}</td>
                            <td style={TD_DIM}>{mt.ctr}%</td>
                            <td style={TD_DIM}>{mt.cpc.toFixed(2)} zł</td>
                            <td style={TD}>{mt.cpa > 0 ? `${mt.cpa.toFixed(2)} zł` : '—'}</td>
                            <td style={TD_DIM}>{mt.cvr}%</td>
                            <td style={TD}>{mt.roas.toFixed(2)}</td>
                            <td style={TD_DIM}>{mt.cost_share_pct}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 4. N-GRAM ANALYSIS
// ─────────────────────────────────────────────────────────
function NgramSection({ data, ngramSize, setNgramSize }) {
    if (!data?.ngrams) return null
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
                {[1, 2, 3].map(n => (
                    <button
                        key={n}
                        onClick={() => setNgramSize(n)}
                        style={{
                            padding: '4px 11px', borderRadius: 999, fontSize: 11, cursor: 'pointer',
                            border: `1px solid ${ngramSize === n ? '#4F8EF7' : 'rgba(255,255,255,0.1)'}`,
                            background: ngramSize === n ? 'rgba(79,142,247,0.18)' : 'transparent',
                            color: ngramSize === n ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                        }}
                    >
                        {n === 1 ? 'Słowa' : n === 2 ? 'Bigramy' : 'Trigramy'}
                    </button>
                ))}
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginLeft: 8 }}>{data.total} wyników</span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>N-gram</th>
                        <th style={TH}>Wystąpień</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>CPA</th>
                    </tr>
                </thead>
                <tbody>
                    {data.ngrams.slice(0, 30).map((ng, i) => {
                        const isWaste = ng.conversions === 0 && ng.cost_usd > 10
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: isWaste ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: isWaste ? '#F87171' : '#F0F0F0' }}>{ng.ngram}</td>
                                <td style={TD_DIM}>{ng.occurrences}</td>
                                <td style={TD}>{ng.clicks.toLocaleString()}</td>
                                <td style={TD}>{ng.cost_usd.toFixed(2)} zł</td>
                                <td style={TD}>{ng.conversions.toFixed(1)}</td>
                                <td style={TD_DIM}>{ng.cvr}%</td>
                                <td style={TD}>{ng.cpa > 0 ? `${ng.cpa.toFixed(2)} zł` : '—'}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 5. RSA ANALYSIS
// ─────────────────────────────────────────────────────────
function RsaSection({ data }) {
    if (!data?.ad_groups?.length) return null
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.ad_groups.map(group => (
                <div key={group.ad_group_id} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {group.ad_group_name}
                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                            {group.ad_count} reklam • CTR spread: {group.ctr_spread}pp
                        </span>
                    </div>
                    {group.ads.map(ad => {
                        const isBest = ad.ctr_pct === group.best_ctr && group.ads.length > 1
                        const isWorst = ad.ctr_pct === group.worst_ctr && group.ads.length > 1 && group.ctr_spread > 0.5
                        return (
                            <div key={ad.id} style={{
                                padding: '10px 12px', borderRadius: 8, marginBottom: 6,
                                background: isBest ? 'rgba(74,222,128,0.04)' : isWorst ? 'rgba(248,113,113,0.04)' : 'rgba(255,255,255,0.02)',
                                border: `1px solid ${isBest ? 'rgba(74,222,128,0.15)' : isWorst ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.05)'}`,
                            }}>
                                <div className="flex items-center justify-between flex-wrap gap-2" style={{ marginBottom: 6 }}>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {isBest && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 999, background: 'rgba(74,222,128,0.15)', color: '#4ADE80', fontWeight: 600 }}>BEST</span>}
                                        {isWorst && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 999, background: 'rgba(248,113,113,0.15)', color: '#F87171', fontWeight: 600 }}>WORST</span>}
                                        {ad.ad_strength && (() => {
                                            const sc = { EXCELLENT: '#4ADE80', GOOD: '#4F8EF7', AVERAGE: '#FBBF24', POOR: '#F87171', UNRATED: 'rgba(255,255,255,0.3)' }
                                            const c = sc[ad.ad_strength] || sc.UNRATED
                                            return <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 999, background: `${c}15`, color: c, border: `1px solid ${c}30`, fontWeight: 600 }}>{ad.ad_strength}</span>
                                        })()}
                                        {ad.approval_status && ad.approval_status !== 'APPROVED' && (() => {
                                            const ac = { DISAPPROVED: '#F87171', APPROVED_LIMITED: '#FBBF24', UNDER_REVIEW: '#FBBF24' }
                                            const c = ac[ad.approval_status] || 'rgba(255,255,255,0.3)'
                                            return <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 999, background: `${c}15`, color: c, border: `1px solid ${c}30`, fontWeight: 600 }}>{ad.approval_status}</span>
                                        })()}
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>
                                            {ad.status} • {ad.headline_count}H / {ad.description_count}D
                                            {ad.pinned_count > 0 && ` • ${ad.pinned_count} pinned`}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3" style={{ fontSize: 11, fontFamily: 'monospace' }}>
                                        <span style={{ color: 'rgba(255,255,255,0.7)' }}>CTR {ad.ctr_pct}%</span>
                                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>CPC {ad.cpc_usd.toFixed(2)} zł</span>
                                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>{ad.clicks} klik</span>
                                        <span style={{ color: 'rgba(255,255,255,0.7)' }}>{ad.conversions.toFixed(1)} conv</span>
                                    </div>
                                </div>
                                <div style={{ fontSize: 12, color: '#4F8EF7', lineHeight: 1.4 }}>
                                    {ad.headlines.join(' | ')}
                                </div>
                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', lineHeight: 1.3, marginTop: 2 }}>
                                    {ad.descriptions.join(' | ')}
                                </div>
                            </div>
                        )
                    })}
                </div>
            ))}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 6. LANDING PAGE ANALYSIS
// ─────────────────────────────────────────────────────────
function LandingPageSection({ data }) {
    if (!data?.pages?.length) return null
    return (
        <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>URL</th>
                        <th style={TH}>Słów kl.</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>ROAS</th>
                    </tr>
                </thead>
                <tbody>
                    {data.pages.map((p, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', maxWidth: 300 }}>
                                <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#4F8EF7' }} title={p.url}>
                                    {p.url.replace(/^https?:\/\/(www\.)?/, '').substring(0, 50)}
                                </span>
                            </td>
                            <td style={TD_DIM}>{p.keyword_count}</td>
                            <td style={TD}>{p.clicks.toLocaleString()}</td>
                            <td style={TD}>{p.cost_usd.toFixed(2)} zł</td>
                            <td style={TD}>{p.conversions.toFixed(1)}</td>
                            <td style={TD_DIM}>{p.cvr}%</td>
                            <td style={TD}>{p.cpa > 0 ? `${p.cpa.toFixed(2)} zł` : '—'}</td>
                            <td style={TD}>{p.roas.toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 7. HOURLY DAYPARTING
// ─────────────────────────────────────────────────────────
function HourlyDaypartingSection({ data }) {
    if (!data?.hours?.length) return null
    const maxConv = Math.max(...data.hours.map(h => h.conversions))
    const maxClicks = Math.max(...data.hours.map(h => h.clicks))
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 3, marginBottom: 12 }}>
                {data.hours.map(h => {
                    const intensity = maxConv > 0 ? h.conversions / maxConv : 0
                    const isBusinessHour = h.hour >= 9 && h.hour <= 18
                    return (
                        <div key={h.hour} title={`${h.hour_label}: ${h.clicks} klik, ${h.conversions} konw, CPA ${h.cpa > 0 ? h.cpa.toFixed(0) + ' zł' : '—'}`}
                            style={{
                                height: 56, borderRadius: 6, cursor: 'default',
                                background: `rgba(79,142,247,${0.08 + intensity * 0.72})`,
                                border: `1px solid ${isBusinessHour ? 'rgba(79,142,247,0.2)' : 'rgba(255,255,255,0.05)'}`,
                                display: 'flex', flexDirection: 'column',
                                alignItems: 'center', justifyContent: 'flex-end',
                                paddingBottom: 4, position: 'relative',
                            }}>
                            {h.conversions > 0 && (
                                <span style={{ fontSize: 8, color: '#4ADE80', fontWeight: 600, marginBottom: 1 }}>
                                    {h.conversions.toFixed(0)}
                                </span>
                            )}
                            <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.5)' }}>
                                {h.hour}
                            </span>
                        </div>
                    )
                })}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>Godzina</th>
                        <th style={TH}>Kliknięcia</th>
                        <th style={TH}>Koszt</th>
                        <th style={TH}>Konwersje</th>
                        <th style={TH}>CTR</th>
                        <th style={TH}>CPA</th>
                        <th style={TH}>CVR</th>
                        <th style={TH}>ROAS</th>
                    </tr>
                </thead>
                <tbody>
                    {data.hours.filter(h => h.clicks > 0).map(h => {
                        const isBizHour = h.hour >= 9 && h.hour <= 18
                        return (
                            <tr key={h.hour} style={{
                                borderBottom: '1px solid rgba(255,255,255,0.04)',
                                background: isBizHour ? 'rgba(79,142,247,0.03)' : 'transparent',
                            }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500 }}>{h.hour_label}</td>
                                <td style={TD}>{h.clicks.toLocaleString()}</td>
                                <td style={TD}>{h.cost_usd.toFixed(2)} zł</td>
                                <td style={TD}>{h.conversions.toFixed(1)}</td>
                                <td style={TD_DIM}>{h.ctr}%</td>
                                <td style={TD}>{h.cpa > 0 ? `${h.cpa.toFixed(0)} zł` : '—'}</td>
                                <td style={TD_DIM}>{h.cvr}%</td>
                                <td style={TD}>{h.roas.toFixed(2)}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 8. ACCOUNT STRUCTURE AUDIT
// ─────────────────────────────────────────────────────────
function SeverityBadge({ severity }) {
    const c = severity === 'HIGH' ? '#F87171' : severity === 'MEDIUM' ? '#FBBF24' : '#4ADE80'
    return (
        <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 999,
            background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
            {severity}
        </span>
    )
}

function AccountStructureSection({ data }) {
    if (!data) return null
    const { issues, oversized_ad_groups, mixed_match_ad_groups, cannibalized_keywords } = data
    if (!issues?.length) {
        return (
            <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
                Brak wykrytych problemów strukturalnych
            </div>
        )
    }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
                {issues.map(issue => (
                    <MetricPill key={issue.type} label={
                        issue.type === 'cannibalization' ? 'Kanibalizacja' :
                        issue.type === 'oversized_ad_groups' ? 'Zbyt duże grupy' : 'Mieszane dopas.'
                    } value={issue.count} color={issue.severity === 'HIGH' ? '#F87171' : '#FBBF24'} />
                ))}
            </div>

            {cannibalized_keywords?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
                        Kanibalizacja słów kluczowych ({cannibalized_keywords.length})
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                <th style={TH}>Słowo kluczowe</th>
                                <th style={TH}>Dopasowanie</th>
                                <th style={TH}>Wystąpień</th>
                                <th style={TH}>Łączny koszt</th>
                                <th style={TH}>Lokalizacje</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cannibalized_keywords.slice(0, 15).map((item, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F87171' }}>{item.keyword_text}</td>
                                    <td style={{ ...TD, fontFamily: 'inherit' }}><MatchBadge type={item.match_type} /></td>
                                    <td style={TD}>{item.occurrences}</td>
                                    <td style={TD}>{item.total_cost_usd.toFixed(2)} zł</td>
                                    <td style={{ ...TD_DIM, fontSize: 10 }}>
                                        {item.locations.map((l, j) => (
                                            <div key={j}>{l.campaign_name} → {l.ad_group_name}</div>
                                        ))}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {oversized_ad_groups?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
                        Zbyt duże grupy reklam — &gt;20 słów kluczowych ({oversized_ad_groups.length})
                    </div>
                    {oversized_ad_groups.map((ag, i) => (
                        <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '6px 8px', borderRadius: 6,
                            background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                        }}>
                            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
                                {ag.campaign_name} → {ag.ad_group_name}
                            </span>
                            <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#FBBF24' }}>
                                {ag.keyword_count} słów
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {mixed_match_ad_groups?.length > 0 && (
                <div>
                    <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
                        Mieszane dopasowania BROAD + EXACT w grupie ({mixed_match_ad_groups.length})
                    </div>
                    {mixed_match_ad_groups.map((ag, i) => (
                        <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '6px 8px', borderRadius: 6,
                            background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                        }}>
                            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
                                {ag.campaign_name} → {ag.ad_group_name}
                            </span>
                            <div className="flex items-center gap-1">
                                {ag.match_types.map(mt => <MatchBadge key={mt} type={mt} />)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 8. BIDDING STRATEGY ADVISOR
// ─────────────────────────────────────────────────────────
function StatusBadge({ status }) {
    const config = {
        OK:                    { label: 'OK',        color: '#4ADE80' },
        UPGRADE_RECOMMENDED:   { label: 'Upgrade',   color: '#FBBF24' },
        CHANGE_RECOMMENDED:    { label: 'Zmień!',    color: '#F87171' },
    }
    const c = config[status] || { label: status, color: 'rgba(255,255,255,0.3)' }
    return (
        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
            background: `${c.color}15`, color: c.color, border: `1px solid ${c.color}30` }}>
            {c.label}
        </span>
    )
}

function BiddingAdvisorSection({ data }) {
    if (!data?.campaigns?.length) return null
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div className="flex items-center gap-3 flex-wrap" style={{ marginBottom: 16 }}>
                <MetricPill label="OK" value={data.summary.ok} color="#4ADE80" />
                <MetricPill label="Upgrade" value={data.summary.upgrade} color="#FBBF24" />
                <MetricPill label="Do zmiany" value={data.summary.change} color="#F87171" />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        <th style={TH}>Kampania</th>
                        <th style={TH}>Obecna strategia</th>
                        <th style={TH}>Rekomendacja</th>
                        <th style={TH}>Konw. / 30d</th>
                        <th style={TH}>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {data.campaigns.map(c => (
                        <tr key={c.campaign_id} style={{
                            borderBottom: '1px solid rgba(255,255,255,0.04)',
                            background: c.status === 'CHANGE_RECOMMENDED' ? 'rgba(248,113,113,0.04)' :
                                        c.status === 'UPGRADE_RECOMMENDED' ? 'rgba(251,191,36,0.04)' : 'transparent',
                        }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {c.campaign_name}
                            </td>
                            <td style={TD_DIM}>{c.current_strategy}</td>
                            <td style={{ ...TD, color: c.status !== 'OK' ? '#4F8EF7' : 'rgba(255,255,255,0.5)' }}>
                                {c.recommended_strategy}
                            </td>
                            <td style={TD}>{c.conversions_30d}</td>
                            <td style={{ ...TD, fontFamily: 'inherit' }}><StatusBadge status={c.status} /></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────
export default function SearchOptimization() {
    const { selectedClientId } = useApp()
    const { filters } = useFilter()
    const days = filters.period || 30

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [sections, setSections] = useState({
        waste: true, dayparting: true, matchType: true,
        ngram: false, rsa: false, landing: false,
        hourly: false, structure: false, bidding: false,
    })
    const [ngramSize, setNgramSize] = useState(1)

    const [waste, setWaste] = useState(null)
    const [daypart, setDaypart] = useState(null)
    const [matchType, setMatchType] = useState(null)
    const [ngram, setNgram] = useState(null)
    const [rsa, setRsa] = useState(null)
    const [landing, setLanding] = useState(null)
    const [hourly, setHourly] = useState(null)
    const [structure, setStructure] = useState(null)
    const [bidding, setBidding] = useState(null)

    useEffect(() => {
        if (selectedClientId) loadAll()
    }, [selectedClientId, days])

    useEffect(() => {
        if (selectedClientId && sections.ngram) {
            getNgramAnalysis(selectedClientId, { ngram_size: ngramSize }).then(setNgram).catch(() => setNgram(null))
        }
    }, [ngramSize, selectedClientId])

    async function loadAll() {
        setLoading(true)
        setError(null)
        try {
            const [w, dp, mt, ng, r, lp, hr, st, bd] = await Promise.all([
                getWastedSpend(selectedClientId, days).catch(() => null),
                getDayparting(selectedClientId, days).catch(() => null),
                getMatchTypeAnalysis(selectedClientId, days).catch(() => null),
                getNgramAnalysis(selectedClientId, { ngram_size: ngramSize }).catch(() => null),
                getRsaAnalysis(selectedClientId).catch(() => null),
                getLandingPages(selectedClientId, days).catch(() => null),
                getHourlyDayparting(selectedClientId).catch(() => null),
                getAccountStructure(selectedClientId).catch(() => null),
                getBiddingAdvisor(selectedClientId, days).catch(() => null),
            ])
            setWaste(w)
            setDaypart(dp)
            setMatchType(mt)
            setNgram(ng)
            setRsa(r)
            setLanding(lp)
            setHourly(hr)
            setStructure(st)
            setBidding(bd)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    function toggle(key) {
        setSections(s => ({ ...s, [key]: !s[key] }))
    }

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />
    if (error) return <ErrorMessage message={error} onRetry={loadAll} />

    if (loading) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 20 }}>
                    Optymalizacja SEARCH
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            </div>
        )
    }

    return (
        <div style={{ maxWidth: 1400 }}>
            <div style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                    Optymalizacja SEARCH
                </h1>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                    Analiza {days} dni — 9 narzędzi optymalizacji kampanii wyszukiwania
                </p>
            </div>

            {/* 1. Wasted Spend */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={AlertTriangle} title="Zmarnowany budżet" subtitle={waste ? `${waste.waste_pct}% spend` : ''} open={sections.waste} onToggle={() => toggle('waste')} />
                {sections.waste && <WastedSpendSection data={waste} />}
            </div>

            {/* 2. Dayparting */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={CalendarDays} title="Harmonogram (dni tygodnia)" subtitle="SEARCH" open={sections.dayparting} onToggle={() => toggle('dayparting')} />
                {sections.dayparting && <DaypartingSection data={daypart} />}
            </div>

            {/* 3. Hourly Dayparting */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={Clock} title="Harmonogram godzinowy" subtitle="heatmap 0-23h" open={sections.hourly} onToggle={() => toggle('hourly')} />
                {sections.hourly && <HourlyDaypartingSection data={hourly} />}
            </div>

            {/* 4. Match Type */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={Layers} title="Analiza dopasowań" subtitle={matchType ? `${matchType.match_types.length} typów` : ''} open={sections.matchType} onToggle={() => toggle('matchType')} />
                {sections.matchType && <MatchTypeSection data={matchType} />}
            </div>

            {/* 4. N-gram */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={Hash} title="Analiza N-gramów" subtitle={ngram ? `${ngram.total} wyników` : ''} open={sections.ngram} onToggle={() => toggle('ngram')} />
                {sections.ngram && <NgramSection data={ngram} ngramSize={ngramSize} setNgramSize={setNgramSize} />}
            </div>

            {/* 5. RSA */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={FileText} title="Analiza reklam RSA" subtitle={rsa ? `${rsa.ad_groups.length} grup` : ''} open={sections.rsa} onToggle={() => toggle('rsa')} />
                {sections.rsa && <RsaSection data={rsa} />}
            </div>

            {/* 6. Landing Pages */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={Globe} title="Analiza stron docelowych" subtitle={landing ? `${landing.pages.length} URL` : ''} open={sections.landing} onToggle={() => toggle('landing')} />
                {sections.landing && <LandingPageSection data={landing} />}
            </div>

            {/* 7. Account Structure Audit */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={GitBranch} title="Audyt struktury konta" subtitle={structure?.issues?.length ? `${structure.issues.length} problemów` : 'OK'} open={sections.structure} onToggle={() => toggle('structure')} />
                {sections.structure && <AccountStructureSection data={structure} />}
            </div>

            {/* 8. Bidding Strategy Advisor */}
            <div className={CARD} style={SECTION_STYLE}>
                <SectionHeader icon={Target} title="Doradca strategii bidowania" subtitle={bidding ? `${bidding.changes_needed} do zmiany` : ''} open={sections.bidding} onToggle={() => toggle('bidding')} />
                {sections.bidding && <BiddingAdvisorSection data={bidding} />}
            </div>
        </div>
    )
}
