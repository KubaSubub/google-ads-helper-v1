import { useState, useRef, useEffect } from 'react'
import { Keyboard } from 'lucide-react'
import { NAV_GROUPS } from './layout/Sidebar/navConfig'
import { C, T, S, R, B, PILL, MODAL, TOOLTIP_STYLE, SEVERITY, TRANSITION, FONT } from '../constants/designTokens'

/**
 * Build shortcut entries from nav config — maps keys 1-9 to sidebar items in order.
 */
function buildShortcutEntries() {
    const entries = []
    let index = 1
    for (const group of NAV_GROUPS) {
        for (const item of group.items) {
            if (index <= 9) {
                entries.push({ key: String(index), label: item.label })
            }
            index++
        }
    }
    return entries
}

const NAV_SHORTCUTS = buildShortcutEntries()

const EXTRA_SHORTCUTS = [
    { key: '/', label: 'Fokus na wyszukiwarkę' },
    { key: 'Esc', label: 'Wróć / odznacz' },
]

export default function ShortcutsHint() {
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    // Close on outside click
    useEffect(() => {
        if (!open) return
        function handleClick(e) {
            if (ref.current && !ref.current.contains(e.target)) {
                setOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [open])

    // Close on Escape
    useEffect(() => {
        if (!open) return
        function handleKey(e) {
            if (e.key === 'Escape') {
                setOpen(false)
            }
        }
        document.addEventListener('keydown', handleKey)
        return () => document.removeEventListener('keydown', handleKey)
    }, [open])

    return (
        <div ref={ref} style={{ position: 'relative' }}>
            <button
                onClick={() => setOpen((v) => !v)}
                title="Skróty klawiszowe"
                style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    border: B.medium,
                    background: open ? C.w08 : C.w03,
                    color: open ? C.w80 : C.w40,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                    if (!open) {
                        e.currentTarget.style.background = C.w06
                        e.currentTarget.style.color = C.w60
                    }
                }}
                onMouseLeave={(e) => {
                    if (!open) {
                        e.currentTarget.style.background = C.w03
                        e.currentTarget.style.color = C.w40
                    }
                }}
            >
                <Keyboard size={15} />
            </button>

            {open && (
                <div
                    style={{
                        position: 'absolute',
                        top: 'calc(100% + 8px)',
                        right: 0,
                        width: 280,
                        background: 'rgba(17, 19, 24, 0.97)',
                        backdropFilter: 'blur(16px)',
                        border: B.card,
                        borderRadius: 12,
                        padding: '14px 0',
                        zIndex: 100,
                        boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
                    }}
                >
                    {/* Header */}
                    <div
                        style={{
                            padding: '0 16px 10px',
                            borderBottom: B.card,
                            marginBottom: 8,
                        }}
                    >
                        <div
                            style={{
                                fontSize: 11,
                                fontWeight: 600,
                                color: C.w60,
                                textTransform: 'uppercase',
                                letterSpacing: '0.08em',
                                fontFamily: 'Syne, sans-serif',
                            }}
                        >
                            Skróty klawiszowe
                        </div>
                    </div>

                    {/* Navigation shortcuts */}
                    <div style={{ padding: '0 12px' }}>
                        <div
                            style={{
                                fontSize: 9,
                                fontWeight: 500,
                                color: C.w30,
                                textTransform: 'uppercase',
                                letterSpacing: '0.1em',
                                padding: '4px 4px 6px',
                            }}
                        >
                            Nawigacja
                        </div>
                        {NAV_SHORTCUTS.map(({ key, label }) => (
                            <ShortcutRow key={key} shortcutKey={key} label={label} />
                        ))}
                    </div>

                    {/* Separator */}
                    <div style={{ height: 1, background: C.w05, margin: '8px 12px' }} />

                    {/* Extra shortcuts */}
                    <div style={{ padding: '0 12px' }}>
                        <div
                            style={{
                                fontSize: 9,
                                fontWeight: 500,
                                color: C.w30,
                                textTransform: 'uppercase',
                                letterSpacing: '0.1em',
                                padding: '4px 4px 6px',
                            }}
                        >
                            Ogólne
                        </div>
                        {EXTRA_SHORTCUTS.map(({ key, label }) => (
                            <ShortcutRow key={key} shortcutKey={key} label={label} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

function ShortcutRow({ shortcutKey, label }) {
    return (
        <div
            style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '4px 4px',
            }}
        >
            <span style={{ fontSize: 12, color: C.textSecondary, fontFamily: 'DM Sans, sans-serif' }}>
                {label}
            </span>
            <kbd
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: 24,
                    height: 22,
                    padding: '0 6px',
                    borderRadius: 6,
                    background: C.w06,
                    border: B.medium,
                    fontSize: 11,
                    fontWeight: 500,
                    color: C.textPlaceholder,
                    fontFamily: 'DM Sans, monospace',
                }}
            >
                {shortcutKey}
            </kbd>
        </div>
    )
}
