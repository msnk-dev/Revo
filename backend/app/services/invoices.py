from sqlalchemy.orm import Session

from app.schemas.contract import InvoiceOut


def list_for_customer(db: Session, customer_id: int, status: str | None = None) -> list[InvoiceOut]:
    return []

