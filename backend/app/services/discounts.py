from datetime import date
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Discount, DiscountProduct, Product
from app.schemas.contract import DiscountOut
from app.schemas.discounts import DiscountCreateIn


def _detail(db: Session, row: Discount) -> dict:
    products = list(db.scalars(select(DiscountProduct.product_id).where(DiscountProduct.discount_id == row.id).order_by(DiscountProduct.product_id)))
    return {"id": row.id, "name": row.name, "type": row.type, "value": row.value, "scope": row.scope,
            "min_purchase": row.min_purchase, "min_quantity": row.min_quantity, "start_date": row.start_date,
            "end_date": row.end_date, "max_uses": row.max_uses, "uses_count": row.uses_count,
            "is_active": row.is_active, "product_ids": products}


def list_discounts(db: Session, page: int, page_size: int, q: str | None):
    query = select(Discount)
    count = select(func.count()).select_from(Discount)
    if q:
        query = query.where(Discount.name.ilike(f"%{q.strip()}%"))
        count = count.where(Discount.name.ilike(f"%{q.strip()}%"))
    rows = list(db.scalars(query.order_by(Discount.name, Discount.id).offset((page - 1) * page_size).limit(page_size)))
    row_ids = [row.id for row in rows]
    product_map: dict[int, list[int]] = {row_id: [] for row_id in row_ids}
    if row_ids:
        for discount_id, product_id in db.execute(
            select(DiscountProduct.discount_id, DiscountProduct.product_id)
            .where(DiscountProduct.discount_id.in_(row_ids)).order_by(DiscountProduct.product_id)
        ):
            product_map[discount_id].append(product_id)
    return [
        {"id": row.id, "name": row.name, "type": row.type, "value": row.value, "scope": row.scope,
         "min_purchase": row.min_purchase, "min_quantity": row.min_quantity, "start_date": row.start_date,
         "end_date": row.end_date, "max_uses": row.max_uses, "uses_count": row.uses_count,
         "is_active": row.is_active, "product_ids": product_map[row.id]}
        for row in rows
    ], db.scalar(count) or 0


def get_discount(db: Session, discount_id: int):
    row = db.get(Discount, discount_id)
    if row is None:
        raise NotFoundError("Discount not found")
    return _detail(db, row)


def _validate_products(db: Session, product_ids: list[int]) -> None:
    if not product_ids:
        return
    found = set(db.scalars(select(Product.id).where(Product.id.in_(product_ids), Product.is_active.is_(True))))
    if found != set(product_ids):
        raise ValidationFailed("One or more discount products are unavailable", {"product_ids": "Unknown or inactive product"})


def _save(db: Session, row: Discount, payload: DiscountCreateIn):
    _validate_products(db, payload.product_ids)
    values = payload.model_dump(exclude={"product_ids"})
    for key, value in values.items():
        setattr(row, key, value)
    try:
        db.flush()
        db.execute(DiscountProduct.__table__.delete().where(DiscountProduct.discount_id == row.id))
        db.add_all(DiscountProduct(discount_id=row.id, product_id=product_id) for product_id in payload.product_ids)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Discount conflicts with an existing record") from exc
    db.refresh(row)
    return _detail(db, row)


def create_discount(db: Session, payload: DiscountCreateIn):
    row = Discount(name=payload.name, type=payload.type, value=payload.value, scope=payload.scope,
                   min_purchase=payload.min_purchase, min_quantity=payload.min_quantity,
                   start_date=payload.start_date, end_date=payload.end_date, max_uses=payload.max_uses,
                   uses_count=0, is_active=True)
    db.add(row)
    db.flush()
    return _save(db, row, payload)


def update_discount(db: Session, discount_id: int, payload: DiscountCreateIn):
    row = db.get(Discount, discount_id)
    if row is None:
        raise NotFoundError("Discount not found")
    return _save(db, row, payload)


def deactivate_discount(db: Session, discount_id: int) -> None:
    row = db.get(Discount, discount_id)
    if row is None:
        raise NotFoundError("Discount not found")
    row.is_active = False
    db.commit()


def list_eligible(db: Session, customer_id: int, quantity: int, product_id: int | None = None) -> list[DiscountOut]:
    today = date.today()
    query = select(Discount).where(
        Discount.is_active.is_(True),
        (Discount.start_date.is_(None)) | (Discount.start_date <= today),
        (Discount.end_date.is_(None)) | (Discount.end_date >= today),
        (Discount.max_uses.is_(None)) | (Discount.uses_count < Discount.max_uses),
        Discount.min_quantity <= quantity,
    )
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            return []
        query = query.where(
            (Discount.scope == "subscription")
            | (Discount.id.in_(select(DiscountProduct.discount_id).where(DiscountProduct.product_id == product_id)))
        )
        estimated = product.sales_price * quantity
        query = query.where(Discount.min_purchase <= estimated)
    return [DiscountOut(id=row.id, name=row.name, type=row.type, value=row.value, scope=row.scope) for row in db.scalars(query.order_by(Discount.id))]
