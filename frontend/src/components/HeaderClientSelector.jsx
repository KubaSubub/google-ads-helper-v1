import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Settings, Users } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import ClientDrawer from './layout/Sidebar/ClientDrawer'
import { C, B, TRANSITION } from '../constants/designTokens'

export default function HeaderClientSelector() {
    const { selectedClientId, setSelectedClientId, clients } = useApp()
    const selectedClient = clients.find((c) => c.id === selectedClientId)
    const [open, setOpen] = useState(false)
    const [drawerOpen, setDrawerOpen] = useState(false)
    const ref = useRef(null)

    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [open])

    return (
        <>
            <div ref={ref} style={{ position: 'relative' }}>
                <button
                    onClick={() => setOpen((o) => !o)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        height: 36,
                        padding: '0 12px',
                        borderRadius: 10,
                        fontSize: 13,
                        fontWeight: 500,
                        color: selectedClient ? '#FFFFFF' : C.w40,
                        background: open ? C.w06 : C.w04,
                        border: `1px solid ${open ? 'rgba(79,142,247,0.4)' : C.w08}`,
                        cursor: 'pointer',
                        transition: TRANSITION.fast,
                        maxWidth: 260,
                        minWidth: 180,
                    }}
                    className="hover:bg-white/[0.06]"
                >
                    <Users size={14} style={{ color: C.accentBlue, flexShrink: 0 }} />
                    <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {selectedClient ? selectedClient.name : 'Wybierz klienta...'}
                    </span>
                    <ChevronDown
                        size={13}
                        style={{
                            color: C.w40,
                            flexShrink: 0,
                            transform: open ? 'rotate(180deg)' : 'none',
                            transition: 'transform 0.15s',
                        }}
                    />
                </button>

                {open && (
                    <div style={{
                        position: 'absolute',
                        top: 'calc(100% + 6px)',
                        right: 0,
                        minWidth: 260,
                        zIndex: 60,
                        background: C.surfaceElevated,
                        border: B.medium,
                        borderRadius: 10,
                        padding: 4,
                        boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
                        maxHeight: 360,
                        overflowY: 'auto',
                    }}>
                        {clients.map((client) => {
                            const active = client.id === selectedClientId
                            return (
                                <button
                                    key={client.id}
                                    onClick={() => {
                                        setSelectedClientId(client.id)
                                        setOpen(false)
                                    }}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 8,
                                        width: '100%',
                                        padding: '9px 10px',
                                        borderRadius: 7,
                                        fontSize: 12,
                                        fontWeight: active ? 500 : 400,
                                        color: active ? '#FFFFFF' : C.w60,
                                        background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                                        border: 'none',
                                        cursor: 'pointer',
                                        textAlign: 'left',
                                    }}
                                    className={!active ? 'hover:bg-white/[0.05]' : ''}
                                >
                                    <span style={{
                                        width: 6,
                                        height: 6,
                                        borderRadius: '50%',
                                        flexShrink: 0,
                                        background: active ? '#4ADE80' : 'rgba(255,255,255,0.15)',
                                    }} />
                                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {client.name}
                                    </span>
                                    {client.google_customer_id && (
                                        <span style={{ fontSize: 10, color: C.w25, fontFamily: 'monospace', flexShrink: 0 }}>
                                            {client.google_customer_id}
                                        </span>
                                    )}
                                </button>
                            )
                        })}
                        <div style={{ borderTop: B.subtle, marginTop: 4, paddingTop: 4 }}>
                            <button
                                onClick={() => { setDrawerOpen(true); setOpen(false) }}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 8,
                                    width: '100%',
                                    padding: '9px 10px',
                                    borderRadius: 7,
                                    fontSize: 12,
                                    color: C.accentBlue,
                                    background: 'transparent',
                                    border: 'none',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                }}
                                className="hover:bg-white/[0.05]"
                            >
                                <Settings size={12} />
                                Zarządzaj klientami
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <ClientDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        </>
    )
}
