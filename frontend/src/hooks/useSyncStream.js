import { useState, useRef, useCallback } from 'react'

/**
 * Hook for SSE-based sync streaming.
 * Reuses the SSE pattern from Agent.jsx (fetch + getReader + event parsing).
 */
export function useSyncStream() {
    const [state, setState] = useState('idle') // idle | syncing | done | error
    const [phases, setPhases] = useState([])   // [{phase, label, index, total, status, count, error, reason, dateFrom, dateTo}]
    const [currentPhase, setCurrentPhase] = useState(null)
    const [progress, setProgress] = useState(0)
    const [eta, setEta] = useState(null)
    const [elapsed, setElapsed] = useState(0)
    const [result, setResult] = useState(null) // final done event data
    const [errorMsg, setErrorMsg] = useState(null)
    const abortRef = useRef(null)

    const reset = useCallback(() => {
        setState('idle')
        setPhases([])
        setCurrentPhase(null)
        setProgress(0)
        setEta(null)
        setElapsed(0)
        setResult(null)
        setErrorMsg(null)
    }, [])

    const startSync = useCallback(async (clientId, config = {}) => {
        reset()
        setState('syncing')

        const params = new URLSearchParams()
        params.set('client_id', clientId)
        if (config.preset) params.set('preset', config.preset)
        if (config.phases) params.set('phases', config.phases.join(','))
        if (config.dateFrom) params.set('date_from', config.dateFrom)
        if (config.dateTo) params.set('date_to', config.dateTo)

        const abortCtrl = new AbortController()
        abortRef.current = abortCtrl

        try {
            const response = await fetch(`/api/v1/sync/trigger-stream?${params.toString()}`, {
                method: 'POST',
                credentials: 'include',
                signal: abortCtrl.signal,
            })

            if (!response.ok) {
                if (response.status === 401) {
                    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
                }
                throw new Error(`Błąd serwera: ${response.status}`)
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const parts = buffer.split('\n\n')
                buffer = parts.pop()

                for (const part of parts) {
                    const lines = part.trim().split('\n')
                    let eventType = ''
                    let eventData = ''

                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim()
                        } else if (line.startsWith('data: ')) {
                            eventData = line.slice(6).replace(/\\n/g, '\n')
                        }
                    }

                    if (!eventType || !eventData) continue

                    let data
                    try { data = JSON.parse(eventData) } catch { continue }

                    switch (eventType) {
                        case 'sync_start':
                            setPhases(data.phases.map((p, i) => ({
                                phase: p,
                                label: p,
                                index: i + 1,
                                total: data.total_phases,
                                status: 'pending',
                            })))
                            break

                        case 'phase_start':
                            setCurrentPhase(data.phase)
                            setPhases(prev => prev.map(p =>
                                p.phase === data.phase
                                    ? { ...p, status: 'running', label: data.label, dateFrom: data.date_from, dateTo: data.date_to }
                                    : p
                            ))
                            break

                        case 'phase_done':
                            setPhases(prev => prev.map(p =>
                                p.phase === data.phase
                                    ? { ...p, status: 'done', count: data.count }
                                    : p
                            ))
                            break

                        case 'phase_error':
                            setPhases(prev => prev.map(p =>
                                p.phase === data.phase
                                    ? { ...p, status: 'error', error: data.error }
                                    : p
                            ))
                            break

                        case 'phase_skip':
                            setPhases(prev => prev.map(p =>
                                p.phase === data.phase
                                    ? { ...p, status: 'skipped', reason: data.reason, label: data.label }
                                    : p
                            ))
                            break

                        case 'progress':
                            setProgress(data.percent)
                            setEta(data.eta_seconds)
                            setElapsed(data.elapsed_seconds)
                            break

                        case 'done':
                            setResult(data)
                            setState('done')
                            setCurrentPhase(null)
                            setProgress(100)
                            break

                        case 'error':
                            setErrorMsg(data.message)
                            setState('error')
                            break
                    }
                }
            }

            // If we finished reading but state wasn't set to done/error
            setState(prev => prev === 'syncing' ? 'done' : prev)

        } catch (err) {
            if (err.name === 'AbortError') {
                setState('idle')
                setErrorMsg('Synchronizacja anulowana')
            } else {
                setState('error')
                setErrorMsg(err.message)
            }
        }
    }, [reset])

    const cancel = useCallback(() => {
        abortRef.current?.abort()
    }, [])

    return {
        state,
        phases,
        currentPhase,
        progress,
        eta,
        elapsed,
        result,
        errorMsg,
        startSync,
        cancel,
        reset,
    }
}
