"""Google Ads debug helpers for source-of-truth diagnostics."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdGroup, Campaign, Client, Keyword, NegativeKeyword
from app.services.credentials_service import CredentialsService
from app.services.google_ads import google_ads_service


class GoogleAdsDebugService:
    @staticmethod
    def _sqlite_path_from_url(database_url: str) -> Path | None:
        if not database_url.startswith("sqlite:///"):
            return None

        path_part = database_url.removeprefix("sqlite:///")
        if path_part in {"", ":memory:"}:
            return None

        return Path(path_part)

    @staticmethod
    def _mask_value(value: str | None, keep_start: int = 4, keep_end: int = 4) -> str | None:
        if not value:
            return None
        if len(value) <= keep_start + keep_end:
            return "*" * len(value)
        return f"{value[:keep_start]}...{value[-keep_end:]}"

    @staticmethod
    def _metadata_value(metadata: Any, key: str) -> str | None:
        if not metadata:
            return None
        for item_key, item_value in metadata:
            if item_key == key:
                return item_value
        return None

    @staticmethod
    def _criterion_kind_from_negative(negative: bool) -> str:
        return "NEGATIVE" if negative else "POSITIVE"

    @staticmethod
    def _presence_state(api_rows: list[dict[str, Any]], db_rows: list[dict[str, Any]]) -> str:
        if api_rows and db_rows:
            return "API_AND_DB"
        if api_rows:
            return "API_ONLY"
        if db_rows:
            return "DB_ONLY"
        return "NOT_FOUND"

    @staticmethod
    def _classification(api_rows: list[dict[str, Any]], db_rows: list[dict[str, Any]]) -> str:
        source_rows = api_rows or db_rows
        if not source_rows:
            return "UNKNOWN"
        kinds = {row["criterion_kind"] for row in source_rows}
        if len(kinds) == 1:
            return next(iter(kinds))
        return "MIXED"

    @staticmethod
    def _db_paths() -> dict[str, Any]:
        db_path = GoogleAdsDebugService._sqlite_path_from_url(settings.database_url)
        legacy_path = settings.backend_dir / "data" / "google_ads_app.db"
        return {
            "db_source_path": str(db_path) if db_path else None,
            "db_legacy_path": str(legacy_path),
            "db_legacy_exists": legacy_path.exists(),
        }

    def _search_with_call(self, customer_id: str, query: str) -> tuple[list[Any], str | None]:
        ga_service = google_ads_service.client.get_service("GoogleAdsService")
        request = google_ads_service.client.get_type("SearchGoogleAdsRequest")
        request.customer_id = customer_id
        request.query = query
        response, call = ga_service.transport.search.with_call(request=request)
        metadata = call.trailing_metadata() or call.initial_metadata()
        return list(response.results), self._metadata_value(metadata, "request-id")

    def _list_accessible_customers(self) -> dict[str, Any]:
        customer_service = google_ads_service.client.get_service("CustomerService")
        request = google_ads_service.client.get_type("ListAccessibleCustomersRequest")
        response, call = customer_service.transport.list_accessible_customers.with_call(request=request)
        metadata = call.trailing_metadata() or call.initial_metadata()
        customer_ids = [resource_name.split("/")[-1] for resource_name in response.resource_names]
        return {
            "request_id": self._metadata_value(metadata, "request-id"),
            "customer_ids": customer_ids,
        }

    @staticmethod
    def _serialize_customer_client_row(row: Any) -> dict[str, Any]:
        customer_client = row.customer_client
        return {
            "id": str(customer_client.id),
            "client_customer": customer_client.client_customer,
            "descriptive_name": customer_client.descriptive_name,
            "manager": bool(customer_client.manager),
            "level": int(customer_client.level),
            "status": getattr(customer_client.status, "name", str(customer_client.status)),
            "hidden": bool(customer_client.hidden),
            "time_zone": customer_client.time_zone,
            "currency_code": customer_client.currency_code,
        }

    def _lookup_customer_client(self, login_customer_id: str | None, target_customer_id: str) -> dict[str, Any]:
        if not login_customer_id:
            return {
                "request_id": None,
                "login_customer_id": None,
                "rows": [],
                "contains_target_customer": False,
            }

        query = f"""
            SELECT
                customer_client.client_customer,
                customer_client.id,
                customer_client.descriptive_name,
                customer_client.manager,
                customer_client.level,
                customer_client.status,
                customer_client.hidden,
                customer_client.time_zone,
                customer_client.currency_code
            FROM customer_client
            WHERE customer_client.id = {int(target_customer_id)}
        """
        rows, request_id = self._search_with_call(login_customer_id, query)
        return {
            "request_id": request_id,
            "login_customer_id": login_customer_id,
            "query": query,
            "rows": [self._serialize_customer_client_row(row) for row in rows],
            "contains_target_customer": len(rows) > 0,
        }

    @staticmethod
    def _serialize_api_row(row: Any, source_query_type: str, request_id: str | None) -> dict[str, Any]:
        criterion = getattr(row, "ad_group_criterion", None) or getattr(row, "campaign_criterion", None)
        campaign = getattr(row, "campaign", None)
        ad_group = getattr(row, "ad_group", None)
        negative = bool(getattr(criterion, "negative", False))
        return {
            "customer_id": str(row.customer.id) if getattr(row, "customer", None) else None,
            "campaign_id": str(campaign.id) if campaign and getattr(campaign, "id", None) is not None else None,
            "campaign_name": campaign.name if campaign else None,
            "campaign_status": getattr(campaign.status, "name", str(campaign.status)) if campaign and getattr(campaign, "status", None) is not None else None,
            "campaign_advertising_channel_type": (
                getattr(campaign.advertising_channel_type, "name", str(campaign.advertising_channel_type))
                if campaign and getattr(campaign, "advertising_channel_type", None) is not None
                else None
            ),
            "ad_group_id": str(ad_group.id) if ad_group and getattr(ad_group, "id", None) is not None else None,
            "ad_group_name": ad_group.name if ad_group else None,
            "ad_group_status": getattr(ad_group.status, "name", str(ad_group.status)) if ad_group and getattr(ad_group, "status", None) is not None else None,
            "criterion_id": str(criterion.criterion_id) if criterion else None,
            "keyword_text": criterion.keyword.text if criterion and getattr(criterion, "keyword", None) else None,
            "match_type": (
                getattr(criterion.keyword.match_type, "name", str(criterion.keyword.match_type))
                if criterion and getattr(criterion, "keyword", None) and getattr(criterion.keyword, "match_type", None) is not None
                else None
            ),
            "negative": negative,
            "criterion_kind": GoogleAdsDebugService._criterion_kind_from_negative(negative),
            "criterion_status": getattr(criterion.status, "name", str(criterion.status)) if criterion and getattr(criterion, "status", None) is not None else None,
            "request_id": request_id,
            "source_query_type": source_query_type,
            "storage_kind": "API",
            "db_source_path": None,
            "source": "GOOGLE_ADS_API",
        }

    @staticmethod
    def _serialize_positive_db_row(
        keyword: Keyword,
        ad_group: AdGroup,
        campaign: Campaign,
        client: Client,
        db_source_path: str | None,
    ) -> dict[str, Any]:
        return {
            "customer_id": str(client.google_customer_id).replace("-", ""),
            "campaign_id": str(campaign.google_campaign_id),
            "campaign_name": campaign.name,
            "campaign_status": campaign.status,
            "campaign_advertising_channel_type": campaign.campaign_type,
            "ad_group_id": str(ad_group.google_ad_group_id),
            "ad_group_name": ad_group.name,
            "ad_group_status": ad_group.status,
            "criterion_id": str(keyword.google_keyword_id),
            "keyword_text": keyword.text,
            "match_type": keyword.match_type,
            "negative": False,
            "criterion_kind": keyword.criterion_kind or "POSITIVE",
            "criterion_status": keyword.status,
            "request_id": None,
            "source_query_type": "sqlite.keywords",
            "storage_kind": "DB_POSITIVE",
            "db_source_path": db_source_path,
            "source": "LOCAL_CACHE",
            "db_record_id": keyword.id,
            "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None,
        }

    @staticmethod
    def _serialize_negative_db_row(
        keyword: NegativeKeyword,
        client: Client,
        campaign: Campaign | None,
        ad_group: AdGroup | None,
        db_source_path: str | None,
    ) -> dict[str, Any]:
        return {
            "customer_id": str(client.google_customer_id).replace("-", ""),
            "campaign_id": str(campaign.google_campaign_id) if campaign else None,
            "campaign_name": campaign.name if campaign else None,
            "campaign_status": campaign.status if campaign else None,
            "campaign_advertising_channel_type": campaign.campaign_type if campaign else None,
            "ad_group_id": str(ad_group.google_ad_group_id) if ad_group else None,
            "ad_group_name": ad_group.name if ad_group else None,
            "ad_group_status": ad_group.status if ad_group else None,
            "criterion_id": keyword.google_criterion_id,
            "keyword_text": keyword.text,
            "match_type": keyword.match_type,
            "negative": True,
            "criterion_kind": keyword.criterion_kind or "NEGATIVE",
            "criterion_status": keyword.status,
            "request_id": None,
            "source_query_type": "sqlite.negative_keywords",
            "storage_kind": "DB_NEGATIVE",
            "db_source_path": db_source_path,
            "source": keyword.source,
            "negative_scope": keyword.negative_scope,
            "db_record_id": keyword.id,
            "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None,
        }

    @staticmethod
    def _build_keyword_view_query(criterion_id: int) -> str:
        return f"""
            SELECT
                customer.id,
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group_criterion.criterion_id,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type
            FROM keyword_view
            WHERE ad_group_criterion.criterion_id = {criterion_id}
            ORDER BY campaign.id, ad_group.id
        """

    @staticmethod
    def _build_ad_group_criterion_query(criterion_id: int) -> str:
        return f"""
            SELECT
                customer.id,
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group_criterion.criterion_id,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = KEYWORD
              AND ad_group_criterion.criterion_id = {criterion_id}
            ORDER BY campaign.id, ad_group.id
        """

    @staticmethod
    def _build_search_debug_query(include_removed: bool = True, limit: int = 50) -> str:
        filters = []
        if not include_removed:
            filters.extend(
                [
                    "ad_group_criterion.status != 'REMOVED'",
                    "campaign.status != 'REMOVED'",
                ]
            )
        where_clause = ""
        if filters:
            where_clause = "WHERE " + "\n              AND ".join(filters)
        return """
            SELECT
                customer.id,
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group_criterion.criterion_id,
                ad_group_criterion.status,
                ad_group_criterion.negative,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type
            FROM keyword_view
            {where_clause}
            ORDER BY campaign.name, ad_group.name, ad_group_criterion.keyword.text
            LIMIT {limit}
        """.format(where_clause=where_clause, limit=int(limit))

    def search_keyword_sources(
        self,
        db: Session,
        client_id: int,
        search_terms: list[str] | None = None,
        include_removed: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not google_ads_service.is_connected:
            raise RuntimeError("Google Ads API not connected")

        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise RuntimeError("Client not found")

        normalized_customer_id = google_ads_service.normalize_customer_id(client.google_customer_id)
        normalized_terms = [term.strip() for term in (search_terms or []) if term and term.strip()]
        query = self._build_search_debug_query(include_removed=include_removed, limit=limit)
        fetched_at = datetime.now(timezone.utc)
        api_results, request_id = self._search_with_call(normalized_customer_id, query)

        api_rows = []
        for row in api_results:
            serialized = self._serialize_api_row(row, "keyword_view", request_id)
            keyword_text = (serialized.get("keyword_text") or "").lower()
            if normalized_terms and not any(term.lower() in keyword_text for term in normalized_terms):
                continue
            api_rows.append(serialized)
            if len(api_rows) >= limit:
                break

        positive_query = (
            db.query(Keyword, AdGroup, Campaign)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client.id)
        )
        negative_query = (
            db.query(NegativeKeyword, Campaign, AdGroup)
            .outerjoin(Campaign, NegativeKeyword.campaign_id == Campaign.id)
            .outerjoin(AdGroup, NegativeKeyword.ad_group_id == AdGroup.id)
            .filter(NegativeKeyword.client_id == client.id)
        )

        if not include_removed:
            positive_query = positive_query.filter(Keyword.status != "REMOVED")
            negative_query = negative_query.filter(NegativeKeyword.status != "REMOVED")

        if normalized_terms:
            positive_filters = [
                Keyword.text.ilike(f"%{term}%")
                for term in normalized_terms
            ]
            negative_filters = [
                NegativeKeyword.text.ilike(f"%{term}%")
                for term in normalized_terms
            ]
            positive_query = positive_query.filter(or_(*positive_filters))
            negative_query = negative_query.filter(or_(*negative_filters))

        db_info = self._db_paths()
        db_rows = [
            self._serialize_positive_db_row(keyword, ad_group, campaign, client, db_info["db_source_path"])
            for keyword, ad_group, campaign in (
                positive_query
                .order_by(Campaign.name.asc(), AdGroup.name.asc(), Keyword.text.asc())
                .limit(limit)
                .all()
            )
        ]
        db_rows.extend(
            self._serialize_negative_db_row(keyword, client, campaign, ad_group, db_info["db_source_path"])
            for keyword, campaign, ad_group in (
                negative_query
                .order_by(Campaign.name.asc(), AdGroup.name.asc(), NegativeKeyword.text.asc())
                .limit(limit)
                .all()
            )
        )

        return {
            "client_id": client.id,
            "client_name": client.name,
            "customer_id": normalized_customer_id,
            "search_terms": normalized_terms,
            "include_removed": include_removed,
            "limit": limit,
            "fetched_at": fetched_at.isoformat(),
            "query": query,
            "request_ids": {
                "keyword_view": request_id,
            },
            "classification": self._classification(api_rows, db_rows),
            "presence_state": self._presence_state(api_rows, db_rows),
            "synced_to_db": len(db_rows) > 0,
            "api_count": len(api_rows),
            "local_count": len(db_rows),
            "db_rows_found": len(db_rows),
            "db_positive_rows_found": sum(1 for row in db_rows if row["storage_kind"] == "DB_POSITIVE"),
            "db_negative_rows_found": sum(1 for row in db_rows if row["storage_kind"] == "DB_NEGATIVE"),
            "api_rows": api_rows,
            "db_rows": db_rows,
            **db_info,
        }

    def build_keyword_source_of_truth(self, db: Session, client_id: int, criterion_id: int) -> dict[str, Any]:
        if not google_ads_service.is_connected:
            raise RuntimeError("Google Ads API not connected")

        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise RuntimeError("Client not found")

        normalized_customer_id = google_ads_service.normalize_customer_id(client.google_customer_id)
        login_customer_id = google_ads_service.get_login_customer_id()
        keyword_view_query = self._build_keyword_view_query(int(criterion_id))
        ad_group_criterion_query = self._build_ad_group_criterion_query(int(criterion_id))

        keyword_view_rows, keyword_view_request_id = self._search_with_call(normalized_customer_id, keyword_view_query)
        ad_group_rows, ad_group_request_id = self._search_with_call(normalized_customer_id, ad_group_criterion_query)
        accessible_customers = self._list_accessible_customers()
        mcc_customer_lookup = self._lookup_customer_client(login_customer_id, normalized_customer_id)
        db_info = self._db_paths()

        api_rows = [
            self._serialize_api_row(row, "keyword_view", keyword_view_request_id)
            for row in keyword_view_rows
        ]
        api_rows.extend(
            self._serialize_api_row(row, "ad_group_criterion", ad_group_request_id)
            for row in ad_group_rows
        )

        db_positive_rows = (
            db.query(Keyword, AdGroup, Campaign)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client.id,
                Keyword.google_keyword_id == str(criterion_id),
            )
            .order_by(Campaign.google_campaign_id.asc(), AdGroup.google_ad_group_id.asc())
            .all()
        )
        db_negative_rows = (
            db.query(NegativeKeyword, Campaign, AdGroup)
            .outerjoin(Campaign, NegativeKeyword.campaign_id == Campaign.id)
            .outerjoin(AdGroup, NegativeKeyword.ad_group_id == AdGroup.id)
            .filter(
                NegativeKeyword.client_id == client.id,
                NegativeKeyword.google_criterion_id == str(criterion_id),
            )
            .order_by(Campaign.google_campaign_id.asc(), AdGroup.google_ad_group_id.asc())
            .all()
        )

        db_rows = [
            self._serialize_positive_db_row(keyword, ad_group, campaign, client, db_info["db_source_path"])
            for keyword, ad_group, campaign in db_positive_rows
        ]
        db_rows.extend(
            self._serialize_negative_db_row(keyword, client, campaign, ad_group, db_info["db_source_path"])
            for keyword, campaign, ad_group in db_negative_rows
        )

        credentials = CredentialsService.get_google_ads_credentials()
        return {
            "client_id": client.id,
            "client_name": client.name,
            "customer_id": normalized_customer_id,
            "login_customer_id": login_customer_id,
            "criterion_id": str(criterion_id),
            "google_ads_context": {
                "customer_id_used": normalized_customer_id,
                "login_customer_id": login_customer_id,
                "developer_token_masked": self._mask_value(credentials.get("developer_token")),
                "oauth_client_id_masked": self._mask_value(credentials.get("client_id")),
                "refresh_token_present": bool(credentials.get("refresh_token")),
            },
            "accessible_customers": {
                "request_id": accessible_customers["request_id"],
                "customer_ids": accessible_customers["customer_ids"],
                "contains_target_customer": normalized_customer_id in accessible_customers["customer_ids"],
            },
            "mcc_customer_lookup": mcc_customer_lookup,
            "request_ids": {
                "keyword_view": keyword_view_request_id,
                "ad_group_criterion": ad_group_request_id,
                "accessible_customers": accessible_customers["request_id"],
                "mcc_customer_lookup": mcc_customer_lookup["request_id"],
            },
            "classification": self._classification(api_rows, db_rows),
            "presence_state": self._presence_state(api_rows, db_rows),
            "synced_to_db": len(db_rows) > 0,
            "db_rows_found": len(db_rows),
            "db_positive_rows_found": len(db_positive_rows),
            "db_negative_rows_found": len(db_negative_rows),
            "api_rows": api_rows,
            "db_rows": db_rows,
            **db_info,
        }


google_ads_debug_service = GoogleAdsDebugService()
