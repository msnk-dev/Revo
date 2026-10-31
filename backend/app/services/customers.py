from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import Customer, Invoice, Payment, PaymentMethod, User
from app.schemas.contract import PaymentOut
from app.schemas.customers import CustomerCreateIn


def list_customers(db: Session, page: int, page_size: int, q: str | None):
    query = select(Customer).where(Customer.is_active.is_(True))
    count = select(func.count()).select_from(Customer).where(Customer.is_active.is_(True))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where((Customer.name.ilike(pattern)) | (Customer.email.ilike(pattern)))
        count = count.where((Customer.name.ilike(pattern)) | (Customer.email.ilike(pattern)))
    return (
        list(db.scalars(query.order_by(Customer.name, Customer.id).offset((page - 1) * page_size).limit(page_size))),
        db.scalar(count) or 0,
    )


def get_customer(db: Session, actor: Actor, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise NotFoundError("Customer not found")
    if actor.role == "customer" and (actor.customer_id != customer.id or customer.user_id != actor.user_id):
        raise NotFoundError("Customer not found")
    return customer


def create_customer(db: Session, payload: CustomerCreateIn) -> Customer:
    customer = Customer(**payload.model_dump(), is_active=True)
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Customer conflicts with an existing account") from exc
    db.refresh(customer)
    return customer


def update_customer(db: Session, actor: Actor, customer_id: int, payload: CustomerCreateIn) -> Customer:
    customer = get_customer(db, actor, customer_id)
    if actor.role == "customer" and set(payload.model_fields_set) - {"name", "phone", "company", "billing_address", "tax_id"}:
        raise ForbiddenError("Customers cannot change their account email")
    for field, value in payload.model_dump().items():
        if actor.role != "customer" or field != "email":
            setattr(customer, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Customer update conflicts with an existing account") from exc
    db.refresh(customer)
    return customer


def deactivate_customer(db: Session, customer_id: int) -> None:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    if customer.user_id is not None:
        user = db.get(User, customer.user_id)
        if user is not None:
            user.is_active = False
            user.token_version += 1
    customer.is_active = False
    db.commit()


def get_payment_history(db: Session, customer_id: int, limit: int = 20) -> list[PaymentOut]:
    rows = db.execute(
        select(Payment, PaymentMethod.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(PaymentMethod, PaymentMethod.id == Payment.method_id)
        .where(Invoice.customer_id == customer_id)
        .order_by(Payment.paid_on.desc(), Payment.id.desc())
        .limit(max(1, min(limit, 100)))
    )
    return [PaymentOut(id=payment.id, invoice_id=payment.invoice_id, amount=payment.amount,
                       paid_on=payment.paid_on, method=method) for payment, method in rows]
