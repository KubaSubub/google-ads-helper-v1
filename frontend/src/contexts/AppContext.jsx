import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getAuthStatus, getClients } from '../api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [selectedClientId, setSelectedClientId] = useState(() => {
        const saved = localStorage.getItem('selectedClientId');
        return saved ? parseInt(saved, 10) : null;
    });
    const [clients, setClients] = useState([]);
    const [clientsLoading, setClientsLoading] = useState(true);
    const [alertCount, setAlertCount] = useState(0);
    const [toast, setToast] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(null);
    const [authChecking, setAuthChecking] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const data = await getAuthStatus();
            setIsAuthenticated(data.authenticated);
        } catch {
            setIsAuthenticated(false);
        } finally {
            setAuthChecking(false);
        }
    }, []);

    const refreshClients = useCallback(async () => {
        try {
            setClientsLoading(true);
            const data = await getClients();
            const list = Array.isArray(data) ? data : data.items || [];
            setClients(list);
            return list;
        } catch {
            return [];
        } finally {
            setClientsLoading(false);
        }
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    // Load clients once auth is confirmed
    useEffect(() => {
        if (isAuthenticated) refreshClients();
    }, [isAuthenticated, refreshClients]);

    useEffect(() => {
        if (selectedClientId) {
            localStorage.setItem('selectedClientId', String(selectedClientId));
        }
    }, [selectedClientId]);

    const showToast = useCallback((message, type = 'success', duration = 3000) => {
        setToast({ message, type, id: Date.now() });
        setTimeout(() => setToast(null), duration);
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
                isAuthenticated,
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
