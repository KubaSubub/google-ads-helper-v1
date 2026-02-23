import { useState, useMemo } from 'react'
import { AlertTriangle, TrendingDown, TrendingUp, Info, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react'

const SEVERITY_CONFIG = {
    HIGH: {
        icon: AlertTriangle,
        color: '#F87171',
        bg: 'rgba(248,113,113,0.08)',
        border: 'rgba(248,113,113,0.2)',
        label: 'Uwaga',
    },
    MEDIUM: {
        icon: TrendingDown,
        color: '#FBBF24',
        bg: 'rgba(251,191,36,0.08)',
        border: 'rgba(251,191,36,0.2)',
        label: 'Ostrzeżenie',
    },
    INFO: {
        icon: Info,
        color: '#4F8EF7',
        bg: 'rgba(79,142,247,0.08)',
        border: 'rgba(79,142,247,0.2)',
        label: 'Info',
    },
    POSITIVE: {
        icon: TrendingUp,
        color: '#4ADE80',
        bg: 'rgba(74,222,128,0.08)',
        border: 'rgba(74,222,128,0.2)',
        label: 'Sukces',
    },
}

function generateInsights(kpis, campaigns, recommendations) {
    const insights = []

    if (!campaigns || campaigns.length === 0) return insights

    const enabled = campaigns.filter(c => c.status === 'ENABLED')
    if (enabled.length === 0) return insights

    // --- Rule 1: ENABLED campaigns with spend > avg AND conv = 0 → HIGH
    const avgCost = enabled.reduce((s, c) => s + (c.cost ?? 0), 0) / enabled.length
    const aboveAvgNoConv = enabled.filter(c => (c.cost ?? 0) > avgCost && (c.conversions ?? 0) === 0)
    if (aboveAvgNoConv.length > 0) {
        const names = aboveAvgNoConv.slice(0, 2).map(c => c.name).join(', ')
        const extra = aboveAvgNoConv.length > 2 ? ` i ${aboveAvgNoConv.length - 2} inne` : ''
        insights.push({
            id: 'rule1',
            severity: 'HIGH',
            message: `${aboveAvgNoConv.length} kampani${aboveAvgNoConv.length === 1 ? 'a' : 'e'} powyżej średniego kosztu bez konwersji`,
            detail: `${names}${extra} — rozważ wstrzymanie lub optymalizację targetowania.`,
        })
    }

    // --- Rule 2: CTR delta > +10% AND conv delta < -5% → MEDIUM "rozbieżność"
    const withDeltas = enabled.filter(
        c => c.ctr_delta !== undefined && c.ctr_delta !== null &&
             c.conversions_delta !== undefined && c.conversions_delta !== null
    )
    const divergent = withDeltas.filter(c => c.ctr_delta > 10 && c.conversions_delta < -5)
    if (divergent.length > 0) {
        const names = divergent.slice(0, 2).map(c => c.name).join(', ')
        const extra = divergent.length > 2 ? ` i ${divergent.length - 2} inne` : ''
        insights.push({
            id: 'rule2',
            severity: 'MEDIUM',
            message: `Rozbieżność CTR vs konwersje w ${divergent.length} kampani${divergent.length === 1 ? 'i' : 'ach'}`,
            detail: `${names}${extra} — CTR rośnie, lecz konwersje spadają. Sprawdź stronę docelową i dopasowanie przekazu.`,
        })
    }

    // --- Rule 3: HIGH recommendations → INFO
    const highRecs = (recommendations || []).filter(r => r.priority === 'HIGH' && r.status === 'pending')
    if (highRecs.length > 0) {
        insights.push({
            id: 'rule3',
            severity: 'INFO',
            message: `${highRecs.length} rekomendacj${highRecs.length === 1 ? 'a' : 'i'} HIGH oczekuje na wdrożenie`,
            detail: `Niezatwierdzone rekomendacje mogą blokować dalszą optymalizację kampanii.`,
        })
    }

    // --- Rule 4: Campaign ROAS > 2× avg → positive
    const avgRoas = enabled.reduce((s, c) => s + (c.roas ?? 0), 0) / enabled.length
    if (avgRoas > 0) {
        const stars = enabled.filter(c => (c.roas ?? 0) > avgRoas * 2)
        if (stars.length > 0) {
            const names = stars.slice(0, 2).map(c => c.name).join(', ')
            const extra = stars.length > 2 ? ` i ${stars.length - 2} inne` : ''
            insights.push({
                id: 'rule4',
                severity: 'POSITIVE',
                message: `${stars.length} kampani${stars.length === 1 ? 'a' : 'e'} z ROAS powyżej 2× średniej`,
                detail: `${names}${extra} — rozważ zwiększenie budżetu, aby skalować wyniki.`,
            })
        }
    }

    return insights
}

export default function InsightsFeed({ kpis, campaigns, recommendations }) {
    const insights = useMemo(
        () => generateInsights(kpis, campaigns, recommendations),
        [kpis, campaigns, recommendations]
    )

    const [expanded, setExpanded] = useState(insights.length > 0)

    // Sync expand state when insights change from 0 to >0
    const hasInsights = insights.length > 0

    return (
        <div className="v2-card" style={{ overflow: 'hidden' }}>
            {/* Header — always visible */}
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
                    {hasInsights && (
                        <span style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: '2px 7px',
                            borderRadius: 999,
                            background: 'rgba(251,191,36,0.15)',
                            color: '#FBBF24',
                            border: '1px solid rgba(251,191,36,0.25)',
                        }}>
                            {insights.length}
                        </span>
                    )}
                    {!hasInsights && (
                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                            — wszystko wygląda dobrze
                        </span>
                    )}
                </div>
                {expanded
                    ? <ChevronUp size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />
                    : <ChevronDown size={14} style={{ color: 'rgba(255,255,255,0.3)' }} />
                }
            </button>

            {/* Insight list */}
            {expanded && hasInsights && (
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {insights.map(insight => {
                        const cfg = SEVERITY_CONFIG[insight.severity]
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
                                <div>
                                    <div style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0', marginBottom: 2 }}>
                                        {insight.message}
                                    </div>
                                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
                                        {insight.detail}
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Empty expanded state */}
            {expanded && !hasInsights && (
                <div style={{
                    borderTop: '1px solid rgba(255,255,255,0.07)',
                    padding: '20px',
                    textAlign: 'center',
                    fontSize: 12,
                    color: 'rgba(255,255,255,0.3)',
                }}>
                    Brak aktywnych insightów — kampanie działają prawidłowo.
                </div>
            )}
        </div>
    )
}
