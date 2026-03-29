import { useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { NAV_GROUPS } from '../components/layout/Sidebar/navConfig'

/**
 * Builds a flat list of nav routes in sidebar order (1-indexed).
 * Skips type-filtered items — all routes are always reachable via keyboard.
 */
function buildRouteList() {
    const routes = []
    for (const group of NAV_GROUPS) {
        for (const item of group.items) {
            routes.push(item.to)
        }
    }
    return routes
}

const ROUTES = buildRouteList()

function isEditableElement(el) {
    if (!el) return false
    const tag = el.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
    if (el.isContentEditable) return true
    return false
}

/**
 * Keyboard shortcuts for page navigation.
 *
 * - Keys 1-9: navigate to pages in sidebar order
 * - `/` (slash): focus the first visible search input on the page
 * - Escape: go back (history.back) when not on a root page
 */
export function useKeyboardShortcuts() {
    const navigate = useNavigate()
    const location = useLocation()

    const handleKeyDown = useCallback(
        (e) => {
            // Ignore when typing in form fields
            if (isEditableElement(e.target)) return

            // Ignore when modifier keys are held (Ctrl+1, Alt+1, etc.)
            if (e.ctrlKey || e.altKey || e.metaKey) return

            const key = e.key

            // Number keys 1-9: navigate to page by sidebar index
            if (key >= '1' && key <= '9') {
                const index = parseInt(key, 10) - 1
                if (index < ROUTES.length) {
                    e.preventDefault()
                    navigate(ROUTES[index])
                }
                return
            }

            // Slash: focus search input
            if (key === '/') {
                const searchInput =
                    document.querySelector('input[type="search"]') ||
                    document.querySelector('input[placeholder*="Szukaj"]') ||
                    document.querySelector('input[placeholder*="szukaj"]') ||
                    document.querySelector('input[placeholder*="Search"]') ||
                    document.querySelector('input[placeholder*="Filtruj"]')
                if (searchInput) {
                    e.preventDefault()
                    searchInput.focus()
                }
                return
            }

            // Escape: go back
            if (key === 'Escape') {
                // Don't intercept Escape if a modal/popover might be open
                // Only navigate back if not on a root-level page
                const rootPaths = ['/', '/daily-audit', '/campaigns', '/keywords', '/search-terms',
                    '/recommendations', '/quality-score', '/settings', '/alerts',
                    '/action-history', '/audit-center', '/agent', '/reports',
                    '/shopping', '/pmax', '/display', '/video', '/competitive',
                    '/forecast', '/semantic']
                if (!rootPaths.includes(location.pathname)) {
                    e.preventDefault()
                    window.history.back()
                    return
                }
                // Also unfocus active element on Escape
                if (document.activeElement && document.activeElement !== document.body) {
                    e.preventDefault()
                    document.activeElement.blur()
                }
                return
            }

            // Question mark: toggle shortcuts overlay (handled by ShortcutsHint)
            // We don't handle it here — the button in the header manages its own state.
        },
        [navigate, location.pathname]
    )

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown)
        return () => document.removeEventListener('keydown', handleKeyDown)
    }, [handleKeyDown])

    return { routes: ROUTES }
}
