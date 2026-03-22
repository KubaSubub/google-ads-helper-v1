/**
 * Shared mock data (fixtures) for Playwright E2E tests.
 * Wartości monetarne w micros (÷1,000,000), conversions jako float.
 * Polskie znaki w nazwach kampanii/keywords.
 */

// ─── Campaigns ──────────────────────────────────────────────────────
export const MOCK_CAMPAIGNS = {
    items: [
        {
            id: 101,
            name: 'Sushi Naka Naka — Brandówka',
            campaign_type: 'SEARCH',
            status: 'ENABLED',
            budget_micros: 50_000_000,
            cost_micros: 32_450_000,
            clicks: 245,
            impressions: 4820,
            conversions: 12.5,
            conversion_value_micros: 625_000_000,
            ctr: 5.08,
            avg_cpc_micros: 132_449,
            campaign_role_auto: 'BRAND',
            campaign_role_override: null,
            role_source: 'AUTO',
            role_confidence: 0.92,
            protection_level: 'HIGH',
            health_score: 82,
        },
        {
            id: 102,
            name: 'PMax — Główna kampania zasięgowa',
            campaign_type: 'PERFORMANCE_MAX',
            status: 'ENABLED',
            budget_micros: 100_000_000,
            cost_micros: 78_200_000,
            clicks: 520,
            impressions: 12400,
            conversions: 28.3,
            conversion_value_micros: 1_415_000_000,
            ctr: 4.19,
            avg_cpc_micros: 150_384,
            campaign_role_auto: 'PMAX',
            campaign_role_override: null,
            role_source: 'AUTO',
            role_confidence: 1.0,
            protection_level: 'MEDIUM',
            health_score: 75,
        },
        {
            id: 103,
            name: 'Display — Remarketing żółć',
            campaign_type: 'DISPLAY',
            status: 'PAUSED',
            budget_micros: 30_000_000,
            cost_micros: 0,
            clicks: 0,
            impressions: 0,
            conversions: 0.0,
            conversion_value_micros: 0,
            ctr: 0,
            avg_cpc_micros: 0,
            campaign_role_auto: 'REMARKETING',
            campaign_role_override: null,
            role_source: 'AUTO',
            role_confidence: 0.85,
            protection_level: 'LOW',
            health_score: 45,
        },
    ],
    total: 3,
};

// ─── Keywords ───────────────────────────────────────────────────────
export const MOCK_KEYWORDS = {
    items: [
        {
            id: 201,
            keyword_text: 'sushi naka naka',
            match_type: 'EXACT',
            status: 'ENABLED',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Brand exact',
            quality_score: 9,
            clicks: 120,
            impressions: 1400,
            cost_micros: 15_600_000,
            conversions: 8.2,
            avg_cpc_micros: 130_000,
            impression_share: 0.92,
            bid_micros: 200_000,
            serving_status: 'ELIGIBLE',
        },
        {
            id: 202,
            keyword_text: 'restauracja japońska warszawa',
            match_type: 'PHRASE',
            status: 'ENABLED',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Geo phrases',
            quality_score: 6,
            clicks: 45,
            impressions: 980,
            cost_micros: 8_100_000,
            conversions: 2.1,
            avg_cpc_micros: 180_000,
            impression_share: 0.65,
            bid_micros: 250_000,
            serving_status: 'ELIGIBLE',
        },
        {
            id: 203,
            keyword_text: 'sushi dostawa łódź',
            match_type: 'BROAD',
            status: 'ENABLED',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Broad reach',
            quality_score: 4,
            clicks: 88,
            impressions: 3200,
            cost_micros: 22_000_000,
            conversions: 1.0,
            avg_cpc_micros: 250_000,
            impression_share: 0.41,
            bid_micros: 300_000,
            serving_status: 'LOW_SEARCH_VOLUME',
        },
        {
            id: 204,
            keyword_text: 'najlepsze sushi w mieście',
            match_type: 'PHRASE',
            status: 'PAUSED',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Generic phrases',
            quality_score: 3,
            clicks: 12,
            impressions: 450,
            cost_micros: 4_800_000,
            conversions: 0.0,
            avg_cpc_micros: 400_000,
            impression_share: 0.22,
            bid_micros: 350_000,
            serving_status: 'BELOW_FIRST_PAGE_BID',
        },
        {
            id: 205,
            keyword_text: 'catering japoński ćwiczenia',
            match_type: 'EXACT',
            status: 'REMOVED',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Removed group',
            quality_score: null,
            clicks: 0,
            impressions: 0,
            cost_micros: 0,
            conversions: 0.0,
            avg_cpc_micros: 0,
            impression_share: 0,
            bid_micros: 0,
            serving_status: null,
        },
    ],
    total: 5,
    page: 1,
    total_pages: 1,
};

// ─── Negative Keywords ──────────────────────────────────────────────
export const MOCK_NEGATIVE_KEYWORDS = {
    items: [
        { id: 301, keyword_text: 'darmowe', match_type: 'BROAD', scope: 'CAMPAIGN', campaign_id: 101, campaign_name: 'Sushi Naka Naka — Brandówka' },
        { id: 302, keyword_text: 'przepis na sushi', match_type: 'PHRASE', scope: 'CAMPAIGN', campaign_id: 101, campaign_name: 'Sushi Naka Naka — Brandówka' },
    ],
    total: 2,
    page: 1,
    total_pages: 1,
};

// ─── Negative Keyword Lists ────────────────────────────────────────
export const MOCK_NEGATIVE_KEYWORD_LISTS = [
    { id: 401, name: 'Lista globalna', keyword_count: 15 },
    { id: 402, name: 'Konkurencja', keyword_count: 8 },
];

// ─── Search Terms ───────────────────────────────────────────────────
export const MOCK_SEARCH_TERMS = {
    items: [
        {
            id: 501,
            search_term: 'sushi naka naka warszawa',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Brand exact',
            clicks: 35,
            impressions: 420,
            cost_micros: 4_550_000,
            conversions: 5.0,
            ctr: 8.33,
            segment: 'HIGH_PERFORMER',
        },
        {
            id: 502,
            search_term: 'jak zrobić sushi w domu',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Broad reach',
            clicks: 22,
            impressions: 680,
            cost_micros: 6_600_000,
            conversions: 0.0,
            ctr: 3.24,
            segment: 'WASTE',
        },
        {
            id: 503,
            search_term: 'restauracja azjatycka',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Geo phrases',
            clicks: 8,
            impressions: 290,
            cost_micros: 1_920_000,
            conversions: 0.5,
            ctr: 2.76,
            segment: 'OTHER',
        },
        {
            id: 504,
            search_term: 'pizza hut menu',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Broad reach',
            clicks: 15,
            impressions: 520,
            cost_micros: 4_500_000,
            conversions: 0.0,
            ctr: 2.88,
            segment: 'IRRELEVANT',
        },
        {
            id: 505,
            search_term: 'sushi łódź śródmieście',
            campaign_id: 101,
            campaign_name: 'Sushi Naka Naka — Brandówka',
            ad_group_name: 'Geo phrases',
            clicks: 18,
            impressions: 310,
            cost_micros: 3_240_000,
            conversions: 2.3,
            ctr: 5.81,
            segment: 'HIGH_PERFORMER',
        },
    ],
    total: 5,
    page: 1,
    total_pages: 1,
};

export const MOCK_SEGMENTED_SEARCH_TERMS = {
    HIGH_PERFORMER: [MOCK_SEARCH_TERMS.items[0], MOCK_SEARCH_TERMS.items[4]],
    WASTE: [MOCK_SEARCH_TERMS.items[1]],
    IRRELEVANT: [MOCK_SEARCH_TERMS.items[3]],
    OTHER: [MOCK_SEARCH_TERMS.items[2]],
};

// ─── Recommendations ────────────────────────────────────────────────
export const MOCK_RECOMMENDATIONS = {
    items: [
        {
            id: 601,
            type: 'PAUSE_KEYWORD',
            priority: 'HIGH',
            entity_name: 'sushi dostawa łódź',
            entity_type: 'keyword',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            reason: 'Keyword has high cost and low conversions over the last 30 days.',
            recommended_action: 'Pause keyword to reduce wasted spend.',
            source: 'PLAYBOOK_RULES',
            status: 'pending',
            executable: true,
            context_outcome: 'ACTION',
            confidence_score: 0.88,
            risk_score: 0.15,
            impact_micros: 22_000_000,
            metadata: { spend: 22.0, clicks: 88, conversions: 1.0, ctr: 2.75 },
            suggested_action: 'PAUSE_KEYWORD',
            action_payload: { action_type: 'PAUSE_KEYWORD' },
            expires_at: '2026-04-01T00:00:00',
        },
        {
            id: 602,
            type: 'ADD_NEGATIVE',
            priority: 'HIGH',
            entity_name: 'jak zrobić sushi w domu',
            entity_type: 'search_term',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            reason: 'Search term generates clicks but zero conversions.',
            recommended_action: 'Add as negative keyword (EXACT).',
            source: 'PLAYBOOK_RULES',
            status: 'pending',
            executable: true,
            context_outcome: 'ACTION',
            confidence_score: 0.95,
            risk_score: 0.05,
            impact_micros: 6_600_000,
            metadata: { spend: 6.6, clicks: 22, conversions: 0.0, ctr: 3.24 },
            suggested_action: 'ADD_NEGATIVE',
            action_payload: { action_type: 'ADD_NEGATIVE' },
        },
        {
            id: 603,
            type: 'INCREASE_BUDGET',
            priority: 'MEDIUM',
            entity_name: 'PMax — Główna kampania zasięgowa',
            entity_type: 'campaign',
            campaign_name: 'PMax — Główna kampania zasięgowa',
            reason: 'Campaign is budget-capped but has strong ROAS.',
            recommended_action: 'Increase daily budget by 20%.',
            source: 'ANALYTICS',
            status: 'pending',
            executable: false,
            context_outcome: 'INSIGHT_ONLY',
            confidence_score: 0.72,
            risk_score: 0.35,
            metadata: { spend: 78.2, clicks: 520, conversions: 28.3 },
            suggested_action: 'INCREASE_BUDGET',
            action_payload: { action_type: 'INCREASE_BUDGET' },
            why_blocked: [{ code: 'ROAS_ONLY_SIGNAL' }],
        },
        {
            id: 604,
            type: 'REALLOCATE_BUDGET',
            priority: 'LOW',
            entity_name: 'Display — Remarketing żółć',
            entity_type: 'campaign',
            campaign_name: 'Display — Remarketing żółć',
            reason: 'Campaign is paused but has unused budget that could be reallocated.',
            recommended_action: 'Move budget to PMax campaign.',
            source: 'HYBRID',
            status: 'pending',
            executable: false,
            context_outcome: 'BLOCKED_BY_CONTEXT',
            confidence_score: 0.55,
            risk_score: 0.60,
            metadata: {},
            suggested_action: 'REALLOCATE_BUDGET',
            action_payload: { action_type: 'REALLOCATE_BUDGET' },
            why_blocked: [{ code: 'ROLE_MISMATCH' }, { code: 'DONOR_PROTECTED_MEDIUM' }],
        },
        {
            id: 605,
            type: 'QS_ALERT',
            priority: 'MEDIUM',
            entity_name: 'najlepsze sushi w mieście',
            entity_type: 'keyword',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            reason: 'Quality Score is 3/10 — ad relevance and landing page experience are below average.',
            recommended_action: 'Review ad copy and landing page for this keyword.',
            source: 'ANALYTICS',
            status: 'pending',
            executable: false,
            context_outcome: 'INSIGHT_ONLY',
            confidence_score: 0.80,
            risk_score: 0.20,
            metadata: { quality_score: 3 },
            suggested_action: 'QS_ALERT',
            action_payload: { action_type: 'QS_ALERT' },
        },
    ],
    total: 5,
};

export const MOCK_RECOMMENDATIONS_SUMMARY = {
    total: 5,
    executable_total: 2,
    high_priority: 2,
    by_context_outcome: { ACTION: 2, INSIGHT_ONLY: 2, BLOCKED_BY_CONTEXT: 1 },
    by_priority: { HIGH: 2, MEDIUM: 2, LOW: 1 },
    by_source: { PLAYBOOK_RULES: 2, ANALYTICS: 2, HYBRID: 1 },
};

// ─── Dashboard KPIs ─────────────────────────────────────────────────
export const MOCK_DASHBOARD_KPIS = {
    cost: 110.65,
    clicks: 765,
    impressions: 17220,
    conversions: 40.8,
    ctr: 4.44,
    cost_change: -8.2,
    clicks_change: 12.5,
    impressions_change: 5.1,
    conversions_change: 15.3,
    ctr_change: 6.9,
};

// ─── Health Score ───────────────────────────────────────────────────
export const MOCK_HEALTH_SCORE = {
    score: 74,
    issues: [
        { severity: 'high', message: 'Kampania Display wstrzymana ponad 30 dni' },
        { severity: 'medium', message: '2 słowa kluczowe z Quality Score < 4' },
        { severity: 'low', message: 'Brak rozszerzeń sitelink w 1 kampanii' },
    ],
};

// ─── Budget Pacing ──────────────────────────────────────────────────
export const MOCK_BUDGET_PACING = [
    {
        campaign_id: 101,
        campaign_name: 'Sushi Naka Naka — Brandówka',
        status: 'ENABLED',
        daily_budget: 50.0,
        spend_today: 32.45,
        pacing_pct: 64.9,
    },
    {
        campaign_id: 102,
        campaign_name: 'PMax — Główna kampania zasięgowa',
        status: 'ENABLED',
        daily_budget: 100.0,
        spend_today: 78.2,
        pacing_pct: 78.2,
    },
];

// ─── Device Breakdown ───────────────────────────────────────────────
export const MOCK_DEVICE_BREAKDOWN = [
    { device: 'DESKTOP', clicks: 380, impressions: 8500, cost_micros: 55_000_000, conversions: 22.0 },
    { device: 'MOBILE', clicks: 320, impressions: 7200, cost_micros: 45_000_000, conversions: 15.5 },
    { device: 'TABLET', clicks: 65, impressions: 1520, cost_micros: 10_650_000, conversions: 3.3 },
];

// ─── Alerts (business) ──────────────────────────────────────────────
export const MOCK_ALERTS = {
    alerts: [
        {
            id: 701,
            severity: 'HIGH',
            alert_type: 'COST_SPIKE',
            title: 'Skok kosztów w kampanii Brand',
            description: 'Koszt wzrósł o 45% w porównaniu do średniej z 7 dni.',
            status: 'unresolved',
            metric: 'cost',
            campaign_id: 101,
        },
        {
            id: 702,
            severity: 'MEDIUM',
            alert_type: 'CTR_DROP',
            title: 'Spadek CTR w PMax',
            description: 'CTR spadł z 4.5% do 3.1% w ciągu ostatnich 3 dni.',
            status: 'unresolved',
            metric: 'ctr',
            campaign_id: 102,
        },
        {
            id: 703,
            severity: 'LOW',
            alert_type: 'CONVERSION_DROP',
            title: 'Spadek konwersji — niska istotność',
            description: 'Liczba konwersji spadła o 10%, ale jest w normie statystycznej.',
            status: 'unresolved',
            metric: 'conversions',
            campaign_id: 101,
        },
    ],
};

// ─── Z-Score Anomalies ──────────────────────────────────────────────
export const MOCK_ZSCORE_ANOMALIES = {
    anomalies: [
        { date: '2026-03-20', campaign_id: 101, value: 85.20, z_score: 2.45, direction: 'spike' },
        { date: '2026-03-18', campaign_id: 102, value: 12.10, z_score: -2.10, direction: 'drop' },
    ],
    mean: 42.5,
    std: 15.3,
};

// ─── Daily Audit ────────────────────────────────────────────────────
export const MOCK_DAILY_AUDIT = {
    health_summary: {
        health_score: 74,
        total_active_campaigns: 3,
        total_enabled_keywords: 5,
    },
    kpi_snapshot: {
        today_spend: 110.65,
        yesterday_spend: 120.40,
        today_clicks: 765,
        yesterday_clicks: 680,
        today_conversions: 40.8,
        yesterday_conversions: 35.2,
    },
    anomalies_24h: [
        { severity: 'high', alert_type: 'COST_SPIKE', campaign_name: 'Sushi Naka Naka — Brandówka', message: 'Skok kosztów +45% w kampanii Brand' },
    ],
    disapproved_ads: [
        { ad_id: 901, headline_1: 'Najlepsze sushi w mieście!', campaign_name: 'Sushi Naka Naka — Brandówka', approval_status: 'DISAPPROVED', reason: 'Misleading content' },
    ],
    budget_capped_performers: [
        { campaign_id: 102, campaign_name: 'PMax — Główna kampania zasięgowa', pacing_pct: 95.2, cpa: 2.76 },
    ],
    search_terms_needing_action: [
        { term: 'jak zrobić sushi w domu', clicks: 22, cost_micros: 6_600_000, conversions: 0.0 },
        { term: 'pizza hut menu', clicks: 15, cost_micros: 4_500_000, conversions: 0.0 },
    ],
    pending_recommendations: {
        count: 5,
        top: [
            { type: 'PAUSE_KEYWORD', priority: 'HIGH', entity_name: 'sushi dostawa łódź' },
        ],
    },
    budget_pacing: MOCK_BUDGET_PACING,
    quick_scripts: {
        clean_waste: 3,
        pause_burning: 1,
        boost_winners: 2,
        emergency_brake: 0,
        add_negatives: 4,
    },
};

// ─── Action History ─────────────────────────────────────────────────
export const MOCK_ACTION_HISTORY = {
    items: [
        {
            id: 801,
            operation: 'PAUSE_KEYWORD',
            resource_type: 'keyword',
            entity_name: 'sushi dostawa łódź',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            status: 'SUCCESS',
            executed_at: '2026-03-22T10:30:00',
            client_type: 'GOOGLE_ADS_HELPER',
            revertable: true,
            old_value: 'ENABLED',
            new_value: 'PAUSED',
            delta_pct: null,
        },
        {
            id: 802,
            operation: 'UPDATE_BID',
            resource_type: 'keyword',
            entity_name: 'restauracja japońska warszawa',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            status: 'REVERTED',
            executed_at: '2026-03-21T15:00:00',
            client_type: 'GOOGLE_ADS_HELPER',
            revertable: false,
            old_value: '0.25',
            new_value: '0.18',
            delta_pct: -28.0,
        },
        {
            id: 803,
            operation: 'ADD_NEGATIVE',
            resource_type: 'search_term',
            entity_name: 'pizza hut menu',
            campaign_name: 'Sushi Naka Naka — Brandówka',
            status: 'FAILED',
            executed_at: '2026-03-20T09:15:00',
            client_type: 'GOOGLE_ADS_HELPER',
            revertable: false,
            old_value: null,
            new_value: 'NEGATIVE_EXACT',
            delta_pct: null,
            error_message: 'Google Ads API rate limit exceeded',
        },
    ],
    total: 3,
};

// ─── Forecast ───────────────────────────────────────────────────────
export const MOCK_FORECAST = {
    campaign_id: 101,
    campaign_name: 'Sushi Naka Naka — Brandówka',
    metric: 'clicks',
    historical: [
        { date: '2026-03-15', value: 35 },
        { date: '2026-03-16', value: 42 },
        { date: '2026-03-17', value: 38 },
        { date: '2026-03-18', value: 45 },
        { date: '2026-03-19', value: 40 },
        { date: '2026-03-20', value: 48 },
        { date: '2026-03-21', value: 43 },
    ],
    prediction: [
        { date: '2026-03-22', value: 46, lower: 38, upper: 54 },
        { date: '2026-03-23', value: 47, lower: 37, upper: 57 },
        { date: '2026-03-24', value: 44, lower: 33, upper: 55 },
    ],
    kpis: {
        avg_daily: 41.6,
        trend_pct: 5.2,
        forecast_total: 137,
    },
};

// ─── Campaign Trends ────────────────────────────────────────────────
export const MOCK_CAMPAIGN_TRENDS = [
    { date: '2026-03-19', cost: 32.1, clicks: 110, impressions: 2400, conversions: 5.8 },
    { date: '2026-03-20', cost: 35.4, clicks: 125, impressions: 2650, conversions: 7.2 },
    { date: '2026-03-21', cost: 28.9, clicks: 98, impressions: 2100, conversions: 4.5 },
];

// ─── Geo Breakdown ──────────────────────────────────────────────────
export const MOCK_GEO_BREAKDOWN = [
    { region: 'Warszawa', clicks: 280, impressions: 5200, cost_micros: 38_000_000, conversions: 18.0 },
    { region: 'Kraków', clicks: 120, impressions: 2800, cost_micros: 18_000_000, conversions: 8.5 },
];

// ─── Quality Score Audit ────────────────────────────────────────────
export const MOCK_QUALITY_SCORE_AUDIT = {
    average_qs: 5.8,
    low_qs_count: 2,
    high_qs_count: 1,
    distribution: [
        { score: 3, count: 1 },
        { score: 4, count: 1 },
        { score: 6, count: 1 },
        { score: 9, count: 1 },
    ],
    keywords: MOCK_KEYWORDS.items.filter(k => k.quality_score != null),
};

// ─── Semantic Clusters ──────────────────────────────────────────────
export const MOCK_SEMANTIC_CLUSTERS = {
    clusters: [
        { cluster_id: 1, label: 'Sushi brand', keywords: ['sushi naka naka', 'naka naka'], size: 2, avg_ctr: 5.08 },
        { cluster_id: 2, label: 'Dostawa jedzenia', keywords: ['sushi dostawa', 'dostawa łódź'], size: 2, avg_ctr: 2.75 },
    ],
};

// ─── Client Details (for Settings) ──────────────────────────────────
export const MOCK_CLIENT_DETAIL = {
    id: 3,
    name: 'Sushi Naka Naka',
    google_customer_id: '123-456-7890',
    is_demo: true,
    status: 'ACTIVE',
    industry: 'Gastronomia',
    monthly_budget: 5000,
    target_cpa: 3.50,
    target_roas: 5.0,
    safety_limits: {
        MAX_BID_CHANGE_PCT: 0.50,
        MAX_BUDGET_CHANGE_PCT: 0.30,
        MIN_BID_USD: 0.10,
        MAX_BID_USD: 100.00,
        MAX_KEYWORD_PAUSE_PCT: 0.20,
        MAX_NEGATIVES_PER_DAY: 100,
    },
};

// ─── Agent Status ───────────────────────────────────────────────────
export const MOCK_AGENT_STATUS = {
    available: true,
    model: 'claude-sonnet-4-20250514',
};

// ─── Reports ────────────────────────────────────────────────────────
export const MOCK_REPORTS = [
    {
        id: 'rpt-001',
        type: 'monthly',
        period_label: '2026-03',
        created_at: '2026-03-01T08:00:00',
        status: 'completed',
        client_id: 3,
    },
    {
        id: 'rpt-002',
        type: 'weekly',
        period_label: 'week-12',
        created_at: '2026-03-18T08:00:00',
        status: 'completed',
        client_id: 3,
    },
];

// ─── Unified Timeline (for ActionHistory) ───────────────────────────
export const MOCK_UNIFIED_TIMELINE = {
    items: MOCK_ACTION_HISTORY.items,
    total: 3,
};

// ─── History Filters ────────────────────────────────────────────────
export const MOCK_HISTORY_FILTERS = {
    resource_types: ['keyword', 'campaign', 'search_term', 'ad'],
    operations: ['PAUSE_KEYWORD', 'UPDATE_BID', 'ADD_NEGATIVE', 'INCREASE_BUDGET'],
    statuses: ['SUCCESS', 'FAILED', 'REVERTED', 'DRY_RUN'],
};

// ─── Search Optimization — generic empty/minimal responses ─────────
export const MOCK_ANALYTICS_EMPTY = {
    items: [],
    data: [],
    total: 0,
};
