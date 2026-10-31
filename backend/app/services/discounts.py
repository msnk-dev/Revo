from sqlalchemy.orm import Session

from app.schemas.contract import DiscountOut


def list_eligible(db: Session, customer_id: int, quantity: int, product_id: int | None = None) -> list[DiscountOut]:
    return []

