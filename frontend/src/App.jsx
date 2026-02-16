import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Campaigns from './pages/Campaigns'
import SearchTerms from './pages/SearchTerms'
import Keywords from './pages/Keywords'
import Anomalies from './pages/Anomalies'
import Settings from './pages/Settings'
import Semantic from './pages/Semantic'
import Recommendations from './pages/Recommendations'
import QualityScore from './pages/QualityScore'
import Forecast from './pages/Forecast'

export default function App() {
    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8 pt-16 lg:pt-8">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/campaigns" element={<Campaigns />} />
                    <Route path="/search-terms" element={<SearchTerms />} />
                    <Route path="/keywords" element={<Keywords />} />
                    <Route path="/anomalies" element={<Anomalies />} />
                    <Route path="/semantic" element={<Semantic />} />
                    <Route path="/recommendations" element={<Recommendations />} />
                    <Route path="/quality-score" element={<QualityScore />} />
                    <Route path="/forecast" element={<Forecast />} />
                    <Route path="/settings" element={<Settings />} />
                </Routes>
            </main>
        </div>
    )
}
