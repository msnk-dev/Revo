from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Sequence, delete, func, select
from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import ForbiddenError, NotFoundError, ValidationFailed
from app.models import (
    Customer,
    Plan,
    Product,
    Subscription,
    SubscriptionLine,
    SubscriptionLineVariant,
    SubscriptionStatusHistory,
    QuotationTemplate,
    QuotationTemplateLine,
    QuotationTemplateLineVariant,
)
from app.schemas.contract import SubscriptionOut
from app.schemas.subscriptions import SubscriptionCreateIn, SubscriptionLineIn, SubscriptionUpdateIn
from app.services import catalog as catalog_service


def list_for_customer(db: Session, customer_id: int) -> list[SubscriptionOut]:
    rows = db.scalars(
        select(Subscription).where(Subscription.customer_id == customer_id).order_by(Subscription.created_at.desc())
    )
    return [
        SubscriptionOut(
            id=row.id, number=row.number, customer_id=row.customer_id, plan_id=row.plan_id,
            status=row.status, start_date=row.start_date, next_invoice_date=row.next_invoice_date,
            is_paused=row.is_paused,
        )
        for row in rows
    ]


def _number(db: Session, new_id: int) -> str:
    is_postgres = db.bind is not None and db.bind.dialect.name == "postgresql"
    for attempt in range(1000):
        value = db.scalar(select(Sequence("subscription_number_seq").next_value())) if is_postgres else new_id + attempt
        number = f"SUB-{int(value):06d}"
        if db.scalar(select(Subscription.id).where(Subscription.number == number)) is None:
            return number
    raise RuntimeError("Could not allocate a unique subscription number")


def _history(db: Session, subscription: Subscription, old: str | None, new: str, actor_id: int | None) -> None:
    db.add(
        SubscriptionStatusHistory(
            subscription_id=subscription.id,
            from_status=old,
            to_status=new,
            changed_by=actor_id,
            changed_at=datetime.now(timezone.utc),
        )
    )


def _get(db: Session, actor: Actor, subscription_id: int, *, lock: bool = False) -> Subscription:
    query = select(Subscription).where(Subscription.id == subscription_id)
    if actor.role == "customer":
        query = query.where(Subscription.customer_id == actor.customer_id)
    if lock:
        query = query.with_for_update()
    subscription = db.scalar(query)
    if subscription is None:
        raise NotFoundError("Subscription not found")
    return subscription


def _assert_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise ValidationFailed("The selected customer is unavailable", {"customer_id": "Unknown or inactive customer"})
    return customer


def _assert_plan(db: Session, plan_id: int, on_date: date) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None or not plan.is_active or not catalog_service.plan_is_available(plan, on_date):
        raise ValidationFailed("The selected plan is unavailable", {"plan_id": "Unknown, inactive, or unavailable plan"})
    return plan


def _add_lines(db: Session, subscription: Subscription, plan: Plan, lines: list[SubscriptionLineIn]) -> None:
    for index, line_input in enumerate(lines):
        if line_input.quantity < plan.min_quantity:
            raise ValidationFailed(
                "Each subscription line must meet the plan minimum quantity",
                {"lines": f"Line {index + 1} quantity must be at least {plan.min_quantity}"},
            )
        product = db.get(Product, line_input.product_id)
        if product is None or not product.is_active:
            raise ValidationFailed("The selected product is unavailable", {"lines": f"Line {index + 1} product is unavailable"})
        calculated = catalog_service.calculate_unit_price(db, product.id, line_input.variant_value_ids)
        variant_extra = calculated - product.sales_price
        price = (plan.price if index == 0 else product.sales_price) + variant_extra
        line = SubscriptionLine(
            subscription_id=subscription.id,
            product_id=product.id,
            description=line_input.description or product.name,
            quantity=line_input.quantity,
            unit_price=price,
            tax_id=product.default_tax_id,
        )
        db.add(line)
        db.flush()
        db.add_all(
            SubscriptionLineVariant(line_id=line.id, variant_value_id=value_id)
            for value_id in line_input.variant_value_ids
        )


def create_subscription(db: Session, actor: Actor, payload: SubscriptionCreateIn) -> Subscription:
    if actor.role == "customer" and actor.customer_id != payload.customer_id:
        raise ForbiddenError("Customers can only create their own subscriptions")
    _assert_customer(db, payload.customer_id)
    plan = _assert_plan(db, payload.plan_id, payload.start_date)
    if payload.expiry_date is not None and payload.expiry_date < payload.start_date:
        raise ValidationFailed("Expiry must be on or after start date", {"expiry_date": "Must be on or after start_date"})
    subscription = Subscription(
        number="pending",
        customer_id=payload.customer_id,
        plan_id=plan.id,
        status="draft",
        start_date=payload.start_date,
        expiry_date=payload.expiry_date,
        payment_terms_days=payload.payment_terms_days,
        created_by=actor.user_id,
    )
    db.add(subscription)
    db.flush()
    subscription.number = _number(db, subscription.id)
    _add_lines(db, subscription, plan, payload.lines)
    _history(db, subscription, None, "draft", actor.user_id)
    db.commit()
    db.refresh(subscription)
    return subscription


def create_from_template(db: Session, actor: Actor, template_id: int, customer_id: int, start_date: date) -> Subscription:
    if actor.role == "customer" and actor.customer_id != customer_id:
        raise ForbiddenError("Customers can only create their own subscriptions")
    customer = _assert_customer(db, customer_id)
    template = db.get(QuotationTemplate, template_id)
    if template is None:
        raise NotFoundError("Quotation template not found")
    plan = _assert_plan(db, template.plan_id, start_date)
    lines = list(db.scalars(select(QuotationTemplateLine).where(QuotationTemplateLine.template_id == template.id)))
    line_inputs = []
    for template_line in lines:
        variants = db.scalars(
            select(QuotationTemplateLineVariant.variant_value_id).where(
                QuotationTemplateLineVariant.line_id == template_line.id
            )
        )
        line_inputs.append(
            SubscriptionLineIn(
                product_id=template_line.product_id,
                quantity=template_line.quantity,
                variant_value_ids=list(variants),
            )
        )
    if not line_inputs:
        raise ValidationFailed("Quotation template must have at least one line", {"template_id": "No lines configured"})
    subscription = Subscription(
        number="pending", customer_id=customer.id, plan_id=plan.id, status="quotation",
        start_date=start_date, quotation_expires_on=date.today() + timedelta(days=template.validity_days),
        created_by=actor.user_id,
    )
    db.add(subscription)
    db.flush()
    subscription.number = _number(db, subscription.id)
    _add_lines(db, subscription, plan, line_inputs)
    _history(db, subscription, None, "quotation", actor.user_id)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_subscription(db: Session, actor: Actor, subscription_id: int) -> Subscription:
    return _get(db, actor, subscription_id)


def update_subscription(db: Session, actor: Actor, subscription_id: int, payload: SubscriptionUpdateIn) -> Subscription:
    subscription = _get(db, actor, subscription_id, lock=True)
    if subscription.status != "draft":
        raise ValidationFailed("Only draft subscriptions can be edited")
    start_date = payload.start_date or subscription.start_date
    expiry_date = payload.expiry_date if "expiry_date" in payload.model_fields_set else subscription.expiry_date
    if expiry_date is not None and expiry_date < start_date:
        raise ValidationFailed("Expiry must be on or after start date", {"expiry_date": "Must be on or after start_date"})
    plan = _assert_plan(db, subscription.plan_id, start_date)
    subscription.start_date = start_date
    subscription.expiry_date = expiry_date
    if payload.payment_terms_days is not None:
        subscription.payment_terms_days = payload.payment_terms_days
    if payload.lines is not None:
        line_ids = select(SubscriptionLine.id).where(SubscriptionLine.subscription_id == subscription.id)
        db.execute(delete(SubscriptionLineVariant).where(SubscriptionLineVariant.line_id.in_(line_ids)))
        db.execute(delete(SubscriptionLine).where(SubscriptionLine.subscription_id == subscription.id))
        _add_lines(db, subscription, plan, payload.lines)
    db.commit()
    db.refresh(subscription)
    return subscription


def list_subscriptions(db: Session, actor: Actor, page: int, page_size: int, status_filter: str | None):
    query = select(Subscription)
    count = select(func.count()).select_from(Subscription)
    if actor.role == "customer":
        query = query.where(Subscription.customer_id == actor.customer_id)
        count = count.where(Subscription.customer_id == actor.customer_id)
    if status_filter:
        query = query.where(Subscription.status == status_filter)
        count = count.where(Subscription.status == status_filter)
    return (
        list(db.scalars(query.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size))),
        db.scalar(count) or 0,
    )


def _detail(db: Session, subscription: Subscription) -> dict:
    lines = list(db.scalars(select(SubscriptionLine).where(SubscriptionLine.subscription_id == subscription.id)))
    line_outputs = []
    for line in lines:
        variant_ids = list(db.scalars(select(SubscriptionLineVariant.variant_value_id).where(SubscriptionLineVariant.line_id == line.id)))
        line_outputs.append({**{name: getattr(line, name) for name in ("id", "product_id", "description", "quantity", "unit_price", "tax_id")}, "variant_value_ids": variant_ids})
    history = list(db.scalars(select(SubscriptionStatusHistory).where(SubscriptionStatusHistory.subscription_id == subscription.id).order_by(SubscriptionStatusHistory.changed_at, SubscriptionStatusHistory.id)))
    return {
        **{name: getattr(subscription, name) for name in ("id", "number", "customer_id", "plan_id", "status", "start_date", "expiry_date", "next_invoice_date", "payment_terms_days", "quotation_expires_on", "is_paused", "paused_at", "closed_at")},
        "lines": line_outputs,
        "history": history,
    }


def as_detail_list(db: Session, subscriptions: list[Subscription]) -> list[dict]:
    if not subscriptions:
        return []
    subscription_ids = [row.id for row in subscriptions]
    lines = list(db.scalars(select(SubscriptionLine).where(SubscriptionLine.subscription_id.in_(subscription_ids)).order_by(SubscriptionLine.id)))
    line_ids = [line.id for line in lines]
    variant_map: dict[int, list[int]] = {line_id: [] for line_id in line_ids}
    if line_ids:
        pairs = db.execute(select(SubscriptionLineVariant.line_id, SubscriptionLineVariant.variant_value_id)
                           .where(SubscriptionLineVariant.line_id.in_(line_ids)).order_by(SubscriptionLineVariant.id))
        for line_id, value_id in pairs:
            variant_map[line_id].append(value_id)
    history_map: dict[int, list[SubscriptionStatusHistory]] = {sub_id: [] for sub_id in subscription_ids}
    for item in db.scalars(select(SubscriptionStatusHistory).where(SubscriptionStatusHistory.subscription_id.in_(subscription_ids))
                           .order_by(SubscriptionStatusHistory.changed_at, SubscriptionStatusHistory.id)):
        history_map[item.subscription_id].append(item)
    lines_map: dict[int, list[dict]] = {sub_id: [] for sub_id in subscription_ids}
    for line in lines:
        lines_map[line.subscription_id].append({
            **{name: getattr(line, name) for name in ("id", "product_id", "description", "quantity", "unit_price", "tax_id")},
            "variant_value_ids": variant_map[line.id],
        })
    return [
        {
            **{name: getattr(subscription, name) for name in ("id", "number", "customer_id", "plan_id", "status", "start_date", "expiry_date", "next_invoice_date", "payment_terms_days", "quotation_expires_on", "is_paused", "paused_at", "closed_at")},
            "lines": lines_map[subscription.id],
            "history": history_map[subscription.id],
        }
        for subscription in subscriptions
    ]


def transition(db: Session, actor: Actor, subscription_id: int, target: str, today: date | None = None) -> Subscription:
    subscription = _get(db, actor, subscription_id, lock=True)
    current_date = today or date.today()
    if target == "quotation" and subscription.status == "draft":
        if not db.scalar(select(func.count()).select_from(SubscriptionLine).where(SubscriptionLine.subscription_id == subscription.id)):
            raise ValidationFailed("A quotation needs at least one line")
        _assert_customer(db, subscription.customer_id)
        plan = _assert_plan(db, subscription.plan_id, subscription.start_date)
        _ = plan
    elif target == "confirmed" and subscription.status == "quotation":
        if subscription.quotation_expires_on is not None and subscription.quotation_expires_on < current_date:
            raise ValidationFailed("Quotation has expired", {"quotation_expires_on": "Expired quotations cannot be confirmed"})
    elif target == "active" and subscription.status == "confirmed":
        if actor.role == "customer":
            raise ForbiddenError("Only staff can activate a subscription")
        if subscription.start_date > current_date:
            raise ValidationFailed("Subscription cannot start yet", {"start_date": "Activation is allowed on or after the start date"})
        if subscription.expiry_date is not None and subscription.expiry_date < current_date:
            raise ValidationFailed("Subscription has already expired", {"expiry_date": "Cannot activate an expired subscription"})
        subscription.next_invoice_date = subscription.start_date
    else:
        raise ValidationFailed(f"Cannot transition subscription from {subscription.status} to {target}")
    old = subscription.status
    subscription.status = target
    _history(db, subscription, old, target, actor.user_id)
    db.commit()
    db.refresh(subscription)
    return subscription


def pause(db: Session, actor: Actor, subscription_id: int) -> Subscription:
    subscription = _get(db, actor, subscription_id, lock=True)
    plan = db.get(Plan, subscription.plan_id)
    if subscription.status != "active" or subscription.is_paused or plan is None or not plan.pausable:
        raise ValidationFailed("Subscription cannot be paused")
    subscription.is_paused = True
    subscription.paused_at = datetime.now(timezone.utc)
    db.commit()
    return subscription


def resume(db: Session, actor: Actor, subscription_id: int) -> Subscription:
    subscription = _get(db, actor, subscription_id, lock=True)
    if subscription.status != "active" or not subscription.is_paused:
        raise ValidationFailed("Subscription is not paused")
    subscription.is_paused = False
    subscription.paused_at = None
    db.commit()
    return subscription


def close(db: Session, actor: Actor, subscription_id: int) -> Subscription:
    subscription = _get(db, actor, subscription_id, lock=True)
    plan = db.get(Plan, subscription.plan_id)
    if subscription.status != "active":
        raise ValidationFailed("Only active subscriptions can be closed")
    if actor.role == "customer" and (subscription.status != "active" or plan is None or not plan.closable):
        raise ForbiddenError("This subscription cannot be closed by the customer")
    old = subscription.status
    subscription.status = "closed"
    subscription.is_paused = False
    subscription.closed_at = datetime.now(timezone.utc)
    _history(db, subscription, old, "closed", actor.user_id)
    db.commit()
    db.refresh(subscription)
    return subscription


def renew(db: Session, actor: Actor, subscription_id: int) -> Subscription:
    old = _get(db, actor, subscription_id, lock=True)
    plan = db.get(Plan, old.plan_id)
    if plan is None or not plan.renewable or old.expiry_date is None or old.status not in {"active", "closed"}:
        raise ValidationFailed("Subscription is not renewable or has no expiry date")
    next_start = date.fromordinal(old.expiry_date.toordinal() + 1)
    if actor.role == "customer" and old.customer_id != actor.customer_id:
        raise NotFoundError("Subscription not found")
    new = Subscription(
        number="pending", customer_id=old.customer_id, plan_id=old.plan_id, status="draft",
        start_date=next_start, payment_terms_days=old.payment_terms_days, created_by=actor.user_id,
    )
    db.add(new)
    db.flush()
    new.number = _number(db, new.id)
    old_lines = list(db.scalars(select(SubscriptionLine).where(SubscriptionLine.subscription_id == old.id)))
    for line in old_lines:
        copied = SubscriptionLine(
            subscription_id=new.id,
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_id=line.tax_id,
        )
        db.add(copied)
        db.flush()
        for value_id in db.scalars(select(SubscriptionLineVariant.variant_value_id).where(SubscriptionLineVariant.line_id == line.id)):
            db.add(SubscriptionLineVariant(line_id=copied.id, variant_value_id=value_id))
    _history(db, new, None, "draft", actor.user_id)
    db.commit()
    db.refresh(new)
    return new


def as_detail(db: Session, subscription: Subscription) -> dict:
    return _detail(db, subscription)
