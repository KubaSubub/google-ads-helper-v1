const API_BASE = '/api/v1';

async function fetchAPI(endpoint, options = {}) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'API Error');
    }
    return res.json();
}

// Clients
export const getClients = (page = 1) => fetchAPI(`/clients/?page=${page}`);
export const getClient = (id) => fetchAPI(`/clients/${id}`);

// Campaigns
export const getCampaigns = (clientId, params = {}) => {
    const qs = new URLSearchParams({ client_id: clientId, ...params }).toString();
    return fetchAPI(`/campaigns/?${qs}`);
};
export const getCampaignKPIs = (campaignId, days = 30) =>
    fetchAPI(`/campaigns/${campaignId}/kpis?days=${days}`);
export const getCampaignMetrics = (campaignId, dateFrom, dateTo) => {
    const params = new URLSearchParams();
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    return fetchAPI(`/campaigns/${campaignId}/metrics?${params}`);
};

// Search Terms
export const getSearchTerms = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/search-terms/?${qs}`);
};
export const getSearchTermsSummary = (campaignId, days = 30) =>
    fetchAPI(`/search-terms/summary?campaign_id=${campaignId}&days=${days}`);

// Keywords
export const getKeywords = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/keywords/?${qs}`);
};

// Ads
export const getAds = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/ads/?${qs}`);
};

// Analytics
export const getDashboardKPIs = (clientId, days = 30) =>
    fetchAPI(`/analytics/dashboard-kpis?client_id=${clientId}&days=${days}`);
export const getCorrelationMatrix = (data) =>
    fetchAPI('/analytics/correlation', { method: 'POST', body: JSON.stringify(data) });
export const getAnomalies = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchAPI(`/analytics/anomalies?${qs}`);
};

// Sync
export const getSyncStatus = () => fetchAPI('/sync/status');

export const updateClient = (id, data) => fetchAPI(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(data) });

export const getSemanticClusters = (params) => {
    const query = new URLSearchParams(params).toString();
    return fetchAPI(`/semantic/clusters?${query}`);
};

// Recommendations
export const getRecommendations = (clientId, days = 30) =>
    fetchAPI(`/recommendations/?client_id=${clientId}&days=${days}`);
export const getRecommendationsSummary = (clientId, days = 30) =>
    fetchAPI(`/recommendations/summary?client_id=${clientId}&days=${days}`);

// Search Terms Intelligence
export const getSegmentedSearchTerms = (clientId, days = 30) =>
    fetchAPI(`/search-terms/segmented?client_id=${clientId}&days=${days}`);

// Phase 4: Audit & Forecast
export const getQualityScoreAudit = (clientId) =>
    fetchAPI(`/analytics/quality-score-audit?client_id=${clientId}`);

export const getForecast = (campaignId, metric = 'cost', forecastDays = 7) =>
    fetchAPI(`/analytics/forecast?campaign_id=${campaignId}&metric=${metric}&forecast_days=${forecastDays}`);

// Action Execution
export const applyRecommendation = (action, entityId, params = {}) =>
    fetchAPI(`/recommendations/apply`, {
        method: 'POST',
        body: JSON.stringify({ action, entity_id: entityId, params })
    });
