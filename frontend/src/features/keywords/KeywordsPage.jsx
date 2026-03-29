import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Award, Lightbulb, List, Shield } from 'lucide-react'

import EmptyState from '../../components/EmptyState'
import { useApp } from '../../contexts/AppContext'
import { useFilter } from '../../contexts/FilterContext'

import PositiveKeywordsTab from './components/PositiveKeywordsTab'
import NegativeKeywordsTab from './components/NegativeKeywordsTab'
import NegativeKeywordListsTab from './components/NegativeKeywordListsTab'
import KeywordExpansionTab from './components/KeywordExpansionTab'
import { TAB_STYLE } from './components/shared'

export default function KeywordsPage() {
    const { selectedClientId, showToast } = useApp()
    const { filters } = useFilter()
    const [searchParams, setSearchParams] = useSearchParams()
    const [activeTab, setActiveTab] = useState('positive')
    const navigate = useNavigate()

    if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />

    return (
        <div style={{ maxWidth: 1480 }}>
            <div className="flex items-center justify-between flex-wrap gap-4" style={{ marginBottom: 20 }}>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: '#F0F0F0', fontFamily: 'Syne', lineHeight: 1.2 }}>
                    Słowa kluczowe
                </h1>
                <div className="flex items-center gap-2">
                    <button onClick={() => setActiveTab('positive')} style={TAB_STYLE(activeTab === 'positive')}>
                        Słowa kluczowe
                    </button>
                    <button onClick={() => setActiveTab('negative')} style={TAB_STYLE(activeTab === 'negative')}>
                        <Shield size={13} /> Wykluczenia
                    </button>
                    <button onClick={() => setActiveTab('lists')} style={TAB_STYLE(activeTab === 'lists')}>
                        <List size={13} /> Listy
                    </button>
                    <button onClick={() => setActiveTab('expansion')} style={TAB_STYLE(activeTab === 'expansion')}>
                        <Lightbulb size={13} /> Ekspansja
                    </button>
                    <button onClick={() => navigate('/quality-score')} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 12px', borderRadius: 7, fontSize: 11, fontWeight: 500, background: 'rgba(123,92,224,0.08)', border: '1px solid rgba(123,92,224,0.2)', color: '#7B5CE0', cursor: 'pointer', marginLeft: 8 }}>
                        <Award size={12} /> Audyt QS
                    </button>
                </div>
            </div>

            {activeTab === 'positive' && <PositiveKeywordsTab selectedClientId={selectedClientId} showToast={showToast} filters={filters} searchParams={searchParams} setSearchParams={setSearchParams} />}
            {activeTab === 'negative' && <NegativeKeywordsTab selectedClientId={selectedClientId} showToast={showToast} />}
            {activeTab === 'lists' && <NegativeKeywordListsTab selectedClientId={selectedClientId} showToast={showToast} />}
            {activeTab === 'expansion' && <KeywordExpansionTab selectedClientId={selectedClientId} />}
        </div>
    )
}
