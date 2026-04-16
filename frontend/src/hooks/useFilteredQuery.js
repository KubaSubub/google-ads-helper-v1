import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import { useApp } from '../contexts/AppContext'
import { useFilter } from '../contexts/FilterContext'

/**
 * Canonical data-fetch hook: injects `client_id` from AppContext and
 * `date_from/date_to/campaign_type/campaign_status` from FilterContext.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useFilteredQuery('/campaigns/', {
 *       extraParams: { page: 1, page_size: 50 },
 *   })
 *
 * Params merge order (later wins):
 *   client_id -> allParams (dates + campaign filters) -> extraParams
 *
 * `extraParams` should never include filter-managed keys (client_id, date_from,
 * date_to, campaign_type, campaign_status). If it does, callers are bypassing
 * the contract.
 */
export function useFilteredQuery(path, { extraParams, enabled = true } = {}) {
    const { selectedClientId } = useApp()
    const { allParams } = useFilter()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    const extraKey = JSON.stringify(extraParams || {})

    const refetch = useCallback(async () => {
        if (!enabled) return
        if (selectedClientId == null) {
            setData(null)
            return
        }
        setLoading(true)
        setError(null)
        try {
            const params = { client_id: selectedClientId, ...allParams, ...(extraParams || {}) }
            const res = await api.get(path, { params })
            setData(res)
        } catch (e) {
            setError(e)
        } finally {
            setLoading(false)
        }
    }, [path, enabled, selectedClientId, allParams, extraKey])

    useEffect(() => {
        refetch()
    }, [refetch])

    return { data, loading, error, refetch }
}
