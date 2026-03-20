import { useState, useEffect, useCallback } from 'react'
import {
    getRecommendations,
    getRecommendationsSummary,
    applyRecommendation,
    dismissRecommendation,
} from '../api'

const DEFAULT_PARAMS = { status: 'pending' }

export function useRecommendations(clientId, { days } = {}) {
    const [recommendations, setRecommendations] = useState([])
    const [summary, setSummary] = useState({ high_priority: 0, medium: 0, total: 0 })
    const [loading, setLoading] = useState(true)
    const [queryParams, setQueryParams] = useState({ ...DEFAULT_PARAMS, ...(days ? { days } : {}) })

    const fetchRecs = useCallback(
        async (params = queryParams) => {
            if (!clientId) return
            try {
                setLoading(true)
                const normalized = { ...DEFAULT_PARAMS, ...params }
                const [recs, sum] = await Promise.all([
                    getRecommendations(clientId, normalized),
                    getRecommendationsSummary(clientId, normalized),
                ])
                setRecommendations(recs.recommendations || [])
                setSummary(sum || {})
            } catch (err) {
                console.error('Failed to fetch recommendations:', err)
            } finally {
                setLoading(false)
            }
        },
        [clientId, queryParams]
    )

    useEffect(() => {
        if (!clientId) return
        fetchRecs(queryParams)
    }, [clientId, queryParams, fetchRecs])

    const updateFilters = useCallback((params = {}) => {
        setQueryParams(prev => ({ ...prev, ...params }))
    }, [])

    const apply = async (recId, dryRun = false) => {
        return await applyRecommendation(recId, clientId, dryRun)
    }

    const dismiss = async (recId) => {
        await dismissRecommendation(recId, clientId)
        await fetchRecs(queryParams)
    }

    return {
        recommendations,
        summary,
        loading,
        refetch: fetchRecs,
        updateFilters,
        queryParams,
        apply,
        dismiss,
    }
}
