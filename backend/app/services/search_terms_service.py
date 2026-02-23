"""Search Terms Service - segmentation logic (Feature 5).

Segments search terms into 4 categories based on performance:
1. IRRELEVANT - contains irrelevant keywords → add as negative
2. HIGH_PERFORMER - high conversion rate → add as keyword
3. WASTE - clicks but no conversions, low CTR → add as negative
4. OTHER - insufficient data

This logic is called during sync Phase 4.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.search_term import SearchTerm
from app.models.campaign import Campaign
from app.models.ad_group import AdGroup
from app.utils.constants import IRRELEVANT_KEYWORDS
from app.utils.formatters import micros_to_currency


class SearchTermsService:
    """Handles search term segmentation and analysis."""

    def __init__(self, db: Session):
        self.db = db

    def segment_search_terms(self, client_id: int) -> int:
        """Assign segments to all search terms for a client.

        Called during sync Phase 4.

        Segments (ordered — first match wins):
        1. IRRELEVANT — query contains IRRELEVANT_KEYWORDS
        2. HIGH_PERFORMER — conv ≥ 3 AND CVR > campaign avg CVR
        3. WASTE — clicks ≥ 5 AND conv = 0 AND CTR < 1%
        4. OTHER — default

        Args:
            client_id: Client ID

        Returns:
            Count of terms segmented (updated)
        """
        terms = self.db.query(SearchTerm).join(
            AdGroup
        ).join(
            Campaign
        ).filter(
            Campaign.client_id == client_id
        ).all()

        # Pre-compute campaign avg CVR
        campaign_cvrs = self._get_campaign_avg_cvrs(client_id)
        segmented = 0

        for term in terms:
            old_segment = getattr(term, 'segment', None)
            new_segment = self._classify(term, campaign_cvrs)

            # Add segment column if doesn't exist (will be added to model later)
            if not hasattr(term, 'segment'):
                # For now, skip - we need to add 'segment' column to SearchTerm model
                continue

            term.segment = new_segment
            if new_segment != old_segment:
                segmented += 1

        self.db.commit()
        return segmented

    def get_segmented_search_terms(self, client_id: int) -> dict:
        """Return search terms grouped by segment with stats.

        Used by frontend SearchTerms.jsx segment cards.

        Args:
            client_id: Client ID

        Returns:
            Dict with segments as keys, each containing count, totals, and terms list
        """
        segments = {}

        for seg in ["HIGH_PERFORMER", "WASTE", "IRRELEVANT", "OTHER"]:
            # TODO: Add segment column to SearchTerm model first
            # For now, return empty structure
            terms = []

            total_cost = sum(t.cost_micros or 0 for t in terms)
            total_clicks = sum(t.clicks or 0 for t in terms)
            total_conv = sum(t.conversions or 0 for t in terms)

            segments[seg] = {
                "count": len(terms),
                "total_cost_usd": round(total_cost / 1_000_000, 2),
                "total_clicks": total_clicks,
                "total_conversions": total_conv,
                "terms": [
                    {
                        "id": t.id,
                        "query_text": t.text,
                        "clicks": t.clicks or 0,
                        "cost_usd": round((t.cost_micros or 0) / 1_000_000, 2),
                        "conversions": t.conversions or 0,
                        "ctr_pct": round((t.ctr or 0) / 10_000, 2),  # Convert micros to %
                        "segment": seg
                    }
                    for t in terms
                ]
            }

        return segments

    def _classify(self, term: SearchTerm, campaign_cvrs: dict) -> str:
        """Classify single search term into segment.

        Args:
            term: SearchTerm instance
            campaign_cvrs: Dict of campaign_id → avg CVR

        Returns:
            Segment name (IRRELEVANT, HIGH_PERFORMER, WASTE, OTHER)
        """
        query_lower = (term.text or "").lower()

        # 1. IRRELEVANT - contains irrelevant keywords
        if any(kw in query_lower for kw in IRRELEVANT_KEYWORDS):
            return "IRRELEVANT"

        # 2. HIGH_PERFORMER - conv >= 3 AND CVR > campaign avg
        if (term.conversions or 0) >= 3:
            # Get campaign_id from ad_group
            campaign_id = term.ad_group.campaign_id if term.ad_group else None
            campaign_cvr = campaign_cvrs.get(campaign_id, 0)

            term_cvr = (term.conversions / term.clicks) if term.clicks else 0
            if term_cvr > campaign_cvr:
                return "HIGH_PERFORMER"

        # 3. WASTE - clicks >= 5, conv = 0, CTR < 1%
        if (term.clicks or 0) >= 5 and (term.conversions or 0) == 0:
            # CTR stored as micros, convert to decimal
            ctr_decimal = (term.ctr or 0) / 1_000_000  # micros to decimal
            if ctr_decimal < 0.01:  # < 1%
                return "WASTE"

        # 4. OTHER - default
        return "OTHER"

    def _get_campaign_avg_cvrs(self, client_id: int) -> dict:
        """Pre-compute avg CVR per campaign for segmentation.

        Args:
            client_id: Client ID

        Returns:
            Dict of campaign_id → avg CVR (as decimal, e.g., 0.05 = 5%)
        """
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id
        ).all()

        cvrs = {}
        for c in campaigns:
            if c.clicks and c.clicks > 0:
                # TODO: Add conversions and clicks columns to Campaign model
                # For now, return 0
                cvrs[c.id] = 0.0
            else:
                cvrs[c.id] = 0.0

        return cvrs
