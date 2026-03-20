import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider, useApp } from './contexts/AppContext';
import { FilterProvider } from './contexts/FilterContext';
import Toast from './components/Toast';
import Sidebar from './components/Sidebar';
import GlobalFilterBar from './components/GlobalFilterBar';
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
import Agent from './pages/Agent';
import Reports from './pages/Reports';
import DailyAudit from './pages/DailyAudit';
import { Loader2 } from 'lucide-react';

const GLOBAL_FILTER_ROUTES = ['/', '/campaigns', '/keywords', '/search-terms', '/search-optimization', '/recommendations'];

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
            <main className="flex-1 overflow-y-auto p-6 lg:p-8 pt-16 lg:pt-8">
                {showGlobalFilter && <GlobalFilterBar />}
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/daily-audit" element={<DailyAudit />} />
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
                    <Route path="/agent" element={<Agent />} />
                    <Route path="/reports" element={<Reports />} />
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
