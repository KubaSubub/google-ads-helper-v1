import { useState, useEffect, useCallback } from 'react';
import {
    getRecommendations,
    getRecommendationsSummary,
    applyRecommendation,
    dismissRecommendation,
} from '../api';

export function useRecommendations(clientId) {
    const [recommendations, setRecommendations] = useState([]);
    const [summary, setSummary] = useState({ high: 0, medium: 0, total: 0 });
    const [loading, setLoading] = useState(true);

    const fetchRecs = useCallback(
        async (params = {}) => {
            if (!clientId) return;
            try {
                setLoading(true);
                const [recs, sum] = await Promise.all([
                    getRecommendations(clientId, { status: 'pending', ...params }),
                    getRecommendationsSummary(clientId),
                ]);
                setRecommendations(recs.recommendations || []);
                setSummary(sum);
            } catch (err) {
                console.error('Failed to fetch recommendations:', err);
            } finally {
                setLoading(false);
            }
        },
        [clientId]
    );

    useEffect(() => {
        fetchRecs();
    }, [fetchRecs]);

    const apply = async (recId, dryRun = false) => {
        return await applyRecommendation(recId, clientId, dryRun);
    };

    const dismiss = async (recId) => {
        await dismissRecommendation(recId);
        await fetchRecs();
    };

    return { recommendations, summary, loading, refetch: fetchRecs, apply, dismiss };
}
