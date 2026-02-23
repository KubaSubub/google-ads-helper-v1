import { RefreshCw } from 'lucide-react';

export default function SyncButton({ onClick, loading = false, lastSynced }) {
    return (
        <div className="flex items-center gap-2">
            <button
                onClick={onClick}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-app-accent/20 text-app-accent rounded-lg hover:bg-app-accent/30 disabled:opacity-50"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Synchronizacja...' : 'Synchronizuj'}
            </button>
            {lastSynced && (
                <span className="text-xs text-app-muted">
                    Ostatnia: {new Date(lastSynced).toLocaleString('pl-PL')}
                </span>
            )}
        </div>
    );
}
