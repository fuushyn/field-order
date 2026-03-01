from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SalesRep, Product
from schemas import ProductOut
from auth import get_current_rep

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(
    search: str = "",
    category: str = "",
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    if category:
        q = q.filter(Product.category == category)
    return q.all()


@router.get("/products/categories", response_model=list[str])
def list_categories(
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    rows = db.query(Product.category).distinct().all()
    return [r[0] for r in rows]
