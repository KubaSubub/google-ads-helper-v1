// QsHealthWidget — compact quality score health bar linking to /quality-score
import { Award, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function QsHealthWidget({ qsAudit }) {
    const navigate = useNavigate()

    if (!qsAudit || qsAudit.total_keywords === 0) return null

    return (
        <div
            className="v2-card"
            style={{ padding: '14px 18px', marginBottom: 16, cursor: 'pointer' }}
            onClick={() => navigate('/quality-score')}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(123,92,224,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Award size={16} style={{ color: '#7B5CE0' }} />
                    </div>
                    <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F0F0' }}>
                            Quality Score:{' '}
                            <span style={{
                                color: qsAudit.average_qs >= 7 ? '#4ADE80' : qsAudit.average_qs >= 5 ? '#FBBF24' : '#F87171',
                                fontFamily: 'Syne',
                            }}>
                                {qsAudit.average_qs}/10
                            </span>
                        </div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 1 }}>
                            {qsAudit.low_qs_count > 0
                                ? `${qsAudit.low_qs_count} słów z niskim QS • ${qsAudit.low_qs_spend_pct}% budżetu`
                                : 'Wszystkie słowa powyżej progu'}
                        </div>
                    </div>
                </div>
                <ChevronRight size={14} style={{ color: 'rgba(255,255,255,0.2)' }} />
            </div>
        </div>
    )
}
