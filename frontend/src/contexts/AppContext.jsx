import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getAuthStatus, getClients } from '../api';

const AppContext = createContext(null);

const DEFAULT_AUTH_STATUS = {
    authenticated: false,
    configured: false,
    ready: false,
    reason: '',
    missing: [],
    missing_credentials: [],
};

export function AppProvider({ children }) {
    const [selectedClientId, setSelectedClientId] = useState(() => {
        const saved = localStorage.getItem('selectedClientId');
        return saved ? parseInt(saved, 10) : null;
    });
    const [clients, setClients] = useState([]);
    const [clientsLoading, setClientsLoading] = useState(true);
    const [alertCount, setAlertCount] = useState(0);
    const [toast, setToast] = useState(null);
    const [authStatus, setAuthStatus] = useState(DEFAULT_AUTH_STATUS);
    const [authChecking, setAuthChecking] = useState(true);

    const checkAuth = useCallback(async () => {
        const maxWaitMs = 30000;
        const intervalMs = 1000;
        const started = Date.now();

        while (Date.now() - started < maxWaitMs) {
            try {
                const data = await getAuthStatus(true);
                const nextStatus = { ...DEFAULT_AUTH_STATUS, ...data };
                setAuthStatus(nextStatus);
                setAuthChecking(false);
                return nextStatus;
            } catch (err) {
                if (err.status && err.status < 500) break;
                await new Promise((resolve) => setTimeout(resolve, intervalMs));
            }
        }

        setAuthStatus(DEFAULT_AUTH_STATUS);
        setAuthChecking(false);
        return DEFAULT_AUTH_STATUS;
    }, []);

    const refreshClients = useCallback(async () => {
        try {
            setClientsLoading(true);
            const data = await getClients();
            const list = Array.isArray(data) ? data : data.items || [];
            setClients(list);
            return list;
        } catch (err) {
            console.error('Failed to load clients:', err);
            return [];
        } finally {
            setClientsLoading(false);
        }
    }, []);

    const markUnauthorized = useCallback(() => {
        setAuthStatus(DEFAULT_AUTH_STATUS);
        setClients([]);
        setClientsLoading(false);
        localStorage.removeItem('selectedClientId');
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        const onUnauthorized = () => markUnauthorized();
        window.addEventListener('auth:unauthorized', onUnauthorized);
        return () => window.removeEventListener('auth:unauthorized', onUnauthorized);
    }, [markUnauthorized]);

    useEffect(() => {
        if (authStatus.ready) {
            refreshClients();
            return;
        }
        setClients([]);
        setClientsLoading(false);
    }, [authStatus.ready, refreshClients]);

    useEffect(() => {
        if (selectedClientId) {
            localStorage.setItem('selectedClientId', String(selectedClientId));
        } else {
            localStorage.removeItem('selectedClientId');
        }
    }, [selectedClientId]);

    const showToast = useCallback((message, type = 'success', duration) => {
        const id = Date.now();
        setToast({ message, type, id });
        // Errors persist until manual dismiss (X click) so user can read them.
        // Success/info auto-dismiss after duration (default 3s).
        const effectiveDuration = duration ?? (type === 'error' ? 0 : 3000);
        if (effectiveDuration > 0) {
            setTimeout(() => setToast(prev => (prev?.id === id ? null : prev)), effectiveDuration);
        }
    }, []);

    const hideToast = useCallback(() => setToast(null), []);

    return (
        <AppContext.Provider
            value={{
                selectedClientId,
                setSelectedClientId,
                clients,
                clientsLoading,
                refreshClients,
                alertCount,
                setAlertCount,
                toast,
                showToast,
                hideToast,
                isAuthenticated: authStatus.authenticated,
                authStatus,
                authChecking,
                checkAuth,
            }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be inside AppProvider');
    return ctx;
}
