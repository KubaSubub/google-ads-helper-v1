import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ChevronUp, ChevronRight, Lightbulb, ShieldAlert, TrendingUp } from 'lucide-react'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

const SOURCE_LABELS = {
    ANALYTICS: 'Insight backendu',
    PLAYBOOK_RULES: 'Playbook',
    GOOGLE_ADS_API: 'Google Ads',
    HYBRID: 'Hybrid',
}

const PRIORITY_CONFIG = {
    HIGH: {
        icon: AlertTriangle,
        color: C.danger,
        bg: C.dangerBg,
        border: C.dangerBorder,
        label: 'Wysoki',
    },
    MEDIUM: {
        icon: ShieldAlert,
        color: C.warning,
        bg: 'rgba(251,191,36,0.08)',
        border: C.warningBorder,
        label: 'Średni',
    },
    LOW: {
        icon: TrendingUp,
        color: C.accentBlue,
        bg: 'rgba(79,142,247,0.08)',
        border: C.infoBorder,
        label: 'Info',
    },
}

function mapInsights(recommendations = []) {
    return (recommendations || [])
        .filter(rec => rec.source === 'ANALYTICS' && rec.status === 'pending')
        .sort((a, b) => {
            const rank = { HIGH: 0, MEDIUM: 1, LOW: 2 }
            return (rank[a.priority] ?? 99) - (rank[b.priority] ?? 99)
        })
        .map(rec => ({
            id: rec.id,
            priority: rec.priority,
            message: rec.reason,
            detail: rec.recommended_action || rec.metadata?.insight_type || SOURCE_LABELS[rec.source] || rec.source,
            source: rec.source,
            entity: rec.entity_name,
            expiresAt: rec.expires_at,
        }))
}

const PRIORITY_PILLS = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

export default function InsightsFeed({ recommendations }) {
    const insights = useMemo(() => mapInsights(recommendations), [recommendations])
    const [expanded, setExpanded] = useState(insights.some(i => i.priority === 'HIGH'))
    const [filterPriority, setFilterPriority] = useState('ALL')
    const hasInsights = insights.length > 0
    const navigate = useNavigate()

    const filteredInsights = useMemo(() => {
        if (filterPriority === 'ALL') return insights
        return insights.filter(i => i.priority === filterPriority)
    }, [insights, filterPriority])

    return (
        <div className="v2-card" style={{ overflow: 'hidden' }}>
            <button
                data-testid="insights-feed-header"
                onClick={() => setExpanded(v => !v)}
                className="w-full"
                style={{
                    display: 'block',
                    padding: '14px 20px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div className="flex items-center gap-2">
                        <Lightbulb size={15} style={{ color: C.warning }} />
                        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>
                            Automatyczne insighty
                        </span>
                        {hasInsights ? (
                            <span
                                style={{
                                    fontSize: 10,
                                    fontWeight: 600,
                                    padding: '2px 7px',
                                    borderRadius: 999,
                                    background: 'rgba(251,191,36,0.15)',
                                    color: C.warning,
                                    border: '1px solid rgba(251,191,36,0.25)',
                                }}
                            >
                                {insights.length}
                            </span>
                        ) : (
                            <span style={{ fontSize: 11, color: C.w30 }}>
                                - wszystko wygląda dobrze
                            </span>
                        )}
                    </div>
                    {expanded
                        ? <ChevronUp size={14} style={{ color: C.w30 }} />
                        : <ChevronDown size={14} style={{ color: C.w30 }} />}
                </div>
                {hasInsights && (
                    <div
                        data-testid="insights-feed-pills"
                        style={{
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: 6,
                            marginTop: 8,
                            paddingLeft: 23,
                        }}
                    >
                        {insights.slice(0, 3).map(insight => {
                            const cfg = PRIORITY_CONFIG[insight.priority] || PRIORITY_CONFIG.LOW
                            const entityPart = insight.entity ? `${insight.entity}: ` : ''
                            const fullText = `${entityPart}${insight.message || ''}`
                            const display = fullText.length > 40 ? `${fullText.slice(0, 40)}…` : fullText
                            return (
                                <span
                                    key={insight.id}
                                    title={fullText}
                                    style={{
                                        fontSize: 10,
                                        fontWeight: 500,
                                        padding: '3px 8px',
                                        borderRadius: 999,
                                        background: cfg.bg,
                                        border: `1px solid ${cfg.border}`,
                                        color: cfg.color,
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        maxWidth: 280,
                                    }}
                                >
                                    {display}
                                </span>
                            )
                        })}
                        {insights.length > 3 && (
                            <span
                                style={{
                                    fontSize: 10,
                                    fontWeight: 500,
                                    padding: '3px 8px',
                                    color: C.w40,
                                }}
                            >
                                +{insights.length - 3} więcej
                            </span>
                        )}
                    </div>
                )}
            </button>

            {expanded && hasInsights && (
                <div
                    data-testid="insights-feed-panel"
                    style={{
                        borderTop: B.card,
                        padding: '12px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                        maxHeight: insights.filter(i => i.priority === 'HIGH').length > 5 ? 320 : 'none',
                        overflowY: insights.filter(i => i.priority === 'HIGH').length > 5 ? 'auto' : 'visible',
                    }}
                >
                    <div className="flex items-center gap-1" style={{ marginBottom: 4 }}>
                        {PRIORITY_PILLS.map(p => {
                            const active = filterPriority === p
                            const label = p === 'ALL' ? 'Wszystkie' : p === 'HIGH' ? 'Pilne' : p === 'MEDIUM' ? 'Średnie' : 'Info'
                            const count = p === 'ALL' ? insights.length : insights.filter(i => i.priority === p).length
                            return (
                                <button
                                    key={p}
                                    onClick={e => { e.stopPropagation(); setFilterPriority(p) }}
                                    style={{
                                        fontSize: 10, fontWeight: 500, padding: '3px 8px', borderRadius: 999,
                                        border: `1px solid ${active ? C.infoBorder : C.w08}`,
                                        background: active ? 'rgba(79,142,247,0.12)' : 'transparent',
                                        color: active ? C.accentBlue : C.w40,
                                        cursor: 'pointer',
                                    }}
                                >
                                    {label} ({count})
                                </button>
                            )
                        })}
                    </div>
                    {filteredInsights.map(insight => {
                        const cfg = PRIORITY_CONFIG[insight.priority] || PRIORITY_CONFIG.LOW
                        const Icon = cfg.icon
                        return (
                            <div
                                key={insight.id}
                                style={{
                                    background: cfg.bg,
                                    border: `1px solid ${cfg.border}`,
                                    borderRadius: 8,
                                    padding: '10px 14px',
                                    display: 'flex',
                                    gap: 10,
                                    alignItems: 'flex-start',
                                }}
                            >
                                <Icon size={14} style={{ color: cfg.color, flexShrink: 0, marginTop: 1 }} />
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                                        <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>
                                            {insight.entity || 'Insight'}
                                        </span>
                                        <span style={{ fontSize: 10, color: cfg.color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                            {cfg.label}
                                        </span>
                                        <span style={{ fontSize: 10, color: C.textMuted }}>
                                            {SOURCE_LABELS[insight.source] || insight.source}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: 12, color: '#E8E8E8', lineHeight: 1.45, marginBottom: 4 }}>
                                        {insight.message}
                                    </div>
                                    <div style={{ fontSize: 11, color: C.textPlaceholder, lineHeight: 1.5 }}>
                                        {insight.detail}
                                        {insight.expiresAt ? ` • wygasa ${new Date(insight.expiresAt).toLocaleString('pl-PL')}` : ''}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); navigate('/recommendations') }}
                                    style={{
                                        background: C.infoBg,
                                        border: '1px solid rgba(79,142,247,0.25)',
                                        borderRadius: 6,
                                        padding: '4px 10px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 4,
                                        color: C.accentBlue,
                                        fontSize: 11,
                                        fontWeight: 500,
                                        whiteSpace: 'nowrap',
                                        flexShrink: 0,
                                        alignSelf: 'center',
                                    }}
                                >
                                    Przejdź <ChevronRight size={12} />
                                </button>
                            </div>
                        )
                    })}
                </div>
            )}

            {expanded && hasInsights && (
                <div style={{ borderTop: B.card, padding: '10px 16px', textAlign: 'right' }}>
                    <span
                        onClick={() => navigate('/recommendations')}
                        style={{ fontSize: 11, color: C.accentBlue, cursor: 'pointer' }}
                    >
                        Wszystkie rekomendacje →
                    </span>
                </div>
            )}

            {expanded && !hasInsights && (
                <div
                    style={{
                        borderTop: B.card,
                        padding: '20px',
                        textAlign: 'center',
                        fontSize: 12,
                        color: C.w30,
                    }}
                >
                    Brak aktywnych insightów backendowych.
                </div>
            )}
        </div>
    )
}
