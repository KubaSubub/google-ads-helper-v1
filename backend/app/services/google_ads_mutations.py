"""Google Ads API mutation methods — extracted from GoogleAdsService for maintainability.

This mixin contains all write/mutation operations:
- apply_action(): canonical action dispatcher
- _mutate_*(): individual API mutation methods
- batch_add_*(): batch operations
- upload_offline_conversions()
- add_placement_exclusion()

Used via: class GoogleAdsService(GoogleAdsMutationsMixin): ...
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    ActionLog, Campaign, Client, Keyword, NegativeKeyword,
)

if TYPE_CHECKING:
    from app.models.ad_group import AdGroup


class GoogleAdsMutationsMixin:
    """Write/mutation operations for GoogleAdsService.

    Expects self.client (google-ads SDK client) and self.is_connected property
    to be provided by the host class.
    """

    # -----------------------------------------------------------------------
    # Apply Action (canonical action dispatcher)
    # -----------------------------------------------------------------------

    def apply_action(
        self,
        db: Session,
        action_type: str,
        entity_id: int | None,
        params: dict | None = None,
        target: dict | None = None,
        client_id: int | None = None,
    ):
        """Execute a canonical action on a Google Ads entity.

        Mutations are applied to the local DB first and flushed. The caller owns the
        surrounding transaction. When Google Ads credentials are configured, the same
        mutation is sent to the API; otherwise the method returns `mode=LOCAL_ONLY`.
        """
        from app.models import Ad, Campaign, Keyword
        from app.services.action_executor import SafetyViolationError, validate_action
        from app.utils.formatters import micros_to_currency

        params = params or {}
        target = target or {}
        mode = "LIVE" if self.is_connected else "LOCAL_ONLY"

        logger.info(f"EXECUTING: {action_type} entity={entity_id} params={params} target={target}")

        client_limits = None
        if client_id is not None:
            client_record = db.get(Client, client_id)
            if client_record and client_record.business_rules:
                client_limits = (client_record.business_rules or {}).get("safety_limits")

        if action_type == "PAUSE_KEYWORD":
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            kw.status = "PAUSED"
            if self.is_connected:
                self._mutate_keyword_status(kw.google_keyword_id, "PAUSED", db, kw)
            db.flush()
            return {
                "status": "success",
                "message": "Executed PAUSE_KEYWORD",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "ENABLE_KEYWORD":
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            kw.status = "ENABLED"
            if self.is_connected:
                self._mutate_keyword_status(kw.google_keyword_id, "ENABLED", db, kw)
            db.flush()
            return {
                "status": "success",
                "message": "Executed ENABLE_KEYWORD",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "PAUSE_AD":
            ad = db.get(Ad, entity_id)
            if not ad:
                return {"status": "error", "message": f"Ad {entity_id} not found"}
            ad.status = "PAUSED"
            if self.is_connected:
                self._mutate_ad_status(ad, db, "PAUSED")
            db.flush()
            return {
                "status": "success",
                "message": "Executed PAUSE_AD",
                "entity_type": "ad",
                "entity_id": ad.id,
                "mode": mode,
            }

        if action_type in {"UPDATE_BID", "SET_KEYWORD_BID", "SET_BID"}:
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            amount_micros = params.get("amount_micros")
            if amount_micros is None and params.get("amount") is not None:
                amount_micros = int(round(float(params["amount"]) * 1_000_000))
            if amount_micros is None:
                return {"status": "error", "message": "Missing amount for bid update"}

            current_bid = micros_to_currency(kw.bid_micros or 0)
            new_bid = amount_micros / 1_000_000
            try:
                validate_action(action_type, current_bid, new_bid, {}, client_limits)
            except SafetyViolationError as exc:
                return {"status": "error", "message": f"Safety violation: {exc}"}

            kw.bid_micros = int(amount_micros)
            if self.is_connected:
                self._mutate_keyword_bid(kw, db)
            db.flush()
            return {
                "status": "success",
                "message": "Executed UPDATE_BID",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "ADD_KEYWORD":
            from app.models.ad_group import AdGroup as AG

            ad_group_id = target.get("ad_group_id") or params.get("ad_group_id")
            text = (params.get("text") or "").strip()
            match_type = params.get("match_type", "EXACT")
            if not ad_group_id or not text:
                return {"status": "error", "message": "Missing ad_group_id or text"}

            existing = (
                db.query(Keyword)
                .filter(
                    Keyword.ad_group_id == ad_group_id,
                    func.lower(Keyword.text) == text.lower(),
                    Keyword.status != "REMOVED",
                )
                .first()
            )
            if existing:
                return {"status": "error", "message": "Keyword already exists in target ad group"}

            new_kw = Keyword(
                ad_group_id=ad_group_id,
                text=text,
                match_type=match_type,
                status="ENABLED",
                google_keyword_id=f"local-{int(datetime.now(timezone.utc).timestamp())}",
                clicks=0,
                impressions=0,
                cost_micros=0,
                conversions=0.0,
                bid_micros=0,
            )
            db.add(new_kw)
            db.flush()
            if self.is_connected:
                self._mutate_add_keyword(new_kw, db)
            return {
                "status": "success",
                "message": "Executed ADD_KEYWORD",
                "entity_type": "keyword",
                "entity_id": new_kw.id,
                "mode": mode,
            }

        if action_type == "ADD_NEGATIVE":
            from app.models.ad_group import AdGroup as AG

            campaign_id = target.get("campaign_id") or params.get("campaign_id") or entity_id
            ad_group_id = params.get("ad_group_id")
            text = (params.get("text") or "").strip()
            match_type = params.get("match_type", "PHRASE")
            negative_level = params.get("negative_level", "CAMPAIGN")
            if negative_level not in ("CAMPAIGN", "AD_GROUP"):
                return {"status": "error", "message": "negative_level must be CAMPAIGN or AD_GROUP"}

            if negative_level == "AD_GROUP":
                if not ad_group_id:
                    return {"status": "error", "message": "Missing ad_group_id for AD_GROUP level"}
                ad_group = db.get(AG, ad_group_id)
                if not ad_group:
                    return {"status": "error", "message": f"Ad group {ad_group_id} not found"}
                campaign_id = ad_group.campaign_id
                if not text:
                    return {"status": "error", "message": "Missing text"}
                existing = (
                    db.query(NegativeKeyword)
                    .filter(
                        NegativeKeyword.ad_group_id == ad_group_id,
                        NegativeKeyword.negative_scope == "AD_GROUP",
                        func.lower(NegativeKeyword.text) == text.lower(),
                        NegativeKeyword.status != "REMOVED",
                    )
                    .first()
                )
                if existing:
                    return {"status": "error", "message": "Negative keyword already exists"}
                campaign = db.get(Campaign, campaign_id)
                if not campaign:
                    return {"status": "error", "message": f"Campaign {campaign_id} not found"}
                negative = NegativeKeyword(
                    client_id=campaign.client_id,
                    campaign_id=campaign.id,
                    ad_group_id=ad_group_id,
                    criterion_kind="NEGATIVE",
                    text=text,
                    match_type=match_type,
                    negative_scope="AD_GROUP",
                    status="ENABLED",
                    source="LOCAL_ACTION",
                )
                db.add(negative)
                db.flush()
                if self.is_connected:
                    self._mutate_ad_group_negative(ad_group, db, negative)
                return {
                    "status": "success",
                    "message": "Executed ADD_NEGATIVE",
                    "entity_type": "ad_group",
                    "entity_id": ad_group.id,
                    "mode": mode,
                }

            # CAMPAIGN level (default)
            if not campaign_id or not text:
                return {"status": "error", "message": "Missing campaign_id or text"}

            existing = (
                db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.campaign_id == campaign_id,
                    NegativeKeyword.negative_scope == "CAMPAIGN",
                    func.lower(NegativeKeyword.text) == text.lower(),
                    NegativeKeyword.status != "REMOVED",
                )
                .first()
            )
            if existing:
                return {"status": "error", "message": "Negative keyword already exists"}

            campaign = db.get(Campaign, campaign_id)
            if not campaign:
                return {"status": "error", "message": f"Campaign {campaign_id} not found"}

            negative = NegativeKeyword(
                client_id=campaign.client_id,
                campaign_id=campaign.id,
                ad_group_id=None,
                criterion_kind="NEGATIVE",
                text=text,
                match_type=match_type,
                negative_scope="CAMPAIGN",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(negative)
            db.flush()
            if self.is_connected:
                self._mutate_campaign_negative(campaign, db, negative)
            return {
                "status": "success",
                "message": "Executed ADD_NEGATIVE",
                "entity_type": "campaign",
                "entity_id": campaign.id,
                "mode": mode,
            }

        if action_type in {"INCREASE_BUDGET", "SET_BUDGET"}:
            from app.services.action_executor import SafetyViolationError, validate_action
            from app.utils.formatters import micros_to_currency

            campaign = db.get(Campaign, entity_id)
            if not campaign:
                return {"status": "error", "message": f"Campaign {entity_id} not found"}
            amount_micros = params.get("amount_micros")
            if amount_micros is None and params.get("amount") is not None:
                amount_micros = int(round(float(params["amount"]) * 1_000_000))
            if amount_micros is None:
                return {"status": "error", "message": "Missing amount for budget update"}

            current_budget = micros_to_currency(campaign.budget_micros or 0)
            new_budget = amount_micros / 1_000_000
            try:
                validate_action(action_type, current_budget, new_budget, {}, client_limits)
            except SafetyViolationError as exc:
                return {"status": "error", "message": f"Safety violation: {exc}"}

            campaign.budget_micros = int(amount_micros)
            if self.is_connected:
                self._mutate_campaign_budget(campaign, db)
            db.flush()
            return {
                "status": "success",
                "message": f"Executed {action_type}",
                "entity_type": "campaign",
                "entity_id": campaign.id,
                "mode": mode,
            }

        return {"status": "error", "message": f"Unknown action_type: {action_type}"}

    # -----------------------------------------------------------------------
    # Individual mutation methods (Google Ads API calls)
    # -----------------------------------------------------------------------

    def _mutate_keyword_status(self, google_keyword_id: str, new_status: str, db: Session, kw):
        """Send keyword status mutation to Google Ads API."""
        if not self.client or not google_keyword_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ag = db.get(AdGroup, kw.ad_group_id)
        if not ag:
            raise RuntimeError("Ad group not found for keyword mutation")
        campaign = db.get(Campaign, ag.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for keyword mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = service.ad_group_criterion_path(
            customer_id,
            str(ag.google_ad_group_id),
            google_keyword_id,
        )
        criterion.status = getattr(self.client.enums.AdGroupCriterionStatusEnum, new_status)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])

    def _mutate_keyword_bid(self, kw, db: Session):
        """Send keyword bid mutation to Google Ads API."""
        if not self.client or not kw.google_keyword_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ag = db.get(AdGroup, kw.ad_group_id)
        if not ag:
            raise RuntimeError("Ad group not found for bid mutation")
        campaign = db.get(Campaign, ag.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for bid mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for bid mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = service.ad_group_criterion_path(
            customer_id,
            str(ag.google_ad_group_id),
            kw.google_keyword_id,
        )
        criterion.cpc_bid_micros = kw.bid_micros

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("cpc_bid_micros")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])

    def _mutate_ad_status(self, ad, db: Session, new_status: str):
        """Pause or enable an ad via AdGroupAdService."""
        if not self.client or not ad.google_ad_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ad_group = db.get(AdGroup, ad.ad_group_id)
        if not ad_group:
            raise RuntimeError("Ad group not found for ad mutation")
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for ad mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for ad mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupAdService")
        operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.update
        ad_group_ad.resource_name = service.ad_group_ad_path(
            customer_id,
            str(ad_group.google_ad_group_id),
            str(ad.google_ad_id),
        )
        ad_group_ad.status = getattr(self.client.enums.AdGroupAdStatusEnum, new_status)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_ads(customer_id=customer_id, operations=[operation])

    def _mutate_add_keyword(self, kw, db: Session):
        """Create a keyword in Google Ads for a locally staged ADD_KEYWORD action."""
        if not self.client:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ad_group = db.get(AdGroup, kw.ad_group_id)
        if not ad_group:
            raise RuntimeError("Ad group not found for keyword creation")
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for keyword creation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for keyword creation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = self.client.get_service("AdGroupService").ad_group_path(
            customer_id,
            str(ad_group.google_ad_group_id),
        )
        criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = kw.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, kw.match_type)
        if kw.bid_micros:
            criterion.cpc_bid_micros = kw.bid_micros
        response = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            kw.google_keyword_id = resource_name.split("~")[-1]

    def _mutate_campaign_negative(self, campaign, db: Session, negative):
        """Create a campaign-level negative keyword in Google Ads."""
        if not self.client:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for negative keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("CampaignCriterionService")
        operation = self.client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = self.client.get_service("CampaignService").campaign_path(
            customer_id,
            str(campaign.google_campaign_id),
        )
        criterion.negative = True
        criterion.keyword.text = negative.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, negative.match_type)
        response = service.mutate_campaign_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            negative.google_resource_name = resource_name
            negative.google_criterion_id = resource_name.split("~")[-1]

    def _mutate_ad_group_negative(self, ad_group, db: Session, negative):
        """Create an ad-group-level negative keyword in Google Ads."""
        if not self.client:
            return
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for ad-group negative keyword mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for ad-group negative keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = self.client.get_service("AdGroupService").ad_group_path(
            customer_id,
            str(ad_group.google_ad_group_id),
        )
        criterion.negative = True
        criterion.keyword.text = negative.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, negative.match_type)
        response = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            negative.google_resource_name = resource_name
            negative.google_criterion_id = resource_name.split("~")[-1]

    # ------------------------------------------------------------------
    # Batch mutation helpers (single API call for multiple operations)
    # ------------------------------------------------------------------

    def batch_add_campaign_negatives(
        self,
        db: Session,
        campaign: "Campaign",
        negatives: list["NegativeKeyword"],
    ) -> None:
        """Add multiple campaign-level negative keywords in a single API call."""
        if not self.client or not negatives:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for batch negative keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("CampaignCriterionService")
        campaign_path = self.client.get_service("CampaignService").campaign_path(
            customer_id, str(campaign.google_campaign_id),
        )

        operations = []
        for neg in negatives:
            op = self.client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = campaign_path
            criterion.negative = True
            criterion.keyword.text = neg.text
            criterion.keyword.match_type = getattr(
                self.client.enums.KeywordMatchTypeEnum, neg.match_type,
            )
            operations.append(op)

        response = service.mutate_campaign_criteria(
            customer_id=customer_id, operations=operations,
        )
        for i, result in enumerate(response.results):
            resource_name = result.resource_name
            negatives[i].google_resource_name = resource_name
            negatives[i].google_criterion_id = resource_name.split("~")[-1]

    def batch_add_ad_group_negatives(
        self,
        db: Session,
        ad_group: "AdGroup",
        negatives: list["NegativeKeyword"],
    ) -> None:
        """Add multiple ad-group-level negative keywords in a single API call."""
        if not self.client or not negatives:
            return
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for batch ad-group negative mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for batch ad-group negative mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        ad_group_path = self.client.get_service("AdGroupService").ad_group_path(
            customer_id, str(ad_group.google_ad_group_id),
        )

        operations = []
        for neg in negatives:
            op = self.client.get_type("AdGroupCriterionOperation")
            criterion = op.create
            criterion.ad_group = ad_group_path
            criterion.negative = True
            criterion.keyword.text = neg.text
            criterion.keyword.match_type = getattr(
                self.client.enums.KeywordMatchTypeEnum, neg.match_type,
            )
            operations.append(op)

        response = service.mutate_ad_group_criteria(
            customer_id=customer_id, operations=operations,
        )
        for i, result in enumerate(response.results):
            resource_name = result.resource_name
            negatives[i].google_resource_name = resource_name
            negatives[i].google_criterion_id = resource_name.split("~")[-1]

    def _mutate_campaign_budget(self, campaign, db: Session):
        """Update campaign budget amount in Google Ads."""
        if not self.client:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for budget mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        ga_service = self.client.get_service("GoogleAdsService")
        campaign_id_int = int(campaign.google_campaign_id)
        query = f"""
            SELECT
                campaign.campaign_budget
            FROM campaign
            WHERE campaign.id = {campaign_id_int}
        """
        response = list(ga_service.search(customer_id=customer_id, query=query))
        if not response:
            raise RuntimeError("Campaign budget resource not found")
        budget_resource = response[0].campaign.campaign_budget

        budget_service = self.client.get_service("CampaignBudgetService")
        operation = self.client.get_type("CampaignBudgetOperation")
        budget = operation.update
        budget.resource_name = budget_resource
        budget.amount_micros = int(campaign.budget_micros or 0)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        operation.update_mask.CopyFrom(field_mask)
        budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[operation])

    def _mutate_campaign_status(self, campaign, db: Session, new_status: str):
        """Pause or enable a campaign via CampaignService."""
        if not self.client:
            return
        if new_status not in ("ENABLED", "PAUSED"):
            raise ValueError(f"Invalid campaign status: {new_status}")

        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for campaign status mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("CampaignService")
        operation = self.client.get_type("CampaignOperation")
        campaign_resource = service.campaign_path(customer_id, campaign.google_campaign_id)
        campaign_obj = operation.update
        campaign_obj.resource_name = campaign_resource
        campaign_obj.status = getattr(self.client.enums.CampaignStatusEnum, new_status)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_campaigns(customer_id=customer_id, operations=[operation])

    def _mutate_campaign_bidding_target(self, campaign, db: Session, field: str, value):
        """Update campaign target_cpa or target_roas in Google Ads."""
        if not self.client:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for bidding target mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("CampaignService")
        operation = self.client.get_type("CampaignOperation")
        campaign_resource = service.campaign_path(customer_id, campaign.google_campaign_id)
        campaign_obj = operation.update
        campaign_obj.resource_name = campaign_resource

        field_mask = self.client.get_type("FieldMask")

        if field == "target_cpa_micros":
            campaign_obj.target_cpa.target_cpa_micros = int(value)
            field_mask.paths.append("target_cpa.target_cpa_micros")
        elif field == "target_roas":
            campaign_obj.target_roas.target_roas = float(value)
            field_mask.paths.append("target_roas.target_roas")
        else:
            raise ValueError(f"Unknown bidding field: {field}")

        operation.update_mask.CopyFrom(field_mask)
        service.mutate_campaigns(customer_id=customer_id, operations=[operation])

    # -----------------------------------------------------------------------
    # Offline Conversions Upload
    # -----------------------------------------------------------------------

    def upload_offline_conversions(self, db: Session, customer_id: str,
                                    conversions: list[dict]) -> dict:
        """Upload offline conversions via Google Ads API."""
        from app.models.offline_conversion import OfflineConversion

        if not self.is_connected:
            return {"status": "error", "message": "API not connected", "uploaded": 0}

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return {"status": "error", "message": "Client not found", "uploaded": 0}

        service = self.client.get_service("ConversionUploadService")
        upload_operations = []

        for conv in conversions:
            click_conversion = self.client.get_type("ClickConversion")
            click_conversion.gclid = conv["gclid"]
            click_conversion.conversion_action = self.client.get_service(
                "ConversionActionService"
            ).conversion_action_path(normalized, conv.get("conversion_action_id", ""))
            click_conversion.conversion_date_time = conv["conversion_time"]
            if conv.get("conversion_value"):
                click_conversion.conversion_value = float(conv["conversion_value"])
            if conv.get("currency_code"):
                click_conversion.currency_code = conv["currency_code"]
            upload_operations.append(click_conversion)

        try:
            response = service.upload_click_conversions(
                customer_id=normalized,
                conversions=upload_operations,
                partial_failure=True,
            )

            uploaded = 0
            errors = []
            for i, result in enumerate(response.results):
                if result.gclid:
                    uploaded += 1
                    # Update local record status
                    local = db.query(OfflineConversion).filter(
                        OfflineConversion.client_id == client_record.id,
                        OfflineConversion.gclid == conversions[i]["gclid"],
                    ).first()
                    if local:
                        local.upload_status = "UPLOADED"
                        from datetime import datetime, timezone
                        local.uploaded_at = datetime.now(timezone.utc).replace(tzinfo=None)

            if response.partial_failure_error:
                errors.append(str(response.partial_failure_error))

            db.commit()
            return {
                "status": "success" if uploaded > 0 else "partial",
                "uploaded": uploaded,
                "total": len(conversions),
                "errors": errors,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": self._format_google_ads_error(e),
                "uploaded": 0,
            }

    # -----------------------------------------------------------------------
    # Placement Exclusion
    # -----------------------------------------------------------------------

    def add_placement_exclusion(self, db: Session, customer_id: str,
                                 campaign_google_id: str, placement_url: str) -> dict:
        """Add a placement exclusion to a Display/Video campaign."""
        if not self.is_connected:
            return {"status": "local_only", "message": "Saved locally — API not connected"}

        normalized = self.normalize_customer_id(customer_id)
        service = self.client.get_service("CampaignCriterionService")
        operation = self.client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = self.client.get_service("CampaignService").campaign_path(
            normalized, campaign_google_id,
        )
        criterion.negative = True
        criterion.placement.url = placement_url

        try:
            response = service.mutate_campaign_criteria(
                customer_id=normalized, operations=[operation]
            )
            return {
                "status": "success",
                "message": f"Excluded placement: {placement_url}",
                "resource_name": response.results[0].resource_name if response.results else None,
            }
        except Exception as e:
            return {"status": "error", "message": self._format_google_ads_error(e)}
