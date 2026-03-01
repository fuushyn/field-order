from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import SalesRep, Retailer, Product, Order, OrderItem
from schemas import OrderCreate, OrderOut, OrderItemOut, OrderStatusUpdate
from auth import get_current_rep

router = APIRouter(tags=["orders"])


def _order_to_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        retailer_id=order.retailer_id,
        retailer_name=order.retailer.name,
        rep_id=order.rep_id,
        status=order.status,
        total=order.total,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in order.items
        ],
    )


@router.post("/orders", response_model=OrderOut)
def create_order(
    body: OrderCreate,
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    retailer = (
        db.query(Retailer)
        .filter(Retailer.id == body.retailer_id, Retailer.rep_id == rep.id)
        .first()
    )
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    total = 0.0
    order_items = []
    for item in body.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        subtotal = round(product.unit_price * item.quantity, 2)
        total += subtotal
        order_items.append(
            OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.unit_price,
                subtotal=subtotal,
            )
        )

    order = Order(
        retailer_id=body.retailer_id,
        rep_id=rep.id,
        total=round(total, 2),
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_to_out(order)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    retailer_id: int | None = None,
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    q = db.query(Order).filter(Order.rep_id == rep.id)
    if retailer_id is not None:
        q = q.filter(Order.retailer_id == retailer_id)
    orders = q.order_by(Order.created_at.desc()).all()
    return [_order_to_out(o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.rep_id == rep.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_out(order)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    if body.status not in ("pending", "confirmed", "delivered"):
        raise HTTPException(status_code=400, detail="Invalid status")

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.rep_id == rep.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = body.status
    db.commit()
    db.refresh(order)
    return _order_to_out(order)
