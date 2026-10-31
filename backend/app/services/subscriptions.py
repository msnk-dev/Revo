from sqlalchemy.orm import Session

from app.schemas.contract import SubscriptionOut


def list_for_customer(db: Session, customer_id: int) -> list[SubscriptionOut]:
    return []

