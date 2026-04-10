// CampaignMiniRanking — top 3 best + worst campaigns by ROAS
import { TrendingUp, TrendingDown, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function CampaignMiniRanking({ campaigns, campaignMetrics }) {
    const navigate = useNavigate()

    if (!campaigns?.length || !campaignMetrics) return null

    // Build ranked list
    const ranked = campaigns
        .filter(c => c.status === 'ENABLED')
        .map(c => {
            const m = campaignMetrics[String(c.id)]
            if (!m || !m.cost_usd || m.cost_usd < 1) return null
            return {
                id: c.id,
                name: c.name,
                roas: m.roas ?? 0,
                cost: m.cost_usd ?? 0,
                conversions: m.conversions ?? 0,
            }
        })
        .filter(Boolean)
        .sort((a, b) => b.roas - a.roas)

    if (ranked.length < 2) return null

    const top3 = ranked.slice(0, 3)
    const bottom3 = [...ranked].sort((a, b) => a.roas - b.roas).slice(0, 3)

    const ColumnHeader = () => (
        <div className="flex items-center gap-3" style={{ padding: '0 12px 6px', fontSize: 9, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            <span style={{ flex: 1 }}>Kampania</span>
            <span style={{ flexShrink: 0, minWidth: 42, textAlign: 'right' }}>ROAS</span>
            <span style={{ flexShrink: 0, minWidth: 60, textAlign: 'right' }}>Koszt</span>
        </div>
    )

    const Row = ({ c, type }) => {
        const color = type === 'top' ? '#4ADE80' : '#F87171'
        return (
            <div
                onClick={() => navigate(`/campaigns?campaign_id=${c.id}`)}
                className="flex items-center gap-3"
                style={{
                    padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.04)',
                    transition: 'background 0.12s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
            >
                <span style={{ fontSize: 12, fontWeight: 500, color: '#F0F0F0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.name}
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, fontFamily: 'Syne', color, flexShrink: 0, minWidth: 42, textAlign: 'right' }}>
                    {c.roas.toFixed(2)}x
                </span>
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace', flexShrink: 0, minWidth: 60, textAlign: 'right' }}>
                    {c.cost.toFixed(0)} zł
                </span>
            </div>
        )
    }

    return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            {/* Top 3 */}
            <div className="v2-card" style={{ padding: '16px 20px' }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
                    <TrendingUp size={14} style={{ color: '#4ADE80' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Top kampanie
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginLeft: 4 }}>
                        sortowane po ROAS
                    </span>
                </div>
                <ColumnHeader />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {top3.map(c => <Row key={c.id} c={c} type="top" />)}
                </div>
            </div>

            {/* Bottom 3 */}
            <div className="v2-card" style={{ padding: '16px 20px' }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
                    <TrendingDown size={14} style={{ color: '#F87171' }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F0F0', fontFamily: 'Syne' }}>
                        Najsłabsze kampanie
                    </span>
                    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginLeft: 4 }}>
                        sortowane po ROAS
                    </span>
                </div>
                <ColumnHeader />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {bottom3.map(c => <Row key={c.id} c={c} type="bottom" />)}
                </div>
            </div>
        </div>
    )
}
