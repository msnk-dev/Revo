from sqlalchemy.orm import Session

from app.schemas.contract import PaymentOut


def get_payment_history(db: Session, customer_id: int, limit: int = 20) -> list[PaymentOut]:
    return []

