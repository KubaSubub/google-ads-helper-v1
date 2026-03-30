// TopActions — top 3 most impactful pending recommendations
import { Zap, AlertTriangle, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const PRIORITY_CONFIG = {
    HIGH:   { color: '#F87171', bg: 'rgba(248,113,113,0.1)', label: 'Pilne' },
    MEDIUM: { color: '#FBBF24', bg: 'rgba(251,191,36,0.1)',  label: 'Srednie' },
    LOW:    { color: '#4F8EF7', bg: 'rgba(79,142,247,0.1)',  label: 'Info' },
}

export default function TopActions({ recommendations }) {
    const navigate = useNavigate()

    // Filter to pending + sort by score desc, take top 3
    const top = (recommendations || [])
        .filter(r => r.status === 'pending')
        .sort((a, b) => (b.score || 0) - (a.score || 0))
        .slice(0, 3)

    if (top.length === 0) return null

    return (
        <div className="v2-card" style={{ padding: '16px 20px', marginBottom: 16 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                <div className="flex items-center gap-2">
                    <Zap size={14} style={{ color: '#FBBF24' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Top akcje na dzis
                    </span>
                </div>
                <span
                    onClick={() => navigate('/recommendations')}
                    style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}
                >
                    Wszystkie →
                </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {top.map((rec, i) => {
                    const cfg = PRIORITY_CONFIG[rec.priority] || PRIORITY_CONFIG.LOW
                    const impact = rec.impact_micros ? `${(rec.impact_micros / 1_000_000).toFixed(0)} zl` : null
                    return (
                        <div
                            key={rec.id || i}
                            onClick={() => navigate('/recommendations')}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 12,
                                padding: '10px 14px', borderRadius: 10, cursor: 'pointer',
                                background: 'rgba(255,255,255,0.02)',
                                border: '1px solid rgba(255,255,255,0.05)',
                                transition: 'background 0.12s',
                            }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                        >
                            {/* Priority badge */}
                            <span style={{
                                fontSize: 9, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                                background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}30`,
                                whiteSpace: 'nowrap', flexShrink: 0,
                            }}>
                                {cfg.label}
                            </span>

                            {/* Content */}
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {rec.entity_name || rec.rule_id?.replace(/_/g, ' ')}
                                </div>
                                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 2 }}>
                                    {rec.reason}
                                </div>
                            </div>

                            {/* Impact */}
                            {impact && (
                                <div style={{ flexShrink: 0, textAlign: 'right' }}>
                                    <div style={{ fontSize: 12, fontWeight: 600, color: '#4ADE80', fontFamily: 'Syne' }}>
                                        ~{impact}
                                    </div>
                                    <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>oszczednosc</div>
                                </div>
                            )}

                            <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.15)', flexShrink: 0 }} />
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
