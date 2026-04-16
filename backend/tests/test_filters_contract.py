"""Contract test — every data endpoint in the canonical registry must declare
`Depends(common_filters)`. This is the gate that prevents regression to bespoke
filter signatures.

To add a new data endpoint to the canonical list:
1. Declare `filters: CommonFilters = Depends(common_filters)` in the route handler.
2. Add the route path to `DATA_ENDPOINTS` below.
3. Run this test.
"""

from fastapi.dependencies.utils import get_dependant

from app.dependencies import common_filters
from app.main import app

# Canonical list of endpoints that must use common_filters.
# Grow this as endpoints are migrated. Never remove — only add.
DATA_ENDPOINTS: set[tuple[str, str]] = {
    ("GET", "/api/v1/campaigns/"),
    ("GET", "/api/v1/keywords/"),
    ("GET", "/api/v1/analytics/dashboard-kpis"),
}


def _uses_common_filters(route) -> bool:
    """Walk the FastAPI dependant tree and check if common_filters is present."""
    dependant = get_dependant(path=route.path, call=route.endpoint)
    queue = list(dependant.dependencies)
    while queue:
        dep = queue.pop()
        if dep.call is common_filters:
            return True
        queue.extend(dep.dependencies)
    return False


def test_data_endpoints_declared_correctly_in_app():
    """Every route in DATA_ENDPOINTS must actually exist in the FastAPI app."""
    known = {(method, route.path) for route in app.routes for method in getattr(route, "methods", set())}
    missing = DATA_ENDPOINTS - known
    assert not missing, f"DATA_ENDPOINTS references unknown routes: {missing}"


def test_all_data_endpoints_use_common_filters():
    """Every endpoint in DATA_ENDPOINTS must declare Depends(common_filters)."""
    violators: list[tuple[str, str]] = []
    for route in app.routes:
        methods = getattr(route, "methods", set())
        for method in methods:
            if (method, route.path) in DATA_ENDPOINTS:
                if not _uses_common_filters(route):
                    violators.append((method, route.path))
    assert not violators, (
        f"Endpoints in DATA_ENDPOINTS but missing Depends(common_filters): {violators}. "
        "Add `filters: CommonFilters = Depends(common_filters)` to the handler."
    )
