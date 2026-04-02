import { useState } from 'react'
import { Pin, TrendingUp, TrendingDown } from 'lucide-react'
import { STATUS_COLORS } from '../../../constants/designTokens'

export default function BentoCard({ card, onClick, pinned, onTogglePin, changePct }) {
    const sc = STATUS_COLORS[card.status] || STATUS_COLORS.neutral
    const Icon = card.icon
    const [hovered, setHovered] = useState(false)

    const handlePin = (e) => {
        e.stopPropagation()
        onTogglePin?.(card.key)
    }

    return (
        <button onClick={onClick} style={{
            display: 'flex', flexDirection: 'column', gap: 8, padding: 16,
            borderRadius: 12, cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
            background: pinned ? 'rgba(79,142,247,0.06)' : 'rgba(255,255,255,0.02)',
            border: `1px solid ${pinned ? 'rgba(79,142,247,0.25)' : sc.border}`,
            position: 'relative',
        }}
        onMouseEnter={e => { setHovered(true); e.currentTarget.style.background = pinned ? 'rgba(79,142,247,0.10)' : C.w05; e.currentTarget.style.transform = 'translateY(-1px)' }}
        onMouseLeave={e => { setHovered(false); e.currentTarget.style.background = pinned ? 'rgba(79,142,247,0.06)' : 'rgba(255,255,255,0.02)'; e.currentTarget.style.transform = 'none' }}
        >
            {(hovered || pinned) && (
                <div
                    onClick={handlePin}
                    title={pinned ? 'Odepnij' : 'Przypnij'}
                    style={{
                        position: 'absolute', top: 8, right: 8,
                        width: 22, height: 22, borderRadius: 6,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: pinned ? C.infoBg : C.w06,
                        transition: 'all 0.15s', cursor: 'pointer',
                        opacity: pinned ? 1 : 0.6,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = pinned ? 'rgba(79,142,247,0.25)' : C.w12; e.currentTarget.style.opacity = '1' }}
                    onMouseLeave={e => { e.currentTarget.style.background = pinned ? C.infoBg : C.w06; e.currentTarget.style.opacity = pinned ? '1' : '0.6' }}
                >
                    <Pin size={12} style={{
                        color: pinned ? C.accentBlue : C.w50,
                        transform: pinned ? 'rotate(0deg)' : 'rotate(45deg)',
                        transition: 'transform 0.15s',
                    }} />
                </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Icon size={14} style={{ color: sc.dot, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, fontFamily: 'Syne' }}>{card.title}</span>
                </div>
                <div style={{ width: 7, height: 7, borderRadius: 999, background: sc.dot, flexShrink: 0 }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'Syne', color: sc.valueFill }}>{card.value}</div>
                {changePct != null && changePct.pct !== 0 && (() => {
                    const up = changePct.pct > 0
                    const isGood = up === changePct.upIsGood
                    const color = isGood ? C.success : C.danger
                    const TrendIcon = up ? TrendingUp : TrendingDown
                    return (
                        <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: 3,
                            padding: '2px 6px', borderRadius: 999, fontSize: 10, fontWeight: 600,
                            fontFamily: 'DM Sans', lineHeight: 1,
                            color, background: isGood ? C.successBg : C.dangerBg,
                        }}>
                            <TrendIcon size={10} />
                            {up ? '+' : ''}{changePct.pct}%
                        </span>
                    )
                })()}
            </div>
            <div style={{ fontSize: 11, color: C.w40 }}>{card.sub}</div>
        </button>
    )
}
