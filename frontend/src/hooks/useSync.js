import { useState } from 'react';
import { syncClient } from '../api';

export function useSync() {
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState(null);

    const sync = async (clientId) => {
        try {
            setSyncing(true);
            setError(null);
            const result = await syncClient(clientId);
            return result;
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setSyncing(false);
        }
    };

    return { sync, syncing, error };
}
