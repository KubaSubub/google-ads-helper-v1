"""Client CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.schemas import ClientCreate, ClientResponse, ClientUpdate, PaginatedResponse
from app.services.credentials_service import CredentialsService
from app.services.google_ads import google_ads_service

router = APIRouter(prefix="/clients", tags=["Clients"])


def _ensure_discover_ready() -> None:
    diagnostics = google_ads_service.get_connection_diagnostics()
    if not diagnostics["configured"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not diagnostics["authenticated"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not diagnostics["ready"]:
        raise HTTPException(status_code=503, detail=diagnostics["reason"])
    if not CredentialsService.get(CredentialsService.LOGIN_CUSTOMER_ID):
        raise HTTPException(
            status_code=503,
            detail="Brak login_customer_id (MCC). Uzupelnij Login Customer ID w konfiguracji API.",
        )


@router.post("/discover")
def discover_clients(
    customer_ids: str = Query(None, description="Opcjonalne: numery kont Google Ads po przecinku (np. 123-456-7890)"),
    db: Session = Depends(get_db),
):
    """Auto-discover client accounts from Google Ads MCC and add them to DB."""
    _ensure_discover_ready()

    try:
        accounts = google_ads_service.discover_accounts()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not accounts:
        return {
            "message": "Nie znaleziono kont klienckich w MCC.",
            "added": 0,
            "skipped": 0,
        }

    if customer_ids:
        requested = {
            cid.replace("-", "").strip() for cid in customer_ids.split(",") if cid.strip()
        }
        accounts = [
            account
            for account in accounts
            if account["customer_id"].replace("-", "") in requested
        ]
        if not accounts:
            return {
                "message": "Nie znaleziono podanych kont w MCC.",
                "added": 0,
                "skipped": 0,
            }

    added = 0
    skipped = 0
    for account in accounts:
        existing = db.query(Client).filter(
            Client.google_customer_id == account["customer_id"]
        ).first()
        if existing:
            skipped += 1
            continue

        db.add(Client(name=account["name"], google_customer_id=account["customer_id"]))
        added += 1

    db.commit()
    logger.info(f"Discover: added={added}, skipped={skipped}")
    return {
        "message": f"Dodano {added} klientow ({skipped} juz istnialo).",
        "added": added,
        "skipped": skipped,
    }


@router.get("/", response_model=PaginatedResponse)
def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    """List all clients with pagination and optional search."""
    query = db.query(Client)
    if search:
        query = query.filter(Client.name.ilike(f"%{search}%"))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a single client by ID."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/", response_model=ClientResponse, status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client."""
    existing = db.query(Client).filter(Client.google_customer_id == data.google_customer_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Client with this Google Customer ID already exists")

    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db)):
    """Partially update a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Delete a client and all associated data (cascade)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(client)
    db.commit()
    return {"message": f"Client '{client.name}' deleted", "success": True}
