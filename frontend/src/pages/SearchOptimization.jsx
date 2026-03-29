import { useState, useEffect, useMemo } from 'react'
import { LineChart, Line, ResponsiveContainer, XAxis, Tooltip, CartesianGrid, Legend } from 'recharts'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'
import EmptyState from '../components/EmptyState'
import { ErrorMessage } from '../components/UI'
import {
    getDayparting, getRsaAnalysis, getNgramAnalysis,
    getMatchTypeAnalysis, getLandingPages, getWastedSpend,
    getAccountStructure, getBiddingAdvisor, getHourlyDayparting,
    getConversionHealth, getAdGroupHealth, getSmartBiddingHealth,
    getParetoAnalysis, getScalingOpportunities,
    getTargetVsActual, getBidStrategyReport, getLearningStatus,
    getPortfolioHealth, getConversionQuality, getDemographics,
    getPmaxChannels, getPmaxChannelTrends, getAssetGroupPerformance, getPmaxSearchThemes,
    getAudiencePerformance, getMissingExtensions, getExtensionPerformance,
    getPmaxSearchCannibalization,
    getAuctionInsights,
    getShoppingProductGroups,
    getPlacementPerformance,
    getBidModifiers,
    getTopicPerformance,
    getGoogleRecommendations,
    getConversionValueRules,
    getOfflineConversions,
    getAudiencesList,
    addNegativeKeyword,
    addPlacementExclusion,
} from '../api'
import {
    Loader2, CalendarDays, FileText, Hash, Layers, Globe, AlertTriangle,
    ChevronDown, ChevronRight, ExternalLink, TrendingDown, TrendingUp,
    GitBranch, Target, Clock, Users, Zap, BarChart3, Activity,
    Crosshair, GraduationCap, Briefcase, ShieldCheck, PieChart,
    Radio, Box, Search, Headphones, Link2, Star, Shuffle, Settings2,
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
function WastedSpendSection({ data, clientId, showToast }) {
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
                                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.text}</span>
                                <div className="flex items-center gap-2">
                                    <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#F87171' }}>{item.cost_usd.toFixed(2)} zł</span>
                                    {cat === 'search_terms' && clientId && (
                                        <button
                                            onClick={() => {
                                                addNegativeKeyword({ client_id: clientId, text: item.text, match_type: 'EXACT', scope: 'CAMPAIGN' })
                                                    .then(() => showToast?.(`Dodano negatyw: ${item.text}`, 'success'))
                                                    .catch(() => showToast?.(`Błąd dodawania: ${item.text}`, 'error'))
                                            }}
                                            style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', color: '#F87171', cursor: 'pointer' }}
                                        >
                                            Wyklucz
                                        </button>
                                    )}
                                </div>
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
                            <td style={TD}>{mt.clicks.toLocaleString('pl-PL')}</td>
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
                                <td style={TD}>{ng.clicks.toLocaleString('pl-PL')}</td>
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
                            <td style={TD}>{p.clicks.toLocaleString('pl-PL')}</td>
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
                                <td style={TD}>{h.clicks.toLocaleString('pl-PL')}</td>
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
// 10. AD GROUP HEALTH (GAP 8)
// ─────────────────────────────────────────────────────────
function AdGroupHealthSection({ data }) {
    if (!data?.details?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Wszystkie grupy reklam wyglądają dobrze.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                {data.issues.map((iss, i) => (
                    <MetricPill key={i} label={iss.type === 'no_ads' ? 'Brak reklam' : iss.type === 'single_ad' ? '1 reklama' : iss.type === 'too_many_keywords' ? 'Za dużo KW' : iss.type === 'too_few_keywords' ? 'Za mało KW' : 'Brak konw.'}
                        value={iss.count} color={iss.severity === 'HIGH' ? '#F87171' : iss.severity === 'MEDIUM' ? '#FBBF24' : '#4F8EF7'} />
                ))}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa reklam', 'Kampania', 'Reklamy', 'Słowa', 'Koszt', 'Konw.', 'Problemy'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa reklam' || h === 'Kampania' || h === 'Problemy' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.details.map((d, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: d.issues.length >= 2 ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.ad_group_name}</td>
                            <td style={{ ...TD_DIM, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.ads_count < 2 ? '#F87171' : '#4ADE80' }}>{d.ads_count}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.keywords_count > 30 || d.keywords_count < 2 ? '#FBBF24' : 'rgba(255,255,255,0.8)' }}>{d.keywords_count}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${d.cost_usd}</td>
                            <td style={{ ...TD, textAlign: 'right', color: d.conversions === 0 && d.cost_usd >= 50 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{d.conversions}</td>
                            <td style={{ ...TD_DIM, textAlign: 'left', fontSize: 11 }}>{d.issues.join(', ')}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 11. SMART BIDDING HEALTH (GAP 1B)
// ─────────────────────────────────────────────────────────
function SmartBiddingHealthSection({ data }) {
    if (!data?.campaigns?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak kampanii Smart Bidding lub wszystkie zdrowe.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Zdrowe" value={data.summary?.healthy || 0} color="#4ADE80" />
                <MetricPill label="Niski wolumen" value={data.summary?.low_volume || 0} color="#FBBF24" />
                <MetricPill label="Krytyczne" value={data.summary?.critical || 0} color="#F87171" />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Strategia', 'Konw. / 30d', 'Min.', 'Status'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.campaigns.map((c, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: c.status === 'CRITICAL' ? 'rgba(248,113,113,0.04)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.bidding_strategy}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: c.status === 'HEALTHY' ? '#4ADE80' : c.status === 'CRITICAL' ? '#F87171' : '#FBBF24' }}>{c.conversions_30d?.toFixed(1)}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.min_recommended}</td>
                            <td style={{ ...TD, textAlign: 'right', fontFamily: 'inherit' }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                    background: c.status === 'HEALTHY' ? 'rgba(74,222,128,0.1)' : c.status === 'CRITICAL' ? 'rgba(248,113,113,0.1)' : 'rgba(251,191,36,0.1)',
                                    color: c.status === 'HEALTHY' ? '#4ADE80' : c.status === 'CRITICAL' ? '#F87171' : '#FBBF24',
                                    border: `1px solid ${c.status === 'HEALTHY' ? 'rgba(74,222,128,0.2)' : c.status === 'CRITICAL' ? 'rgba(248,113,113,0.2)' : 'rgba(251,191,36,0.2)'}`,
                                }}>{c.status === 'HEALTHY' ? 'Zdrowa' : c.status === 'CRITICAL' ? 'Krytyczna' : 'Niski wolumen'}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 12. PARETO 80/20 (GAP 7A)
// ─────────────────────────────────────────────────────────
function ParetoSection({ data }) {
    if (!data?.campaign_pareto?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych do analizy Pareto.</div>
    const { campaign_pareto, summary } = data
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {summary?.campaign_concentration && (
                <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(79,142,247,0.08)', border: '1px solid rgba(79,142,247,0.15)', marginBottom: 16, fontSize: 12, color: '#4F8EF7' }}>
                    {summary.campaign_concentration}
                </div>
            )}
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Wartość', '% total', 'Kumulat.', 'Koszt', 'Konw.', 'Typ'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {campaign_pareto.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: item.tag === 'HERO' ? 'rgba(74,222,128,0.03)' : 'transparent' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.conv_value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: item.tag === 'HERO' ? '#4ADE80' : 'rgba(255,255,255,0.5)' }}>{item.pct_of_total?.toFixed(1)}%</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.cumulative_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${item.cost_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{item.conversions?.toFixed(1)}</td>
                            <td style={{ ...TD, textAlign: 'right', fontFamily: 'inherit' }}>
                                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
                                    background: item.tag === 'HERO' ? 'rgba(74,222,128,0.1)' : 'rgba(255,255,255,0.05)',
                                    color: item.tag === 'HERO' ? '#4ADE80' : 'rgba(255,255,255,0.4)',
                                    border: `1px solid ${item.tag === 'HERO' ? 'rgba(74,222,128,0.2)' : 'rgba(255,255,255,0.08)'}`,
                                }}>{item.tag === 'HERO' ? 'Hero' : 'Tail'}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 13. SCALING OPPORTUNITIES (GAP 7B)
// ─────────────────────────────────────────────────────────
function ScalingSection({ data }) {
    if (!data?.opportunities?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak okazji do skalowania.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Wartość', '% konta', 'Lost IS (budget)', 'Lost IS (rank)', 'Potencjał'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.opportunities.map((o, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>${o.value_usd?.toFixed(0)}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{o.value_pct?.toFixed(1)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_budget_is > 20 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{o.lost_budget_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: o.lost_rank_is > 20 ? '#FBBF24' : 'rgba(255,255,255,0.8)' }}>{o.lost_rank_is?.toFixed(0)}%</td>
                            <td style={{ ...TD, textAlign: 'right', fontWeight: 600, color: '#4ADE80' }}>~${o.incremental_value_est?.toFixed(0)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 14. TARGET VS ACTUAL (GAP 1D)
// ─────────────────────────────────────────────────────────
function TargetVsActualSection({ data }) {
    if (!data?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak kampanii Smart Bidding z celami.</div>
    const statusColor = { ON_TARGET: '#4ADE80', OVER_TARGET: '#F87171', UNDER_TARGET: '#FBBF24', NO_TARGET: 'rgba(255,255,255,0.4)' }
    const statusLabel = { ON_TARGET: 'W celu', OVER_TARGET: 'Powyżej', UNDER_TARGET: 'Poniżej', NO_TARGET: 'Brak celu' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Strategia', 'Cel', 'Aktualny', 'Odchylenie', 'Status'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.items.map((item, i) => {
                        const isCpa = item.bidding_strategy?.includes('CPA') || item.bidding_strategy === 'MAXIMIZE_CONVERSIONS'
                        const target = isCpa ? (item.target_cpa_usd ? `$${item.target_cpa_usd}` : '—') : (item.target_roas ? `${item.target_roas}x` : '—')
                        const actual = isCpa ? (item.actual_cpa_usd ? `$${item.actual_cpa_usd}` : '—') : (item.actual_roas ? `${item.actual_roas}x` : '—')
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.campaign_name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.bidding_strategy}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{target}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{actual}</td>
                                <td style={{ ...TD, textAlign: 'right', color: statusColor[item.status], fontWeight: 600 }}>{item.deviation_pct != null ? `${item.deviation_pct > 0 ? '+' : ''}${item.deviation_pct}%` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}><span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, color: statusColor[item.status], background: `${statusColor[item.status]}15` }}>{statusLabel[item.status]}</span></td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 15. LEARNING STATUS (GAP 1A)
// ─────────────────────────────────────────────────────────
function LearningStatusSection({ data }) {
    if (!data?.items?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak kampanii Smart Bidding.</div>
    const statusColor = { STABLE: '#4ADE80', LEARNING: '#FBBF24', EXTENDED_LEARNING: '#F87171', STUCK_LEARNING: '#F87171' }
    const statusLabel = { STABLE: 'Stabilna', LEARNING: 'Nauka', EXTENDED_LEARNING: 'Przedłużona', STUCK_LEARNING: 'Zablokowana' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Smart Bidding" value={data.total_smart_bidding} />
                <MetricPill label="W nauce" value={data.learning_count} color={data.learning_count > 0 ? '#FBBF24' : '#4ADE80'} />
                <MetricPill label="Zablokowane" value={data.stuck_count} color={data.stuck_count > 0 ? '#F87171' : '#4ADE80'} />
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Strategia', 'Status', 'Dni w nauce'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.items.map((item, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.campaign_name}</td>
                            <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.bidding_strategy}</td>
                            <td style={{ ...TD, textAlign: 'right' }}><span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, color: statusColor[item.status], background: `${statusColor[item.status]}15` }}>{statusLabel[item.status]}</span></td>
                            <td style={{ ...TD, textAlign: 'right' }}>{item.days_in_learning ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 16. PORTFOLIO HEALTH (GAP 1E)
// ─────────────────────────────────────────────────────────
function PortfolioHealthSection({ data }) {
    if (!data?.portfolios?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak portfelowych strategii.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.portfolios.map((p, pi) => (
                <div key={pi} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', marginBottom: 8 }}>Portfolio {p.portfolio_id} — {p.bidding_strategy} ({p.campaign_count} kampanii)</div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                        <MetricPill label="Koszt" value={`$${p.total_cost_usd}`} />
                        <MetricPill label="Konwersje" value={p.total_conversions} />
                        <MetricPill label="Wartość" value={`$${p.total_value_usd}`} />
                    </div>
                    {p.issues?.length > 0 && p.issues.map((iss, ii) => (
                        <div key={ii} style={{ fontSize: 11, color: iss.severity === 'HIGH' ? '#F87171' : '#FBBF24', marginBottom: 4 }}>⚠ {iss.detail}</div>
                    ))}
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                            {['Kampania', 'Koszt', 'Konwersje', 'Wartość', '% wydatków'].map(h =>
                                <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'right' }}>{h}</th>
                            )}
                        </tr></thead>
                        <tbody>
                            {p.campaigns.map((c, ci) => (
                                <tr key={ci} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{c.campaign_name}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.cost_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.conversions}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>${c.value_usd}</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.spend_share_pct > 70 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{c.spend_share_pct}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 17. CONVERSION QUALITY AUDIT (GAP 2A-2D)
// ─────────────────────────────────────────────────────────
function ConversionQualitySection({ data }) {
    if (!data) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych konwersji.</div>
    const scoreColor = data.quality_score >= 80 ? '#4ADE80' : data.quality_score >= 50 ? '#FBBF24' : '#F87171'
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                <MetricPill label="Quality Score" value={data.quality_score} color={scoreColor} />
                <MetricPill label="Akcji konwersji" value={data.total_actions} />
                <MetricPill label="Primary" value={data.primary_count} />
            </div>
            {data.issues?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    {data.issues.map((iss, i) => (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: iss.severity === 'HIGH' ? 'rgba(248,113,113,0.08)' : iss.severity === 'MEDIUM' ? 'rgba(251,191,36,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${iss.severity === 'HIGH' ? 'rgba(248,113,113,0.2)' : iss.severity === 'MEDIUM' ? 'rgba(251,191,36,0.2)' : 'rgba(255,255,255,0.07)'}` }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: iss.severity === 'HIGH' ? '#F87171' : iss.severity === 'MEDIUM' ? '#FBBF24' : '#F0F0F0' }}>{iss.type}</div>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 }}>{iss.detail}</div>
                            {iss.affected?.length > 0 && <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{iss.affected.join(', ')}</div>}
                        </div>
                    ))}
                </div>
            )}
            {data.actions?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Nazwa', 'Kategoria', 'Primary', 'Counting', 'Wartość dom.', 'Atrybucja', 'Lookback'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Nazwa' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.actions.map((a, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.category}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.primary_for_goal ? '✓' : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.counting_type || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.value_default != null ? `$${a.value_default}` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{a.attribution_model || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.lookback_days ?? '—'}d</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 18. DEMOGRAPHICS (GAP 4A)
// ─────────────────────────────────────────────────────────
function DemographicsSection({ data }) {
    if (!data) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych demograficznych.</div>
    const BreakdownTable = ({ items, title }) => {
        if (!items?.length) return null
        return (
            <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.5)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</div>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Segment', 'Kliknięcia', 'Koszt', 'Konwersje', 'CPA', 'ROAS', '% kosztów'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Segment' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {items.map((item, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{item.segment}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.clicks?.toLocaleString('pl-PL')}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>${item.cost_usd}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.conversions}</td>
                                <td style={{ ...TD, textAlign: 'right', color: item.cpa_usd && data.avg_cpa_usd && item.cpa_usd > data.avg_cpa_usd * 2 ? '#F87171' : 'rgba(255,255,255,0.8)' }}>{item.cpa_usd != null ? `$${item.cpa_usd}` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{item.roas != null ? `${item.roas}x` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{item.cost_share_pct}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        )
    }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.anomalies?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    {data.anomalies.map((a, i) => (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)' }}>
                            <span style={{ fontSize: 12, fontWeight: 600, color: '#F87171' }}>Anomalia: </span>
                            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>{a.segment} — CPA ${a.cpa_usd} ({a.multiplier}x średniej ${a.avg_cpa_usd})</span>
                        </div>
                    ))}
                </div>
            )}
            <BreakdownTable items={data.age_breakdown} title="Przedziały wiekowe" />
            <BreakdownTable items={data.gender_breakdown} title="Płeć" />
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 19. PMAX CHANNEL BREAKDOWN (GAP 3A)
// ─────────────────────────────────────────────────────────
const CHANNEL_COLORS = {
    SEARCH: '#4F8EF7', DISPLAY: '#7B5CE0', VIDEO: '#FBBF24',
    SHOPPING: '#4ADE80', DISCOVER: '#F472B6', CROSS_NETWORK: '#94A3B8',
}
function PmaxChannelsSection({ data, trends }) {
    const [view, setView] = useState('table')
    if (!data?.channels?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o kanalach PMax.</div>
    const hasTrends = trends?.trends?.length > 0
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {hasTrends && (
                <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
                    {[{ key: 'table', label: 'Tabela' }, { key: 'trend', label: 'Trend' }].map(t => (
                        <button key={t.key} onClick={() => setView(t.key)} style={{
                            padding: '4px 12px', borderRadius: 999, fontSize: 11, fontWeight: 500, cursor: 'pointer',
                            background: view === t.key ? 'rgba(79,142,247,0.12)' : 'transparent',
                            color: view === t.key ? '#4F8EF7' : 'rgba(255,255,255,0.4)',
                            border: view === t.key ? '1px solid rgba(79,142,247,0.3)' : '1px solid rgba(255,255,255,0.08)',
                        }}>{t.label}</button>
                    ))}
                </div>
            )}
            {view === 'table' ? (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Kanal', 'Klikniecia', 'Koszt', 'Konwersje', '% kosztow', '% konwersji'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Kanal' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.channels.map((ch, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{ch.network_type}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ch.clicks?.toLocaleString('pl-PL')}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{(ch.cost_micros / 1e6).toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ch.conversions?.toFixed(1)}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{ch.cost_share_pct?.toFixed(1)}%</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', color: ch.cost_share_pct > 60 && ch.conv_share_pct < 30 ? '#F87171' : undefined }}>{ch.conv_share_pct?.toFixed(1)}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
                        {trends.channels.map(ch => (
                            <div key={ch} className="flex items-center gap-1" style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>
                                <div style={{ width: 8, height: 8, borderRadius: 2, background: CHANNEL_COLORS[ch] || '#64748B' }} />
                                {ch}
                            </div>
                        ))}
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={trends.trends} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis
                                dataKey="date"
                                tickFormatter={v => { const d = new Date(v); return `${d.getDate()}.${(d.getMonth()+1).toString().padStart(2,'0')}` }}
                                tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.2)' }}
                                axisLine={false} tickLine={false}
                                interval="preserveStartEnd"
                            />
                            <Tooltip
                                contentStyle={{ background: '#1a1d24', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, fontSize: 11 }}
                                labelFormatter={v => { const d = new Date(v); return `${d.getDate()}.${(d.getMonth()+1).toString().padStart(2,'0')}` }}
                            />
                            {trends.channels.map(ch => (
                                <Line key={ch} type="monotone" dataKey={`${ch}_cost`} stroke={CHANNEL_COLORS[ch] || '#64748B'} strokeWidth={1.5} dot={false} name={`${ch} koszt`} />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 20. ASSET GROUP PERFORMANCE (GAP 3B)
// ─────────────────────────────────────────────────────────
const AD_STRENGTH_COLOR = { EXCELLENT: '#4ADE80', GOOD: '#4F8EF7', AVERAGE: '#FBBF24', POOR: '#F87171' }
function AssetGroupsSection({ data }) {
    if (!data?.asset_groups?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak grup zasobow PMax.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa zasobow', 'Sila reklamy', 'Koszt', 'Konwersje', 'CPA', 'ROAS', 'Zasoby'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa zasobow' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.asset_groups.map((ag, i) => {
                        const cost = ag.total_cost_micros / 1e6
                        const cpa = ag.total_conversions > 0 ? cost / ag.total_conversions : null
                        const roas = cost > 0 ? (ag.total_conversion_value_micros || 0) / 1e6 / cost : null
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{ag.name}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>
                                    <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, background: `${AD_STRENGTH_COLOR[ag.ad_strength] || 'rgba(255,255,255,0.1)'}22`, color: AD_STRENGTH_COLOR[ag.ad_strength] || 'rgba(255,255,255,0.5)' }}>{ag.ad_strength || '—'}</span>
                                </td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cost.toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{ag.total_conversions?.toFixed(1)}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cpa != null ? `${cpa.toFixed(0)} zl` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{roas != null ? `${roas.toFixed(2)}x` : '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{ag.asset_count || 0}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 21. PMAX SEARCH THEMES (GAP 3C)
// ─────────────────────────────────────────────────────────
function SearchThemesSection({ data }) {
    if (!data?.asset_groups?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak sygnalow PMax.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {data.asset_groups.map((ag, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0', marginBottom: 6 }}>{ag.name}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {ag.search_themes?.map((t, j) => (
                            <span key={j} style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(79,142,247,0.1)', border: '1px solid rgba(79,142,247,0.2)', color: '#4F8EF7' }}>{t}</span>
                        ))}
                        {ag.audience_signals?.map((a, j) => (
                            <span key={`a-${j}`} style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, background: 'rgba(123,92,224,0.1)', border: '1px solid rgba(123,92,224,0.2)', color: '#7B5CE0' }}>{a.name} ({a.type})</span>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 22. AUDIENCE PERFORMANCE (GAP 4B)
// ─────────────────────────────────────────────────────────
function AudiencePerfSection({ data }) {
    if (!data?.audiences?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o grupach odbiorcow.</div>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Grupa odbiorcow', 'Typ', 'Koszt', 'Konwersje', 'CPA', 'ROAS', 'Anomalia'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Grupa odbiorcow' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.audiences.map((a, i) => {
                        const cost = a.cost_micros / 1e6
                        const cpa = a.cpa_micros ? a.cpa_micros / 1e6 : null
                        return (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{a.audience_name || a.audience_resource_name}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.audience_type || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{cost.toFixed(0)} zl</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.conversions?.toFixed(1)}</td>
                                <td style={{ ...TD, textAlign: 'right', color: a.is_anomaly ? '#F87171' : undefined }}>{cpa != null ? `${cpa.toFixed(0)} zl` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.roas != null ? `${a.roas.toFixed(2)}x` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{a.is_anomaly ? <span style={{ color: '#F87171', fontWeight: 600 }}>TAK</span> : '—'}</td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 23. MISSING EXTENSIONS (GAP 5A)
// ─────────────────────────────────────────────────────────
function MissingExtSection({ data }) {
    if (!data?.campaigns?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o rozszerzeniach.</div>
    const Check = ({ ok }) => <span style={{ color: ok ? '#4ADE80' : '#F87171', fontWeight: 700, fontSize: 14 }}>{ok ? '\u2713' : '\u2717'}</span>
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Kampania', 'Sitelinks', 'Callouts', 'Snippets', 'Call', 'Score'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Kampania' ? 'left' : 'center' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.campaigns.map((c, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{c.campaign_name}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.sitelink_count >= 4} /> {c.sitelink_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.callout_count >= 4} /> {c.callout_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.snippet_count >= 1} /> {c.snippet_count}</td>
                            <td style={{ ...TD, textAlign: 'center' }}><Check ok={c.has_call} /></td>
                            <td style={{ ...TD, textAlign: 'center' }}>
                                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, background: c.extension_score >= 80 ? 'rgba(74,222,128,0.1)' : c.extension_score >= 50 ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)', color: c.extension_score >= 80 ? '#4ADE80' : c.extension_score >= 50 ? '#FBBF24' : '#F87171' }}>{c.extension_score}%</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// 24. EXTENSION PERFORMANCE (GAP 5B)
// ─────────────────────────────────────────────────────────
function ExtPerfSection({ data }) {
    if (!data?.by_type?.length) return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak danych o wydajnosci rozszerzen.</div>
    const PERF_COLOR = { BEST: '#4ADE80', GOOD: '#4F8EF7', LOW: '#F87171', LEARNING: '#FBBF24' }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['Typ rozszerzenia', 'Ilosc', 'Klikniecia', 'Wyswietlenia', 'CTR', 'BEST', 'GOOD', 'LOW'].map(h =>
                        <th key={h} style={{ ...TH, textAlign: h === 'Typ rozszerzenia' ? 'left' : 'right' }}>{h}</th>
                    )}
                </tr></thead>
                <tbody>
                    {data.by_type.map((t, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0' }}>{t.asset_type}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.count}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.total_clicks?.toLocaleString('pl-PL')}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.total_impressions?.toLocaleString('pl-PL')}</td>
                            <td style={{ ...TD, textAlign: 'right' }}>{t.avg_ctr?.toFixed(2)}%</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.BEST }}>{t.performance_labels?.BEST || 0}</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.GOOD }}>{t.performance_labels?.GOOD || 0}</td>
                            <td style={{ ...TD, textAlign: 'right', color: PERF_COLOR.LOW }}>{t.performance_labels?.LOW || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function PmaxCannibalizationSection({ data }) {
    if (!data?.overlapping_terms?.length && !data?.recommendations?.length) {
        return <div style={{ padding: '0 16px 16px', fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>Brak kanibalizacji PMax ↔ Search.</div>
    }
    const s = data.summary || {}
    const PRIO_COLORS = { high: { bg: 'rgba(248,113,113,0.1)', text: '#F87171' }, medium: { bg: 'rgba(251,191,36,0.1)', text: '#FBBF24' } }
    return (
        <div style={{ padding: '0 16px 16px' }}>
            {/* Summary cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
                {[
                    { label: 'Pokrywające się frazy', value: s.total_overlap, color: '#4F8EF7' },
                    { label: 'Koszt kanibalizacji', value: `${(s.overlap_cost_usd || 0).toFixed(0)} zł`, color: '#F87171' },
                    { label: 'Search lepszy', value: s.search_better_count, color: '#4ADE80' },
                    { label: 'PMax lepszy', value: s.pmax_better_count, color: '#7B5CE0' },
                ].map(c => (
                    <div key={c.label} style={{ padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, borderLeft: `3px solid ${c.color}` }}>
                        <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{c.label}</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: c.color, fontFamily: 'Syne' }}>{c.value}</div>
                    </div>
                ))}
            </div>

            {/* Recommendations */}
            {data.recommendations?.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                    {data.recommendations.map((r, i) => {
                        const pc = PRIO_COLORS[r.priority] || PRIO_COLORS.medium
                        return (
                            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px', marginBottom: 6, borderRadius: 8, background: pc.bg, border: `1px solid ${pc.text}20` }}>
                                <AlertTriangle size={13} style={{ color: pc.text, marginTop: 2, flexShrink: 0 }} />
                                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{r.message}</span>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Overlap table */}
            {data.overlapping_terms?.length > 0 && (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {['Fraza', 'Search klik.', 'Search koszt', 'Search CPA', 'PMax klik.', 'PMax koszt', 'PMax CPA', 'Zwycięzca'].map(h =>
                            <th key={h} style={{ ...TH, textAlign: h === 'Fraza' ? 'left' : 'right' }}>{h}</th>
                        )}
                    </tr></thead>
                    <tbody>
                        {data.overlapping_terms.map((t, i) => {
                            const winColor = t.winner === 'SEARCH' ? '#4ADE80' : t.winner === 'PMAX' ? '#7B5CE0' : 'rgba(255,255,255,0.3)'
                            const winLabel = t.winner === 'SEARCH' ? 'Search' : t.winner === 'PMAX' ? 'PMax' : 'Remis'
                            return (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontFamily: 'inherit', fontWeight: 500, color: '#F0F0F0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.search_term}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.search.clicks}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.search.cost_usd.toFixed(0)} zł</td>
                                    <td style={{ ...TD, textAlign: 'right', color: t.winner === 'SEARCH' ? '#4ADE80' : undefined }}>{t.search.cpa != null ? `${t.search.cpa.toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.pmax.clicks}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{t.pmax.cost_usd.toFixed(0)} zł</td>
                                    <td style={{ ...TD, textAlign: 'right', color: t.winner === 'PMAX' ? '#7B5CE0' : undefined }}>{t.pmax.cpa != null ? `${t.pmax.cpa.toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>
                                        <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 8px', borderRadius: 999, background: `${winColor}15`, color: winColor }}>{winLabel}</span>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </div>
    )
}

// ─────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────
export default function SearchOptimization() {
    const { selectedClientId, showToast } = useApp()
    const { allParams, days, setFilter } = useFilter()

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [sections, setSections] = useState({
        waste: true, dayparting: true, matchType: true,
        ngram: false, rsa: false, landing: false,
        hourly: false, structure: false, bidding: false,
        convHealth: false, adGroupHealth: false, smartBidding: false,
        pareto: false, scaling: false, targetVsActual: false,
        learningStatus: false, portfolioHealth: false,
        convQuality: false, demographics: false,
        pmaxChannels: false, assetGroups: false, searchThemes: false,
        pmaxCannibalization: false,
        auctionInsights: false,
        shoppingGroups: false,
        placementPerf: false,
        topicPerf: false,
        bidModifiers: false,
        googleRecs: false,
        convValueRules: false,
        offlineConversions: false,
        audiencesList: false,
        audiencePerf: false, missingExt: false, extPerf: false,
    })
    const [ngramSize, setNgramSize] = useState(1)
    const [activeSection, setActiveSection] = useState(null)

    const [waste, setWaste] = useState(null)
    const [daypart, setDaypart] = useState(null)
    const [matchType, setMatchType] = useState(null)
    const [ngram, setNgram] = useState(null)
    const [rsa, setRsa] = useState(null)
    const [landing, setLanding] = useState(null)
    const [hourly, setHourly] = useState(null)
    const [structure, setStructure] = useState(null)
    const [bidding, setBidding] = useState(null)
    const [convHealth, setConvHealth] = useState(null)
    const [adGroupHealth, setAdGroupHealth] = useState(null)
    const [smartBidding, setSmartBidding] = useState(null)
    const [pareto, setPareto] = useState(null)
    const [scaling, setScaling] = useState(null)
    const [targetVsActual, setTargetVsActual] = useState(null)
    const [learningStatus, setLearningStatus] = useState(null)
    const [portfolioHealth, setPortfolioHealth] = useState(null)
    const [convQuality, setConvQuality] = useState(null)
    const [demographics, setDemographics] = useState(null)
    const [pmaxChannels, setPmaxChannels] = useState(null)
    const [pmaxTrends, setPmaxTrends] = useState(null)
    const [assetGroups, setAssetGroups] = useState(null)
    const [searchThemes, setSearchThemes] = useState(null)
    const [pmaxCannibalization, setPmaxCannibalization] = useState(null)
    const [audiencePerf, setAudiencePerf] = useState(null)
    const [missingExt, setMissingExt] = useState(null)
    const [extPerf, setExtPerf] = useState(null)
    const [auctionData, setAuctionData] = useState(null)
    const [shoppingData, setShoppingData] = useState(null)
    const [placementData, setPlacementData] = useState(null)
    const [topicData, setTopicData] = useState(null)
    const [bidModData, setBidModData] = useState(null)
    const [googleRecsData, setGoogleRecsData] = useState(null)
    const [convValueRulesData, setConvValueRulesData] = useState(null)
    const [offlineConvData, setOfflineConvData] = useState(null)
    const [audiencesListData, setAudiencesListData] = useState(null)

    useEffect(() => {
        if (selectedClientId) loadAll()
    }, [selectedClientId, allParams])

    useEffect(() => {
        if (selectedClientId && sections.ngram) {
            getNgramAnalysis(selectedClientId, { ngram_size: ngramSize, ...allParams }).then(setNgram).catch(() => setNgram(null))
        }
    }, [ngramSize, selectedClientId, allParams])

    async function loadAll() {
        setLoading(true)
        setError(null)
        try {
            const _catch = (label) => (err) => { console.warn(`[SearchOptim] ${label}`, err); return null }
            const [w, dp, mt, ng, r, lp, hr, st, bd, ch, agh, sb, pa, sc, tva, ls, ph, cq, demo,
                   pch, ptrend, agp, sth, pcann, aud, mex, exp, auct, shopg, plc,
                   topd, bmod, grecs, cvr, oconv, audl] = await Promise.all([
                getWastedSpend(selectedClientId, allParams).catch(_catch('wasted-spend')),
                getDayparting(selectedClientId, allParams).catch(_catch('dayparting')),
                getMatchTypeAnalysis(selectedClientId, allParams).catch(_catch('match-type')),
                getNgramAnalysis(selectedClientId, { ngram_size: ngramSize, ...allParams }).catch(_catch('ngram')),
                getRsaAnalysis(selectedClientId, allParams).catch(_catch('rsa')),
                getLandingPages(selectedClientId, allParams).catch(_catch('landing-pages')),
                getHourlyDayparting(selectedClientId, allParams).catch(_catch('hourly-dayparting')),
                getAccountStructure(selectedClientId).catch(_catch('account-structure')),
                getBiddingAdvisor(selectedClientId, allParams).catch(_catch('bidding-advisor')),
                getConversionHealth(selectedClientId, allParams).catch(_catch('conversion-health')),
                getAdGroupHealth(selectedClientId, allParams).catch(_catch('ad-group-health')),
                getSmartBiddingHealth(selectedClientId, allParams).catch(_catch('smart-bidding')),
                getParetoAnalysis(selectedClientId, allParams).catch(_catch('pareto')),
                getScalingOpportunities(selectedClientId, allParams).catch(_catch('scaling')),
                getTargetVsActual(selectedClientId, allParams).catch(_catch('target-vs-actual')),
                getLearningStatus(selectedClientId).catch(_catch('learning-status')),
                getPortfolioHealth(selectedClientId, allParams).catch(_catch('portfolio-health')),
                getConversionQuality(selectedClientId).catch(_catch('conversion-quality')),
                getDemographics(selectedClientId, allParams).catch(_catch('demographics')),
                getPmaxChannels(selectedClientId, allParams).catch(_catch('pmax-channels')),
                getPmaxChannelTrends(selectedClientId, allParams).catch(_catch('pmax-channel-trends')),
                getAssetGroupPerformance(selectedClientId, allParams).catch(_catch('asset-group')),
                getPmaxSearchThemes(selectedClientId).catch(_catch('pmax-themes')),
                getPmaxSearchCannibalization(selectedClientId, allParams).catch(_catch('pmax-cannibalization')),
                getAudiencePerformance(selectedClientId, allParams).catch(_catch('audience')),
                getMissingExtensions(selectedClientId, allParams).catch(_catch('missing-ext')),
                getExtensionPerformance(selectedClientId, allParams).catch(_catch('ext-performance')),
                getAuctionInsights(selectedClientId, allParams).catch(_catch('auction-insights')),
                getShoppingProductGroups(selectedClientId).catch(_catch('shopping-groups')),
                getPlacementPerformance(selectedClientId, allParams).catch(_catch('placements')),
                getTopicPerformance(selectedClientId, allParams).catch(_catch('topics')),
                getBidModifiers(selectedClientId).catch(_catch('bid-modifiers')),
                getGoogleRecommendations(selectedClientId).catch(_catch('google-recs')),
                getConversionValueRules(selectedClientId).catch(_catch('conv-value-rules')),
                getOfflineConversions(selectedClientId).catch(_catch('offline-conversions')),
                getAudiencesList(selectedClientId).catch(_catch('audiences-list')),
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
            setConvHealth(ch)
            setAdGroupHealth(agh)
            setSmartBidding(sb)
            setPareto(pa)
            setScaling(sc)
            setTargetVsActual(tva)
            setLearningStatus(ls)
            setPortfolioHealth(ph)
            setConvQuality(cq)
            setDemographics(demo)
            setPmaxChannels(pch)
            setPmaxTrends(ptrend)
            setAssetGroups(agp)
            setSearchThemes(sth)
            setPmaxCannibalization(pcann)
            setAudiencePerf(aud)
            setMissingExt(mex)
            setExtPerf(exp)
            setAuctionData(auct)
            setShoppingData(shopg)
            setPlacementData(plc)
            setTopicData(topd)
            setBidModData(bmod)
            setGoogleRecsData(grecs)
            setConvValueRulesData(cvr)
            setOfflineConvData(oconv)
            setAudiencesListData(audl)
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

    // ── Card definitions for bento grid ──
    const cards = [
        { key: 'waste', title: 'Zmarnowany budżet', icon: AlertTriangle, cat: 'budget', types: ['SEARCH','PMAX','SHOPPING'],
          value: waste ? `${waste.total_waste_usd?.toFixed(0) || 0} zł` : '—', sub: waste ? `${waste.waste_pct}% spend · ${waste.categories?.length || 0} kategorii` : '',
          status: waste ? (waste.waste_pct > 3 ? 'danger' : waste.waste_pct > 1 ? 'warning' : 'ok') : 'neutral' },
        { key: 'bidding', title: 'Strategia bidowania', icon: Target, cat: 'budget', types: ['SEARCH','PMAX'],
          value: bidding ? `${bidding.changes_needed || 0} zmian` : '—', sub: bidding ? `${bidding.total_campaigns || 0} kampanii` : '',
          status: bidding ? (bidding.changes_needed > 2 ? 'danger' : bidding.changes_needed > 0 ? 'warning' : 'ok') : 'neutral' },
        { key: 'convHealth', title: 'Zdrowie konwersji', icon: AlertTriangle, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING','DISPLAY','VIDEO'],
          value: convHealth ? `${convHealth.score}/100` : '—', sub: convHealth ? `${convHealth.total_campaigns} kampanii` : '',
          status: convHealth ? (convHealth.score >= 80 ? 'ok' : convHealth.score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'convQuality', title: 'Jakość konwersji', icon: ShieldCheck, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING'],
          value: convQuality ? `${convQuality.quality_score}/100` : '—', sub: convQuality ? `${convQuality.issues?.length || 0} problemów` : '',
          status: convQuality ? (convQuality.quality_score >= 80 ? 'ok' : convQuality.quality_score >= 50 ? 'warning' : 'danger') : 'neutral' },
        { key: 'targetVsActual', title: 'Target vs Rzeczywistość', icon: Crosshair, cat: 'budget', types: ['SEARCH','PMAX'],
          value: targetVsActual ? `${targetVsActual.items?.length || 0} kampanii` : '—', sub: 'Smart Bidding',
          status: 'info' },
        { key: 'smartBidding', title: 'Smart Bidding', icon: Zap, cat: 'budget', types: ['SEARCH','PMAX'],
          value: smartBidding ? `${smartBidding.summary?.critical || 0} kryt.` : '—', sub: smartBidding ? `${smartBidding.summary?.low_volume || 0} niski wolumen` : '',
          status: smartBidding?.summary?.critical > 0 ? 'danger' : smartBidding?.summary?.low_volume > 0 ? 'warning' : 'ok' },
        { key: 'matchType', title: 'Dopasowania', icon: Layers, cat: 'search', types: ['SEARCH'],
          value: matchType ? `${matchType.match_types?.length || 0} typów` : '—', sub: matchType ? `${matchType.total_keywords || 0} keywords` : '',
          status: 'info' },
        { key: 'dayparting', title: 'Harmonogram tygodnia', icon: CalendarDays, cat: 'search', types: ['SEARCH'],
          value: daypart ? 'Aktywne' : '—', sub: 'Analiza dni tygodnia',
          status: 'info' },
        { key: 'hourly', title: 'Harmonogram godzinowy', icon: Clock, cat: 'search', types: ['SEARCH'],
          value: hourly ? 'Heatmapa' : '—', sub: '0-23h',
          status: 'info' },
        { key: 'ngram', title: 'N-gramy', icon: Hash, cat: 'search', types: ['SEARCH'],
          value: ngram ? `${ngram.total} wyników` : '—', sub: `${ngramSize}-gramy`,
          status: 'info' },
        { key: 'rsa', title: 'Reklamy RSA', icon: FileText, cat: 'search', types: ['SEARCH'],
          value: rsa ? `${rsa.ad_groups?.length || 0} grup` : '—', sub: 'Analiza wariantów',
          status: 'info' },
        { key: 'landing', title: 'Strony docelowe', icon: Globe, cat: 'search', types: ['SEARCH','PMAX'],
          value: landing ? `${landing.pages?.length || 0} URL` : '—', sub: 'Wydajność landing pages',
          status: 'info' },
        { key: 'structure', title: 'Struktura konta', icon: GitBranch, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING'],
          value: structure?.issues?.length ? `${structure.issues.length} problemów` : 'OK', sub: 'Audyt struktury',
          status: structure?.issues?.length > 0 ? 'warning' : 'ok' },
        { key: 'adGroupHealth', title: 'Zdrowie grup reklam', icon: Users, cat: 'quality', types: ['SEARCH'],
          value: adGroupHealth ? `${adGroupHealth.details?.length || 0} prob.` : '—', sub: adGroupHealth ? `z ${adGroupHealth.total_ad_groups} grup` : '',
          status: adGroupHealth?.details?.length > 0 ? 'warning' : 'ok' },
        { key: 'pareto', title: 'Pareto 80/20', icon: BarChart3, cat: 'search', types: ['SEARCH','PMAX'],
          value: pareto ? `${pareto.campaign_pareto?.top_campaigns_for_80pct || '?'} kamp.` : '—', sub: '80% wartości',
          status: 'info' },
        { key: 'scaling', title: 'Okazje do skalowania', icon: Activity, cat: 'search', types: ['SEARCH','PMAX'],
          value: scaling ? `${scaling.opportunities?.length || 0} kampanii` : '—', sub: 'Potencjał wzrostu',
          status: scaling?.opportunities?.length > 0 ? 'ok' : 'neutral' },
        { key: 'learningStatus', title: 'Status nauki', icon: GraduationCap, cat: 'budget', types: ['SEARCH','PMAX'],
          value: learningStatus ? `${learningStatus.learning_count || 0} w nauce` : '—', sub: learningStatus ? `z ${learningStatus.total_smart_bidding || 0}` : '',
          status: learningStatus?.learning_count > 0 ? 'warning' : 'ok' },
        { key: 'portfolioHealth', title: 'Strategie portfelowe', icon: Briefcase, cat: 'budget', types: ['SEARCH','PMAX'],
          value: portfolioHealth ? `${portfolioHealth.total_portfolios || 0} portfeli` : '—', sub: 'Portfolio bidding',
          status: 'info' },
        { key: 'demographics', title: 'Demografia', icon: PieChart, cat: 'search', types: ['SEARCH','DISPLAY','VIDEO'],
          value: demographics ? `${demographics.anomalies?.length || 0} anomalii` : '—', sub: 'CPA per segment',
          status: demographics?.anomalies?.length > 0 ? 'warning' : 'ok' },
        { key: 'pmaxChannels', title: 'Kanały PMax', icon: Radio, cat: 'pmax', types: ['PMAX'],
          value: pmaxChannels?.channels ? `${pmaxChannels.channels.length} kanałów` : '—', sub: 'Rozkład budżetu',
          status: 'info' },
        { key: 'assetGroups', title: 'Grupy zasobów PMax', icon: Box, cat: 'pmax', types: ['PMAX'],
          value: assetGroups?.groups ? `${assetGroups.groups.length} grup` : '—', sub: 'Asset groups',
          status: 'info' },
        { key: 'searchThemes', title: 'Tematy PMax', icon: Search, cat: 'pmax', types: ['PMAX'],
          value: 'Sygnały', sub: 'Tematy i odbiorcy',
          status: 'info' },
        { key: 'pmaxCannibalization', title: 'Kanibalizacja PMax↔Search', icon: Shuffle, cat: 'pmax', types: ['PMAX','SEARCH'],
          value: pmaxCannibalization?.summary ? `${pmaxCannibalization.summary.total_overlap} fraz` : '—', sub: 'Pokrywające się frazy',
          status: pmaxCannibalization?.summary?.total_overlap > 0 ? 'warning' : 'ok' },
        { key: 'auctionInsights', title: 'Auction Insights', icon: Crosshair, cat: 'cross', types: ['SEARCH'],
          value: auctionData?.total_competitors ? `${auctionData.total_competitors} konk.` : '—', sub: 'Widoczność konkurencji',
          status: 'info' },
        { key: 'shoppingGroups', title: 'Grupy produktów', icon: Box, cat: 'cross', types: ['SHOPPING'],
          value: shoppingData?.groups ? `${shoppingData.groups.length} grup` : '—', sub: 'Shopping hierarchy',
          status: 'info' },
        { key: 'placementPerf', title: 'Miejsca docelowe', icon: Globe, cat: 'cross', types: ['DISPLAY','VIDEO'],
          value: placementData?.placements ? `${placementData.placements.length} miejsc` : '—', sub: 'Display/Video placements',
          status: 'info' },
        { key: 'topicPerf', title: 'Tematy Display/Video', icon: Layers, cat: 'cross', types: ['DISPLAY','VIDEO'],
          value: topicData?.topics ? `${topicData.topics.length} tematów` : '—', sub: 'Wydajność tematów',
          status: 'info' },
        { key: 'bidModifiers', title: 'Modyfikatory stawek', icon: Settings2, cat: 'budget', types: ['SEARCH','DISPLAY','VIDEO'],
          value: bidModData?.modifiers ? `${bidModData.modifiers.length} aktywnych` : '—', sub: 'Urządzenia, lokalizacje, harmonogram',
          status: 'info' },
        { key: 'googleRecs', title: 'Rekomendacje Google', icon: Star, cat: 'quality', types: ['SEARCH','PMAX','SHOPPING','DISPLAY','VIDEO'],
          value: googleRecsData?.recommendations ? `${googleRecsData.recommendations.length} nowych` : '—', sub: 'Natywne sugestie Google',
          status: googleRecsData?.recommendations?.length > 3 ? 'warning' : 'info' },
        { key: 'convValueRules', title: 'Reguły wartości', icon: Settings2, cat: 'cross', types: ['SEARCH','PMAX','SHOPPING'],
          value: convValueRulesData?.rules ? `${convValueRulesData.rules.length} reguł` : '—', sub: 'Value rules',
          status: 'info' },
        { key: 'offlineConversions', title: 'Konwersje offline', icon: Target, cat: 'cross', types: ['SEARCH','PMAX'],
          value: offlineConvData?.total ? `${offlineConvData.total} uploadów` : '—', sub: 'GCLID imports',
          status: 'info' },
        { key: 'audiencesList', title: 'Lista odbiorców', icon: Users, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PMAX'],
          value: audiencesListData?.total ? `${audiencesListData.total} segm.` : '—', sub: 'Remarketing, in-market, affinity',
          status: 'info' },
        { key: 'audiencePerf', title: 'Wydajność odbiorców', icon: Headphones, cat: 'cross', types: ['SEARCH','DISPLAY','VIDEO','PMAX'],
          value: audiencePerf?.audiences ? `${audiencePerf.audiences.length} segm.` : '—', sub: 'Performance per audience',
          status: 'info' },
        { key: 'missingExt', title: 'Brakujące rozszerzenia', icon: Link2, cat: 'quality', types: ['SEARCH'],
          value: missingExt?.campaigns ? `${missingExt.campaigns.length} kamp.` : '—', sub: 'Kampanie bez rozszerzeń',
          status: missingExt?.campaigns?.length > 0 ? 'warning' : 'ok' },
        { key: 'extPerf', title: 'Wydajność rozszerzeń', icon: Star, cat: 'quality', types: ['SEARCH'],
          value: extPerf?.types ? `${extPerf.types.length} typów` : '—', sub: 'Extension performance',
          status: 'info' },
    ]

    // ── Status colors ──
    const STATUS_COLORS = {
        danger:  { border: 'rgba(248,113,113,0.3)', dot: '#F87171', valueFill: '#F87171' },
        warning: { border: 'rgba(251,191,36,0.3)', dot: '#FBBF24', valueFill: '#FBBF24' },
        ok:      { border: 'rgba(74,222,128,0.3)', dot: '#4ADE80', valueFill: '#4ADE80' },
        info:    { border: 'rgba(79,142,247,0.2)', dot: '#4F8EF7', valueFill: '#4F8EF7' },
        neutral: { border: 'rgba(255,255,255,0.07)', dot: 'rgba(255,255,255,0.3)', valueFill: '#F0F0F0' },
    }

    // ── Campaign type filter (from global FilterContext) ──
    const CAMP_TYPES = ['ALL', 'SEARCH', 'PMAX', 'SHOPPING', 'DISPLAY', 'VIDEO']
    const CAMP_LABELS = { ALL: 'Wszystkie', SEARCH: 'Search', PMAX: 'PMax', SHOPPING: 'Shopping', DISPLAY: 'Display', VIDEO: 'Video' }
    const campFilter = allParams.campaign_type || 'ALL'

    const filteredCards = campFilter === 'ALL' ? cards : cards.filter(c => c.types.includes(campFilter))

    // ── Alerts (problems) ──
    const alerts = cards.filter(c => c.status === 'danger')
    const warnings = cards.filter(c => c.status === 'warning')

    // ── Section drill-down renderer ──
    function renderSection(key) {
        const map = {
            waste: <WastedSpendSection data={waste} clientId={selectedClientId} showToast={showToast} />,
            dayparting: <DaypartingSection data={daypart} />,
            hourly: <HourlyDaypartingSection data={hourly} />,
            matchType: <MatchTypeSection data={matchType} />,
            ngram: <NgramSection data={ngram} ngramSize={ngramSize} setNgramSize={setNgramSize} />,
            rsa: <RsaSection data={rsa} />,
            landing: <LandingPageSection data={landing} />,
            structure: <AccountStructureSection data={structure} />,
            bidding: <BiddingAdvisorSection data={bidding} />,
            adGroupHealth: <AdGroupHealthSection data={adGroupHealth} />,
            smartBidding: <SmartBiddingHealthSection data={smartBidding} />,
            pareto: <ParetoSection data={pareto} />,
            scaling: <ScalingSection data={scaling} />,
            targetVsActual: <TargetVsActualSection data={targetVsActual} />,
            learningStatus: <LearningStatusSection data={learningStatus} />,
            portfolioHealth: <PortfolioHealthSection data={portfolioHealth} />,
            convQuality: <ConversionQualitySection data={convQuality} />,
            demographics: <DemographicsSection data={demographics} />,
            pmaxChannels: <PmaxChannelsSection data={pmaxChannels} trends={pmaxTrends} />,
            assetGroups: <AssetGroupsSection data={assetGroups} />,
            searchThemes: <SearchThemesSection data={searchThemes} />,
            pmaxCannibalization: <PmaxCannibalizationSection data={pmaxCannibalization} />,
            audiencePerf: <AudiencePerfSection data={audiencePerf} />,
            missingExt: <MissingExtSection data={missingExt} />,
            extPerf: <ExtPerfSection data={extPerf} />,
        }
        // Inline sections for keys without dedicated components
        if (key === 'convHealth' && convHealth) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
                        <div style={{ padding: '10px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', flex: '1 1 120px' }}>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Score</div>
                            <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Syne', color: convHealth.score >= 80 ? '#4ADE80' : convHealth.score >= 50 ? '#FBBF24' : '#F87171' }}>{convHealth.score}</div>
                        </div>
                        <div style={{ padding: '10px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', flex: '1 1 120px' }}>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Kampanie</div>
                            <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'Syne', color: '#F0F0F0' }}>{convHealth.total_campaigns}</div>
                        </div>
                    </div>
                    {convHealth.campaigns?.length > 0 && (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead><tr>{['Kampania','Typ','Koszt','Konwersje','CVR','Score','Problemy'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Kampania' || h === 'Problemy' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                            <tbody>{convHealth.campaigns.map((c, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0', fontWeight: 500, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.campaign_name}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.campaign_type}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.cost_usd} zł</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{c.conversions}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.conv_rate_pct}%</td>
                                    <td style={{ ...TD, textAlign: 'right', color: c.score >= 80 ? '#4ADE80' : c.score >= 50 ? '#FBBF24' : '#F87171', fontWeight: 600 }}>{c.score}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'left', fontSize: 11 }}>{c.issues?.join(', ') || '—'}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'auctionInsights' && auctionData?.competitors) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    {auctionData.competitors.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', padding: '12px 0' }}>Brak danych. Uruchom sync.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                                {['Domena','IS %','Overlap %','Poz. wyżej %','Outranking %','Top %','Abs. top %'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Domena' ? 'left' : 'right' }}>{h}</th>)}
                            </tr></thead>
                            <tbody>{auctionData.competitors.map((c, i) => {
                                const isYou = c.is_self
                                return (
                                    <tr key={i} style={isYou ? { borderBottom: '1px solid rgba(79,142,247,0.15)', background: 'rgba(79,142,247,0.04)' } : { borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                        <td style={{ ...TD, color: isYou ? '#4F8EF7' : '#F0F0F0', fontWeight: isYou ? 600 : 400 }}>{c.display_domain} {isYou && <span style={{ fontSize: 9, opacity: 0.5 }}>(Ty)</span>}</td>
                                        <td style={{ ...TD, textAlign: 'right', color: c.impression_share >= 30 ? '#4ADE80' : c.impression_share >= 15 ? '#FBBF24' : '#F87171' }}>{c.impression_share}%</td>
                                        <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.overlap_rate}%</td>
                                        <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.position_above_rate}%</td>
                                        <td style={{ ...TD, textAlign: 'right', color: c.outranking_share >= 40 ? '#4ADE80' : 'rgba(255,255,255,0.6)' }}>{c.outranking_share}%</td>
                                        <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.top_of_page_rate}%</td>
                                        <td style={{ ...TD_DIM, textAlign: 'right' }}>{c.abs_top_of_page_rate}%</td>
                                    </tr>
                                )
                            })}</tbody>
                        </table>
                    }
                </div>
            )
        }
        if (key === 'shoppingGroups' && shoppingData?.groups) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {shoppingData.groups.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak grup produktów.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Grupa','Typ','Bid','Kliknięcia','Impr.','Koszt','Konw.'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Grupa' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                            <tbody>{shoppingData.groups.map((g, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0' }}>{g.case_value || '—'}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{g.case_value_type}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.bid_micros != null ? `${(g.bid_micros/1e6).toFixed(2)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.clicks}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{g.impressions}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.cost_micros != null ? `${(g.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                    <td style={{ ...TD, textAlign: 'right' }}>{g.conversions}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'placementPerf' && placementData?.placements) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['URL/Placement','Typ','Kliknięcia','Impr.','Koszt','Konw.','Video views'].map(h => <th key={h} style={{ ...TH, textAlign: h.startsWith('URL') ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                        <tbody>{placementData.placements.slice(0,20).map((p, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0', maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.placement_url || '—'}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right', fontSize: 10 }}>{p.placement_type}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.clicks}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{p.impressions}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.cost_micros != null ? `${(p.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{p.conversions}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{p.video_views || '—'}</td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            )
        }
        if (key === 'topicPerf' && topicData?.topics) {
            return (
                <div style={{ padding: '0 16px 16px', overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Temat','Bid mod.','Kliknięcia','Impr.','Koszt','Konw.'].map(h => <th key={h} style={{ ...TH, textAlign: h === 'Temat' ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
                        <tbody>{topicData.topics.map((t, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0' }}>{t.topic_path || '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.bid_modifier != null ? `${(t.bid_modifier * 100).toFixed(0)}%` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.clicks}</td>
                                <td style={{ ...TD_DIM, textAlign: 'right' }}>{t.impressions}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.cost_micros != null ? `${(t.cost_micros/1e6).toFixed(0)} zł` : '—'}</td>
                                <td style={{ ...TD, textAlign: 'right' }}>{t.conversions}</td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            )
        }
        if (key === 'bidModifiers' && bidModData?.modifiers) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Kampania','Typ','Urządzenie/Lokalizacja','Modifier'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                        <tbody>{bidModData.modifiers.map((m, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                <td style={{ ...TD, color: '#F0F0F0', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.campaign_name || '—'}</td>
                                <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{m.modifier_type}</td>
                                <td style={TD}>{m.device_type || m.location_name || (m.day_of_week ? `${m.day_of_week} ${m.start_hour}-${m.end_hour}h` : '—')}</td>
                                <td style={{ ...TD, color: m.bid_modifier > 1 ? '#4ADE80' : m.bid_modifier < 1 ? '#F87171' : '#F0F0F0', fontWeight: 600 }}>
                                    {m.bid_modifier != null ? `${m.bid_modifier > 1 ? '+' : ''}${((m.bid_modifier - 1) * 100).toFixed(0)}%` : '—'}
                                </td>
                            </tr>
                        ))}</tbody>
                    </table>
                </div>
            )
        }
        if (key === 'googleRecs' && googleRecsData?.recommendations) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {googleRecsData.recommendations.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak nowych rekomendacji Google.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Typ','Kampania','Impact','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{googleRecsData.recommendations.map((r, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontSize: 11, color: '#F0F0F0' }}>{r.type}</td>
                                    <td style={{ ...TD, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.campaign_name || '—'}</td>
                                    <td style={TD}>{typeof r.impact_estimate === 'object' ? JSON.stringify(r.impact_estimate) : r.impact_estimate || '—'}</td>
                                    <td style={{ ...TD, color: r.status === 'ACTIVE' ? '#4ADE80' : r.dismissed ? '#F87171' : '#FBBF24', fontSize: 10 }}>{r.dismissed ? 'Odrzucona' : r.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'convValueRules' && convValueRulesData?.rules) {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {convValueRulesData.rules.length === 0 ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak reguł wartości konwersji.</p> : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Warunek','Wartość','Typ akcji','Wartość','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{convValueRulesData.rules.map((r, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{r.condition_type || '—'}</td>
                                    <td style={TD}>{r.condition_value || '—'}</td>
                                    <td style={TD_DIM}>{r.action_type || '—'}</td>
                                    <td style={TD}>{r.action_type === 'ADD' && r.action_value_micros != null ? `+${(r.action_value_micros/1e6).toFixed(2)} zł` : r.action_type === 'MULTIPLY' && r.action_multiplier != null ? `×${r.action_multiplier}` : '—'}</td>
                                    <td style={{ ...TD_DIM, fontSize: 10 }}>{r.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    )}
                </div>
            )
        }
        if (key === 'offlineConversions') {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {!offlineConvData?.conversions || offlineConvData.conversions.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak uploadowanych konwersji offline.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['GCLID','Konwersja','Data','Wartość','Status'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{offlineConvData.conversions.map((c, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, fontSize: 10, fontFamily: 'monospace', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.gclid}</td>
                                    <td style={TD}>{c.conversion_name || '—'}</td>
                                    <td style={TD_DIM}>{c.conversion_time}</td>
                                    <td style={TD}>{c.conversion_value != null ? `${c.conversion_value} zł` : '—'}</td>
                                    <td style={{ ...TD, fontSize: 10, color: c.status === 'UPLOADED' ? '#4ADE80' : c.status === 'FAILED' ? '#F87171' : '#FBBF24' }}>{c.status}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    }
                </div>
            )
        }
        if (key === 'audiencesList') {
            return (
                <div style={{ padding: '0 16px 16px' }}>
                    {!audiencesListData?.audiences || audiencesListData.audiences.length === 0
                        ? <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>Brak odbiorców.</p>
                        : <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead><tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{['Nazwa','Typ','Status','Członków'].map(h => <th key={h} style={TH}>{h}</th>)}</tr></thead>
                            <tbody>{audiencesListData.audiences.map((a, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                                    <td style={{ ...TD, color: '#F0F0F0' }}>{a.name}</td>
                                    <td style={{ ...TD_DIM, fontSize: 10, textTransform: 'uppercase' }}>{a.type || '—'}</td>
                                    <td style={{ ...TD, fontSize: 10, color: a.status === 'ENABLED' ? '#4ADE80' : 'rgba(255,255,255,0.4)' }}>{a.status}</td>
                                    <td style={{ ...TD_DIM, textAlign: 'right' }}>{a.member_count != null ? a.member_count.toLocaleString('pl-PL') : '—'}</td>
                                </tr>
                            ))}</tbody>
                        </table>
                    }
                </div>
            )
        }
        return map[key] || <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', padding: 16 }}>Brak danych dla tej sekcji.</p>
    }

    if (loading) {
        return (
            <div style={{ maxWidth: 1400 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', marginBottom: 20 }}>
                    Optymalizacja kampanii
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
                    <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
                </div>
            </div>
        )
    }

    // ── DRILL-DOWN VIEW ──
    if (activeSection) {
        const card = cards.find(c => c.key === activeSection)
        const Icon = card?.icon || AlertTriangle
        return (
            <div style={{ maxWidth: 1400 }}>
                <div style={{ marginBottom: 16 }}>
                    <button onClick={() => setActiveSection(null)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: 8 }}>
                        <ChevronRight size={14} style={{ color: '#4F8EF7', transform: 'rotate(180deg)' }} />
                        <span style={{ fontSize: 12, color: '#4F8EF7' }}>Command Center</span>
                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>›</span>
                        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>{card?.title}</span>
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Icon size={18} style={{ color: '#4F8EF7' }} />
                        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne' }}>{card?.title}</h1>
                    </div>
                </div>
                <div className={CARD}>
                    {renderSection(activeSection)}
                </div>
            </div>
        )
    }

    // ── COMMAND CENTER (BENTO GRID) ──
    return (
        <div style={{ maxWidth: 1400 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Optymalizacja kampanii
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Analiza {days} dni — {filteredCards.length} sekcji
                    </p>
                </div>
            </div>

            {/* Campaign type pill filters — synced with global sidebar filter */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
                {CAMP_TYPES.map(t => (
                    <button key={t} onClick={() => setFilter('campaignType', t)} style={{
                        padding: '5px 14px', borderRadius: 999, fontSize: 12, fontFamily: 'DM Sans', fontWeight: 500,
                        cursor: 'pointer', border: 'none', transition: 'all 0.15s',
                        background: campFilter === t ? '#4F8EF7' : 'transparent',
                        color: campFilter === t ? '#FFFFFF' : 'rgba(255,255,255,0.5)',
                        outline: campFilter === t ? 'none' : '1px solid rgba(255,255,255,0.12)',
                    }}>{CAMP_LABELS[t]}</button>
                ))}
            </div>

            {/* Alert bar */}
            {alerts.length > 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', marginBottom: 16,
                    borderRadius: 8, background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.2)',
                }}>
                    <AlertTriangle size={16} style={{ color: '#F87171', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: '#F87171' }}>
                        {alerts.length} {alerts.length === 1 ? 'problem wymaga' : 'problemy wymagają'} uwagi: {alerts.map(a => a.title).join(', ')}
                    </span>
                </div>
            )}
            {warnings.length > 0 && alerts.length === 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', marginBottom: 16,
                    borderRadius: 8, background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.2)',
                }}>
                    <AlertTriangle size={16} style={{ color: '#FBBF24', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: '#FBBF24' }}>
                        {warnings.length} {warnings.length === 1 ? 'ostrzeżenie' : 'ostrzeżeń'}: {warnings.map(a => a.title).join(', ')}
                    </span>
                </div>
            )}

            {/* Bento Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 12,
            }}>
                {filteredCards.map(card => {
                    const sc = STATUS_COLORS[card.status] || STATUS_COLORS.neutral
                    const Icon = card.icon
                    return (
                        <button key={card.key} onClick={() => setActiveSection(card.key)} style={{
                            display: 'flex', flexDirection: 'column', gap: 8, padding: 16,
                            borderRadius: 12, cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                            background: 'rgba(255,255,255,0.02)', border: `1px solid ${sc.border}`,
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; e.currentTarget.style.transform = 'none' }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <Icon size={14} style={{ color: sc.dot, flexShrink: 0 }} />
                                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>{card.title}</span>
                                </div>
                                <div style={{ width: 7, height: 7, borderRadius: 999, background: sc.dot, flexShrink: 0 }} />
                            </div>
                            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: sc.valueFill }}>{card.value}</div>
                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{card.sub}</div>
                        </button>
                    )
                })}
            </div>
        </div>
    )
}
