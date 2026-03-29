import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Settings } from 'lucide-react'
import { useApp } from '../../../contexts/AppContext'

export default function ClientSelector({ onOpenDrawer }) {
    const { selectedClientId, setSelectedClientId, clients } = useApp()
    const selectedClient = clients.find((c) => c.id === selectedClientId)
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

    return (
        <div style={{ padding: '10px 12px 8px' }}>
            <div style={{
                fontSize: 10,
                color: 'rgba(255,255,255,0.3)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                padding: '0 2px 6px',
                fontWeight: 500,
            }}>
                Klient
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'stretch' }}>
                <div ref={ref} style={{ position: 'relative', flex: 1, minWidth: 0 }}>
                    <button
                        onClick={() => setOpen((o) => !o)}
                        style={{
                            width: '100%',
                            height: 38,
                            padding: '0 32px 0 12px',
                            borderRadius: 8,
                            fontSize: 13,
                            fontWeight: 500,
                            color: selectedClient ? '#FFFFFF' : 'rgba(255,255,255,0.4)',
                            background: open ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.04)',
                            border: `1px solid ${open ? 'rgba(79,142,247,0.4)' : 'rgba(255,255,255,0.08)'}`,
                            outline: 'none',
                            cursor: 'pointer',
                            transition: 'border-color 0.15s, background 0.15s',
                            textAlign: 'left',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                        }}
                        className="hover:bg-white/[0.06]"
                    >
                        {selectedClient ? selectedClient.name : 'Wybierz klienta...'}
                    </button>
                    <ChevronDown
                        size={14}
                        style={{
                            position: 'absolute',
                            right: 10,
                            top: '50%',
                            transform: `translateY(-50%) rotate(${open ? 180 : 0}deg)`,
                            color: 'rgba(255,255,255,0.3)',
                            pointerEvents: 'none',
                            transition: 'transform 0.15s',
                        }}
                    />
                    {open && (
                        <div style={{
                            position: 'absolute',
                            top: 'calc(100% + 4px)',
                            left: 0,
                            right: 0,
                            zIndex: 50,
                            background: '#1A1D24',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: 10,
                            padding: 4,
                            boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
                            maxHeight: 240,
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
                                            padding: '8px 10px',
                                            borderRadius: 7,
                                            fontSize: 12,
                                            fontWeight: active ? 500 : 400,
                                            color: active ? '#FFFFFF' : 'rgba(255,255,255,0.65)',
                                            background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
                                            border: 'none',
                                            cursor: 'pointer',
                                            textAlign: 'left',
                                            transition: 'background 0.1s',
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
                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {client.name}
                                        </span>
                                    </button>
                                )
                            })}
                        </div>
                    )}
                </div>
                <button
                    onClick={onOpenDrawer}
                    title="Zarządzanie klientami"
                    style={{
                        width: 38,
                        borderRadius: 8,
                        background: 'rgba(79,142,247,0.12)',
                        border: '1px solid rgba(79,142,247,0.25)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: '#4F8EF7',
                        flexShrink: 0,
                        transition: 'all 0.15s',
                    }}
                    className="hover:bg-[rgba(79,142,247,0.2)]"
                >
                    <Settings size={14} />
                </button>
            </div>
            {selectedClient && (
                <div style={{
                    fontSize: 10,
                    color: 'rgba(255,255,255,0.25)',
                    padding: '5px 4px 0',
                }}>
                    ID: {selectedClient.google_customer_id}
                </div>
            )}
        </div>
    )
}
