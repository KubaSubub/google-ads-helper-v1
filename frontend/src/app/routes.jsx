import { lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

// Lazy-loaded page components
const MCCOverview = lazy(() => import('../features/mcc-overview'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const DailyAudit = lazy(() => import('../pages/DailyAudit'))
const Campaigns = lazy(() => import('../pages/Campaigns'))
const SearchTerms = lazy(() => import('../pages/SearchTerms'))
const Keywords = lazy(() => import('../pages/Keywords'))
const Semantic = lazy(() => import('../pages/Semantic'))
const Recommendations = lazy(() => import('../pages/Recommendations'))
const QualityScore = lazy(() => import('../pages/QualityScore'))
const Forecast = lazy(() => import('../pages/Forecast'))
const ActionHistory = lazy(() => import('../pages/ActionHistory'))
const Alerts = lazy(() => import('../pages/Alerts'))
const AuditCenter = lazy(() => import('../features/audit-center'))
const Agent = lazy(() => import('../pages/Agent'))
const Reports = lazy(() => import('../pages/Reports'))
const Settings = lazy(() => import('../pages/Settings'))

// New campaign-type pages
const Shopping = lazy(() => import('../features/shopping'))
const PMax = lazy(() => import('../features/pmax'))
const Display = lazy(() => import('../features/display'))
const Video = lazy(() => import('../features/video'))
const Competitive = lazy(() => import('../features/competitive'))
const CrossCampaign = lazy(() => import('../features/cross-campaign'))
const Benchmarks = lazy(() => import('../features/benchmarks'))
const TaskQueue = lazy(() => import('../features/task-queue'))
const Rules = lazy(() => import('../features/rules'))
const Dsa = lazy(() => import('../features/dsa'))

export const GLOBAL_FILTER_ROUTES = [
    '/campaigns', '/keywords', '/search-terms', '/audit-center',
    '/recommendations', '/shopping', '/pmax', '/display', '/video', '/competitive',
    '/cross-campaign', '/benchmarks', '/dsa',
]

export function AppRoutes() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/mcc-overview" replace />} />
            <Route path="/mcc-overview" element={<MCCOverview />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/daily-audit" element={<DailyAudit />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/search-terms" element={<SearchTerms />} />
            <Route path="/keywords" element={<Keywords />} />
            <Route path="/anomalies" element={<Navigate to="/alerts" replace />} />
            <Route path="/semantic" element={<Semantic />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/quality-score" element={<QualityScore />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/clients" element={<Navigate to="/mcc-overview" replace />} />
            <Route path="/action-history" element={<ActionHistory />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/audit-center" element={<AuditCenter />} />
            <Route path="/search-optimization" element={<Navigate to="/audit-center" replace />} />
            <Route path="/agent" element={<Agent />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/shopping" element={<Shopping />} />
            <Route path="/pmax" element={<PMax />} />
            <Route path="/display" element={<Display />} />
            <Route path="/video" element={<Video />} />
            <Route path="/competitive" element={<Competitive />} />
            <Route path="/cross-campaign" element={<CrossCampaign />} />
            <Route path="/benchmarks" element={<Benchmarks />} />
            <Route path="/tasks" element={<TaskQueue />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/dsa" element={<Dsa />} />
        </Routes>
    )
}
