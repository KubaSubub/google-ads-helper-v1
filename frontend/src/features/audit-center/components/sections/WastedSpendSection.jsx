import MetricPill from '../../../../components/shared/MetricPill'
import { addNegativeKeyword } from '../../../../api'

export default function WastedSpendSection({ data, clientId, showToast }) {
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
