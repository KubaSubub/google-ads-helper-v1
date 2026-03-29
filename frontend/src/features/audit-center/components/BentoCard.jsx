import { STATUS_COLORS } from '../../../constants/designTokens'

export default function BentoCard({ card, onClick }) {
    const sc = STATUS_COLORS[card.status] || STATUS_COLORS.neutral
    const Icon = card.icon
    return (
        <button onClick={onClick} style={{
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
}
