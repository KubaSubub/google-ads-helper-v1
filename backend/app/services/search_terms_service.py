"""Search Terms Service - segmentation logic (Feature 5).

Segments search terms into 4 categories based on performance:
1. IRRELEVANT - contains irrelevant keywords -> add as negative
2. HIGH_PERFORMER - high conversion rate -> add as keyword
3. WASTE - clicks but no conversions, low CTR -> add as negative
4. OTHER - insufficient data

This logic is called during sync Phase 4.
"""

import re
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.search_term import SearchTerm
from app.models.metric_daily import MetricDaily
from app.models.campaign import Campaign
from app.models.ad_group import AdGroup
from app.utils.constants import IRRELEVANT_KEYWORDS


class SearchTermsService:
    """Handles search term segmentation and analysis."""

    def __init__(self, db: Session):
        self.db = db

    def segment_search_terms(self, client_id: int) -> int:
        """Assign segments to all search terms for a client.

        Called during sync Phase 4.

        Segments (ordered -- first match wins):
        1. IRRELEVANT -- query contains IRRELEVANT_KEYWORDS (word boundary)
        2. HIGH_PERFORMER -- conv >= 3 AND CVR > campaign avg CVR
        3. WASTE -- clicks >= 5 AND conv = 0 AND CTR < 1%
        4. OTHER -- default
        """
        terms = (
            self.db.query(SearchTerm)
            .join(AdGroup)
            .join(Campaign)
            .options(joinedload(SearchTerm.ad_group))
            .filter(Campaign.client_id == client_id)
            .all()
        )

        # Pre-compute campaign avg CVR from MetricDaily (last 30 days)
        campaign_cvrs = self._get_campaign_avg_cvrs(client_id)

        # Build word-boundary regex patterns for irrelevant keywords
        irrelevant_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in IRRELEVANT_KEYWORDS
        ]

        segmented = 0
        for term in terms:
            old_segment = term.segment
            new_segment = self._classify(term, campaign_cvrs, irrelevant_patterns)
            term.segment = new_segment
            if new_segment != old_segment:
                segmented += 1

        self.db.commit()
        return segmented

    def get_segmented_search_terms(self, client_id: int) -> dict:
        """Return search terms grouped by segment with stats."""
        # Make sure segments are assigned
        terms = (
            self.db.query(SearchTerm)
            .join(AdGroup)
            .join(Campaign)
            .filter(Campaign.client_id == client_id)
            .all()
        )

        # If no segments assigned yet, run segmentation first
        if terms and all(t.segment is None for t in terms):
            self.segment_search_terms(client_id)
            # Re-fetch after commit
            terms = (
                self.db.query(SearchTerm)
                .join(AdGroup)
                .join(Campaign)
                .filter(Campaign.client_id == client_id)
                .all()
            )

        segments = {}
        for seg in ["HIGH_PERFORMER", "WASTE", "IRRELEVANT", "OTHER"]:
            seg_terms = [t for t in terms if t.segment == seg]

            total_cost = sum(t.cost_micros or 0 for t in seg_terms)
            total_clicks = sum(t.clicks or 0 for t in seg_terms)
            total_conv = sum(t.conversions or 0 for t in seg_terms)
            total_conv_value = sum(t.conversion_value_micros or 0 for t in seg_terms)

            segments[seg] = {
                "count": len(seg_terms),
                "total_cost_usd": round(total_cost / 1_000_000, 2),
                "total_clicks": total_clicks,
                "total_conversions": round(total_conv, 2),
                "total_conversion_value_usd": round(total_conv_value / 1_000_000, 2),
                "terms": [
                    {
                        "id": t.id,
                        "query_text": t.text,
                        "keyword_text": t.keyword_text,
                        "clicks": t.clicks or 0,
                        "impressions": t.impressions or 0,
                        "cost_usd": round((t.cost_micros or 0) / 1_000_000, 2),
                        "conversions": round(t.conversions or 0, 2),
                        "conversion_value_usd": round((t.conversion_value_micros or 0) / 1_000_000, 2),
                        "ctr_pct": round((t.ctr or 0) / 10_000, 2),
                        "roas": round(
                            (t.conversion_value_micros or 0) / (t.cost_micros or 1), 2
                        ) if (t.cost_micros or 0) > 0 else 0.0,
                        "segment": seg,
                    }
                    for t in seg_terms
                ],
            }

        return segments

    def _classify(self, term: SearchTerm, campaign_cvrs: dict, irrelevant_patterns: list) -> str:
        """Classify single search term into segment."""
        query_text = (term.text or "").lower()
        clicks = term.clicks or 0
        conversions = term.conversions or 0.0

        # 1. IRRELEVANT - word boundary match against irrelevant keywords
        for pattern in irrelevant_patterns:
            if pattern.search(query_text):
                return "IRRELEVANT"

        # 2. HIGH_PERFORMER - conv >= 3 AND CVR > campaign avg
        if conversions >= 3:
            campaign_id = term.ad_group.campaign_id if term.ad_group else None
            campaign_cvr = campaign_cvrs.get(campaign_id, 0)
            term_cvr = (conversions / clicks) if clicks > 0 else 0
            if term_cvr > campaign_cvr:
                return "HIGH_PERFORMER"

        # 3. WASTE - clicks >= 5, conv = 0, CTR < 1%
        if clicks >= 5 and conversions == 0:
            ctr_pct = (term.ctr or 0) / 10_000  # micros to percent
            if ctr_pct < 1.0:
                return "WASTE"

        # 4. OTHER - default
        return "OTHER"

    def _get_campaign_avg_cvrs(self, client_id: int) -> dict:
        """Compute avg CVR per campaign from MetricDaily (last 30 days).

        Returns dict of campaign_id -> avg CVR as decimal (0.05 = 5%).
        """
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=30)

        results = (
            self.db.query(
                MetricDaily.campaign_id,
                func.sum(MetricDaily.conversions).label("total_conv"),
                func.sum(MetricDaily.clicks).label("total_clicks"),
            )
            .join(Campaign)
            .filter(
                Campaign.client_id == client_id,
                MetricDaily.date >= cutoff,
            )
            .group_by(MetricDaily.campaign_id)
            .all()
        )

        cvrs = {}
        for campaign_id, total_conv, total_clicks in results:
            if total_clicks and total_clicks > 0:
                cvrs[campaign_id] = total_conv / total_clicks
            else:
                cvrs[campaign_id] = 0.0

        return cvrs
