import { useNavigate } from 'react-router-dom'
import { useCallback } from 'react'

/**
 * Centralized navigation hook for cross-tab links.
 * Usage: const navigateTo = useNavigateTo()
 *        navigateTo('keywords', { campaign_id: 5, campaign_name: 'Search A' })
 */
export function useNavigateTo() {
    const navigate = useNavigate()
    return useCallback((tab, filters = {}) => {
        const clean = Object.fromEntries(
            Object.entries(filters).filter(([, v]) => v != null && v !== '')
        )
        const params = new URLSearchParams(clean).toString()
        navigate(params ? `/${tab}?${params}` : `/${tab}`)
    }, [navigate])
}
