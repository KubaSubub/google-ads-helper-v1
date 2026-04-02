import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

/**
 * Custom dark-themed dropdown replacing native <select>.
 *
 * Props:
 *  - value: current value
 *  - onChange(value): callback with selected value (string)
 *  - options: [{ value, label }]
 *  - placeholder: text when no value selected
 *  - style: extra styles on trigger button
 *  - disabled: boolean
 *  - dropUp: open upward instead of downward
 */
export default function DarkSelect({
    value,
    onChange,
    options = [],
    placeholder = 'Wybierz...',
    style: extraStyle = {},
    disabled = false,
    dropUp = false,
}) {
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [open])

    const selected = options.find((o) => String(o.value) === String(value))
    const label = selected ? selected.label : placeholder

    const dropdownPos = dropUp
        ? { bottom: 'calc(100% + 4px)', left: 0, right: 0 }
        : { top: 'calc(100% + 4px)', left: 0, right: 0 }

    return (
        <div ref={ref} style={{ position: 'relative', ...extraStyle }}>
            <button
                type="button"
                onClick={() => !disabled && setOpen((o) => !o)}
                disabled={disabled}
                style={{
                    width: '100%',
                    height: 36,
                    padding: '0 30px 0 10px',
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: selected ? 500 : 400,
                    color: selected ? C.textPrimary : C.w40,
                    background: open ? C.w06 : C.w04,
                    border: `1px solid ${open ? 'rgba(79,142,247,0.4)' : C.w10}`,
                    outline: 'none',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    opacity: disabled ? 0.5 : 1,
                    transition: 'border-color 0.15s, background 0.15s',
                    textAlign: 'left',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                }}
                className="hover:bg-white/[0.06]"
            >
                {label}
            </button>
            <ChevronDown
                size={13}
                style={{
                    position: 'absolute',
                    right: 9,
                    top: '50%',
                    transform: `translateY(-50%) rotate(${open ? 180 : 0}deg)`,
                    color: C.w30,
                    pointerEvents: 'none',
                    transition: 'transform 0.15s',
                }}
            />
            {open && (
                <div style={{
                    position: 'absolute',
                    ...dropdownPos,
                    zIndex: 60,
                    background: C.surfaceElevated,
                    border: B.medium,
                    borderRadius: 8,
                    padding: 3,
                    boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
                    maxHeight: 220,
                    overflowY: 'auto',
                    minWidth: '100%',
                }}>
                    {options.map((opt) => {
                        const active = String(opt.value) === String(value)
                        return (
                            <button
                                type="button"
                                key={opt.value}
                                onClick={() => {
                                    onChange(opt.value)
                                    setOpen(false)
                                }}
                                style={{
                                    display: 'block',
                                    width: '100%',
                                    padding: '7px 10px',
                                    borderRadius: 6,
                                    fontSize: 12,
                                    fontWeight: active ? 500 : 400,
                                    color: active ? '#FFFFFF' : 'rgba(255,255,255,0.65)',
                                    background: active ? C.infoBg : 'transparent',
                                    border: 'none',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'background 0.1s',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                }}
                                className={!active ? 'hover:bg-white/[0.05]' : ''}
                            >
                                {opt.label}
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
