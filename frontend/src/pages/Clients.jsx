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
            <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-app-muted" />
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold text-app-text">Klienci</h1>
                <button
                    onClick={handleDiscover}
                    disabled={discovering}
                    className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                    {discovering ? (
                        <Loader2 size={16} className="animate-spin" />
                    ) : (
                        <Download size={16} />
                    )}
                    {discovering ? 'Pobieram...' : 'Pobierz klientów z Google Ads'}
                </button>
            </div>

            {!clients.length ? (
                <EmptyState
                    message="Brak klientów. Kliknij 'Pobierz klientów z Google Ads' aby zaimportować konta."
                    icon={Users}
                />
            ) : (
                <div className="grid gap-4">
                    {clients.map((client) => (
                        <div
                            key={client.id}
                            className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                                selectedClientId === client.id
                                    ? 'border-app-accent bg-app-accent/10'
                                    : 'border-white/10 bg-app-card hover:border-white/20'
                            }`}
                            onClick={() => setSelectedClientId(client.id)}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="font-medium text-app-text">{client.name}</h3>
                                    <p className="text-xs text-app-muted">
                                        ID: {client.google_customer_id}
                                    </p>
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
                    ))}
                </div>
            )}
        </div>
    );
}
