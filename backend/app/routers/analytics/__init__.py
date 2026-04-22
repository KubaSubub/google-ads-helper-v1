"""Analytics router package.

Aggregates domain sub-routers under the `/analytics` prefix.
During migration, `_legacy` holds endpoints not yet extracted; new domain
sub-routers (`_kpis`, `_health`, ...) are added incrementally and legacy
shrinks until it can be removed.
"""

from fastapi import APIRouter

from app.routers.analytics._auction import router as _auction_router
from app.routers.analytics._audience import router as _audience_router
from app.routers.analytics._bidding import router as _bidding_router
from app.routers.analytics._breakdown import router as _breakdown_router
from app.routers.analytics._comparison import router as _comparison_router
from app.routers.analytics._dsa import router as _dsa_router
from app.routers.analytics._health import router as _health_router
from app.routers.analytics._insights import router as _insights_router
from app.routers.analytics._kpis import router as _kpis_router
from app.routers.analytics._legacy import router as _legacy_router
from app.routers.analytics._mcc_misc import router as _mcc_misc_router
from app.routers.analytics._pacing import router as _pacing_router
from app.routers.analytics._pmax import router as _pmax_router
from app.routers.analytics._quality import router as _quality_router
from app.routers.analytics._shopping import router as _shopping_router
from app.routers.analytics._waste import router as _waste_router

router = APIRouter(prefix="/analytics", tags=["Analytics"])
router.include_router(_legacy_router)
router.include_router(_auction_router)
router.include_router(_audience_router)
router.include_router(_bidding_router)
router.include_router(_breakdown_router)
router.include_router(_comparison_router)
router.include_router(_dsa_router)
router.include_router(_health_router)
router.include_router(_insights_router)
router.include_router(_kpis_router)
router.include_router(_mcc_misc_router)
router.include_router(_pacing_router)
router.include_router(_pmax_router)
router.include_router(_quality_router)
router.include_router(_shopping_router)
router.include_router(_waste_router)

__all__ = ["router"]
