import { TD } from '../../../../constants/designTokens'

export default function RsaSection({ data }) {
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
