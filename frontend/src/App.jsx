import { Suspense } from 'react';
import { Routes, useLocation } from 'react-router-dom';
import { AppProvider, useApp } from './contexts/AppContext';
import { FilterProvider } from './contexts/FilterContext';
import Toast from './components/Toast';
import Sidebar from './components/Sidebar';
import GlobalFilterBar from './components/GlobalFilterBar';
import GlobalDatePicker from './components/GlobalDatePicker';
import Login from './pages/Login';
import { Loader2 } from 'lucide-react';
import { AppRoutes, GLOBAL_FILTER_ROUTES } from './app/routes';

function LoadingFallback() {
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '80px 0' }}>
            <Loader2 size={28} style={{ color: '#4F8EF7' }} className="animate-spin" />
        </div>
    );
}

function AppContent() {
    const { toast, hideToast, authStatus, authChecking, checkAuth } = useApp();
    const location = useLocation();
    const showGlobalFilter = GLOBAL_FILTER_ROUTES.includes(location.pathname);

    if (authChecking) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-surface-900">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
            </div>
        );
    }

    if (!authStatus.ready) {
        return <Login onAuthComplete={checkAuth} initialAuthStatus={authStatus} />;
    }

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <header
                    className="hidden lg:flex"
                    style={{
                        height: 56,
                        flexShrink: 0,
                        alignItems: 'center',
                        justifyContent: 'flex-end',
                        padding: '0 32px',
                        borderBottom: '1px solid rgba(255,255,255,0.07)',
                        background: '#0D0F14',
                    }}
                >
                    <GlobalDatePicker />
                </header>
                <main className="flex-1 overflow-y-auto p-6 lg:p-8 pt-16 lg:pt-8">
                    {showGlobalFilter && <GlobalFilterBar />}
                    <Suspense fallback={<LoadingFallback />}>
                        <Routes>
                            <AppRoutes />
                        </Routes>
                    </Suspense>
                </main>
            </div>
            <Toast toast={toast} onClose={hideToast} />
        </div>
    );
}

export default function App() {
    return (
        <AppProvider>
            <FilterProvider>
                <AppContent />
            </FilterProvider>
        </AppProvider>
    );
}
