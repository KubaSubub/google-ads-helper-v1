import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronDown, ChevronUp, ChevronRight, Lightbulb, ShieldAlert, TrendingUp } from 'lucide-react'

const SOURCE_LABELS = {
    ANALYTICS: 'Insight backendu',
    PLAYBOOK_RULES: 'Playbook',
    GOOGLE_ADS_API: 'Google Ads',
    HYBRID: 'Hybrid',
}

const PRIORITY_CONFIG = {
    HIGH: {
        icon: AlertTriangle,
        color: '#F87171',
        bg: 'rgba(248,113,113,0.08)',
        border: 'rgba(248,113,113,0.2)',
        label: 'Wysoki',
    },
    MEDIUM: {
        icon: ShieldAlert,
        color: '#FBBF24',
        bg: 'rgba(251,191,36,0.08)',
        border: 'rgba(251,191,36,0.2)',
        label: 'Średni',
    },
    LOW: {
        icon: TrendingUp,
        color: '#4F8EF7',
        bg: 'rgba(79,142,247,0.08)',
        border: 'rgba(79,142,247,0.2)',
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

export default function InsightsFeed({ recommendations }) {
    const insights = useMemo(() => mapInsights(recommendations), [recommendations])
    const [expanded, setExpanded] = useState(insights.length > 0)
    const hasInsights = insights.length > 0
    const navigate = useNavigate()

    return (
        <div className="v2-card" style={{ overflow: 'hidden' }}>
            <button
                onClick={() => setExpanded(v => !v)}
                className="w-full"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 20px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    width: '100%',
                }}
            >
                <div className="flex items-center gap-2">
                    <Lightbulb size={15} style={{ color: '#FBBF24' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
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
                                color: '#FBBF24',
                                border: '1px solid rgba(251,191,36,0.25)',
                            }}
                        >
                            {insights.length}
                        </span>
                    ) : (
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                            - wszystko wygląda dobrze
                        </span>
                    )}
                </div>
                {expanded
                    ? <ChevronUp size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />
                    : <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />}
            </button>

            {expanded && hasInsights && (
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {insights.map(insight => {
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
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0' }}>
                                            {insight.entity || 'Insight'}
                                        </span>
                                        <span style={{ fontSize: 10, color: cfg.color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                            {cfg.label}
                                        </span>
                                        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>
                                            {SOURCE_LABELS[insight.source] || insight.source}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: 12, color: '#E8E8E8', lineHeight: 1.45, marginBottom: 4 }}>
                                        {insight.message}
                                    </div>
                                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
                                        {insight.detail}
                                        {insight.expiresAt ? ` • wygasa ${new Date(insight.expiresAt).toLocaleString('pl-PL')}` : ''}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => { e.stopPropagation(); navigate('/recommendations') }}
                                    style={{
                                        background: 'rgba(79,142,247,0.1)',
                                        border: '1px solid rgba(79,142,247,0.25)',
                                        borderRadius: 6,
                                        padding: '4px 10px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 4,
                                        color: '#4F8EF7',
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
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '10px 16px', textAlign: 'right' }}>
                    <span
                        onClick={() => navigate('/recommendations')}
                        style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}
                    >
                        Wszystkie rekomendacje →
                    </span>
                </div>
            )}

            {expanded && !hasInsights && (
                <div
                    style={{
                        borderTop: '1px solid rgba(255,255,255,0.07)',
                        padding: '20px',
                        textAlign: 'center',
                        fontSize: 12,
                        color: 'rgba(255,255,255,0.3)',
                    }}
                >
                    Brak aktywnych insightów backendowych.
                </div>
            )}
        </div>
    )
}
