import { useState, useRef, useEffect } from 'react'
import { Keyboard } from 'lucide-react'
import { NAV_GROUPS } from './layout/Sidebar/navConfig'

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
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: open ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
                    color: open ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                    if (!open) {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                        e.currentTarget.style.color = 'rgba(255,255,255,0.6)'
                    }
                }}
                onMouseLeave={(e) => {
                    if (!open) {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                        e.currentTarget.style.color = 'rgba(255,255,255,0.4)'
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
                        border: '1px solid rgba(255,255,255,0.07)',
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
                            borderBottom: '1px solid rgba(255,255,255,0.07)',
                            marginBottom: 8,
                        }}
                    >
                        <div
                            style={{
                                fontSize: 11,
                                fontWeight: 600,
                                color: 'rgba(255,255,255,0.6)',
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
                                color: 'rgba(255,255,255,0.3)',
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
                    <div style={{ height: 1, background: 'rgba(255,255,255,0.05)', margin: '8px 12px' }} />

                    {/* Extra shortcuts */}
                    <div style={{ padding: '0 12px' }}>
                        <div
                            style={{
                                fontSize: 9,
                                fontWeight: 500,
                                color: 'rgba(255,255,255,0.3)',
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
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', fontFamily: 'DM Sans, sans-serif' }}>
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
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    fontSize: 11,
                    fontWeight: 500,
                    color: 'rgba(255,255,255,0.45)',
                    fontFamily: 'DM Sans, monospace',
                }}
            >
                {shortcutKey}
            </kbd>
        </div>
    )
}
