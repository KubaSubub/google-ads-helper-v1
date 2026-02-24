import { useState } from 'react';
import { useClients } from '../hooks/useClients';
import { useSync } from '../hooks/useSync';
import { useApp } from '../contexts/AppContext';
import SyncButton from '../components/SyncButton';
import EmptyState from '../components/EmptyState';
import { discoverClients } from '../api';
import { Users, Loader2, Download } from 'lucide-react';

export default function Clients() {
    const { clients, loading, refetch } = useClients();
    const { sync, syncing } = useSync();
    const { selectedClientId, setSelectedClientId, showToast } = useApp();
    const [discovering, setDiscovering] = useState(false);

    const handleSync = async (clientId) => {
        try {
            await sync(clientId);
            showToast('Synchronizacja zakończona', 'success');
            refetch();
        } catch {
            showToast('Błąd synchronizacji', 'error');
        }
    };

    const handleDiscover = async () => {
        setDiscovering(true);
        try {
            const result = await discoverClients();
            showToast(result.message, 'success');
            refetch();
        } catch (err) {
            showToast(err.message || 'Błąd pobierania klientów', 'error');
        } finally {
            setDiscovering(false);
        }
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 900 }}>
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                        Klienci
                    </h1>
                    <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                        Zarządzanie kontami Google Ads
                    </p>
                </div>
                <button
                    onClick={handleDiscover}
                    disabled={discovering}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '7px 16px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                        background: 'rgba(79,142,247,0.15)',
                        border: '1px solid rgba(79,142,247,0.3)',
                        color: '#4F8EF7', cursor: 'pointer',
                        opacity: discovering ? 0.5 : 1,
                        transition: 'all 0.15s',
                    }}
                >
                    {discovering
                        ? <Loader2 size={14} className="animate-spin" />
                        : <Download size={14} />
                    }
                    {discovering ? 'Pobieram...' : 'Pobierz klientów z Google Ads'}
                </button>
            </div>

            {!clients.length ? (
                <EmptyState
                    message="Brak klientów. Kliknij 'Pobierz klientów z Google Ads' aby zaimportować konta."
                    icon={Users}
                />
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {clients.map((client) => {
                        const isSelected = selectedClientId === client.id;
                        return (
                            <div
                                key={client.id}
                                className="v2-card"
                                onClick={() => setSelectedClientId(client.id)}
                                style={{
                                    padding: '14px 18px',
                                    cursor: 'pointer',
                                    borderColor: isSelected ? 'rgba(79,142,247,0.4)' : undefined,
                                    background: isSelected ? 'rgba(79,142,247,0.08)' : undefined,
                                    transition: 'all 0.15s',
                                }}
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="flex items-center gap-2" style={{ marginBottom: 3 }}>
                                            {isSelected && (
                                                <span style={{
                                                    width: 6, height: 6, borderRadius: '50%',
                                                    background: '#4ADE80',
                                                    boxShadow: '0 0 6px #4ade80',
                                                    flexShrink: 0,
                                                }} />
                                            )}
                                            <span style={{ fontSize: 14, fontWeight: 500, color: '#F0F0F0' }}>
                                                {client.name}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                                            ID: {client.google_customer_id}
                                            {client.last_synced_at && (
                                                <span style={{ marginLeft: 12 }}>
                                                    Ostatni sync: {new Date(client.last_synced_at).toLocaleString('pl-PL')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <SyncButton
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleSync(client.id);
                                        }}
                                        loading={syncing}
                                        lastSynced={client.last_synced_at}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
