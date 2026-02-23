import { useState, useEffect, useCallback } from 'react';
import { getAnomalies } from '../api';

export function useAlerts(clientId) {
    const [alertCount, setAlertCount] = useState(0);

    const fetchCount = useCallback(async () => {
        if (!clientId) return;
        try {
            const data = await getAnomalies(clientId, 'unresolved');
            setAlertCount(data.length || 0);
        } catch {
            setAlertCount(0);
        }
    }, [clientId]);

    useEffect(() => {
        fetchCount();
    }, [fetchCount]);

    return { alertCount, refetchAlerts: fetchCount };
}
