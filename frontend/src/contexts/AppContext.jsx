import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getAuthStatus } from '../api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [selectedClientId, setSelectedClientId] = useState(() => {
        const saved = localStorage.getItem('selectedClientId');
        return saved ? parseInt(saved, 10) : null;
    });
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

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

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
