import { Routes, Route } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './contexts/AppContext';
import { FilterProvider } from './contexts/FilterContext';
import Toast from './components/Toast';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Campaigns from './pages/Campaigns';
import SearchTerms from './pages/SearchTerms';
import Keywords from './pages/Keywords';
import Settings from './pages/Settings';
import Semantic from './pages/Semantic';
import Recommendations from './pages/Recommendations';
import QualityScore from './pages/QualityScore';
import Forecast from './pages/Forecast';
import Clients from './pages/Clients';
import ActionHistory from './pages/ActionHistory';
import Alerts from './pages/Alerts';
import SearchOptimization from './pages/SearchOptimization';
import { Loader2 } from 'lucide-react';

function AppContent() {
    const {
        toast,
        hideToast,
        isAuthenticated,
        isConfigured,
        authMissing,
        authChecking,
        checkAuth,
    } = useApp();

    if (authChecking) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-surface-900">
                <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
            </div>
        );
    }

    if (!isAuthenticated || !isConfigured) {
        return <Login onAuthComplete={checkAuth} authMissing={authMissing} />;
    }

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8 pt-16 lg:pt-8">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/campaigns" element={<Campaigns />} />
                    <Route path="/search-terms" element={<SearchTerms />} />
                    <Route path="/keywords" element={<Keywords />} />
                    <Route path="/anomalies" element={<Navigate to="/alerts" replace />} />
                    <Route path="/semantic" element={<Semantic />} />
                    <Route path="/recommendations" element={<Recommendations />} />
                    <Route path="/quality-score" element={<QualityScore />} />
                    <Route path="/forecast" element={<Forecast />} />
                    <Route path="/clients" element={<Clients />} />
                    <Route path="/action-history" element={<ActionHistory />} />
                    <Route path="/alerts" element={<Alerts />} />
                    <Route path="/search-optimization" element={<SearchOptimization />} />
                    <Route path="/settings" element={<Settings />} />
                </Routes>
            </main>
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
