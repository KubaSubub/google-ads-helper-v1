// HealthScoreCard — circular gauge + 6-pillar breakdown + issue list
const PILLAR_LABELS = {
    performance: 'Wyniki',
    quality: 'Jakość',
    efficiency: 'Efektywność',
    coverage: 'Zasięg',
    stability: 'Stabilność',
    structure: 'Struktura',
}
const PILLAR_ORDER = ['performance', 'quality', 'efficiency', 'coverage', 'stability', 'structure']

function pillarColor(score) {
    if (score > 70) return '#4ADE80'
    if (score > 40) return '#FBBF24'
    return '#F87171'
}

function PillarBars({ breakdown }) {
    if (!breakdown || !breakdown.performance) return null
    return (
        <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
            {PILLAR_ORDER.map(key => {
                const p = breakdown[key]
                if (!p) return null
                return (
                    <div key={key} style={{ flex: 1, minWidth: 0 }} title={`${PILLAR_LABELS[key]}: ${p.score}/100`}>
                        <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.3)', marginBottom: 3, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {PILLAR_LABELS[key]}
                        </div>
                        <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
                            <div style={{
                                height: '100%',
                                borderRadius: 2,
                                width: `${p.score}%`,
                                background: pillarColor(p.score),
                                transition: 'width 0.6s ease',
                            }} />
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

export default function HealthScoreCard({ score, issues, loading, dataAvailable, breakdown, onClick }) {
    const radius = 34
    const circumference = 2 * Math.PI * radius
    const safeScore = typeof score === 'number' ? score : 0
    const offset = circumference * (1 - safeScore / 100)
    const color = safeScore > 70 ? '#4ADE80' : safeScore > 40 ? '#FBBF24' : '#F87171'

    // Aggressive background tint for alarming scores
    const bgTint = safeScore > 70 || safeScore === 0
        ? 'transparent'
        : safeScore <= 40
            ? 'rgba(248,113,113,0.08)'
            : 'rgba(251,191,36,0.06)'
    const borderTint = safeScore > 70 || safeScore === 0
        ? undefined
        : safeScore <= 40
            ? '1px solid rgba(248,113,113,0.18)'
            : '1px solid rgba(251,191,36,0.12)'

    return (
        <div
            className="v2-card"
            style={{
                padding: '20px 24px', height: '100%', display: 'flex', flexDirection: 'column',
                cursor: onClick ? 'pointer' : 'default',
                background: bgTint,
                ...(borderTint ? { border: borderTint } : {}),
            }}
            onClick={onClick}
        >
            <div style={{ fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
                Health Score
            </div>

            {loading ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 12 }}>
                    Ładowanie…
                </div>
            ) : dataAvailable === false ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
                            Brak danych
                        </div>
                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', lineHeight: 1.4 }}>
                            Synchronizuj konto aby zebrać dane
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <div className="flex items-center gap-5">
                        {/* Circular gauge */}
                        <div style={{ position: 'relative', width: 76, height: 76, flexShrink: 0 }}>
                            <svg width="76" height="76" viewBox="0 0 76 76">
                                <circle cx="38" cy="38" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
                                <circle
                                    cx="38" cy="38" r={radius} fill="none"
                                    stroke={color} strokeWidth="6"
                                    strokeDasharray={circumference}
                                    strokeDashoffset={offset}
                                    strokeLinecap="round"
                                    transform="rotate(-90 38 38)"
                                    style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                                />
                            </svg>
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <span style={{ fontSize: 22, fontWeight: 700, color, fontFamily: 'Syne', lineHeight: 1 }}>
                                    {safeScore}
                                </span>
                            </div>
                        </div>

                        {/* Issues list */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            {(issues || []).length === 0 ? (
                                <div style={{ fontSize: 12, color: '#4ADE80', lineHeight: 1.5 }}>
                                    Wszystko działa poprawnie
                                </div>
                            ) : (
                                (issues || []).slice(0, 3).map((issue, i) => (
                                    <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'flex-start', marginBottom: 5 }}>
                                        <span style={{
                                            fontSize: 6, marginTop: 4, flexShrink: 0,
                                            color: issue.severity === 'HIGH' ? '#F87171' : issue.severity === 'MEDIUM' ? '#FBBF24' : '#4ADE80',
                                        }}>●</span>
                                        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', lineHeight: 1.45 }}>
                                            {issue.message}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Pillar breakdown bars */}
                    <PillarBars breakdown={breakdown} />
                </>
            )}
        </div>
    )
}
