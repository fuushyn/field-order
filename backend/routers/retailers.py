from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import SalesRep, Retailer
from schemas import RetailerOut
from auth import get_current_rep

router = APIRouter(tags=["retailers"])


@router.get("/retailers", response_model=list[RetailerOut])
def list_retailers(
    search: str = "",
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    q = db.query(Retailer).filter(Retailer.rep_id == rep.id)
    if search:
        q = q.filter(Retailer.name.ilike(f"%{search}%"))
    return q.all()


@router.get("/retailers/{retailer_id}", response_model=RetailerOut)
def get_retailer(
    retailer_id: int,
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    retailer = (
        db.query(Retailer)
        .filter(Retailer.id == retailer_id, Retailer.rep_id == rep.id)
        .first()
    )
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")
    return retailer
