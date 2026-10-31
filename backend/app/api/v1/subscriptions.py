from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_current_actor, get_db
from app.schemas.subscriptions import (
    SubscriptionCreateIn, SubscriptionDetailOut, SubscriptionListOut,
    SubscriptionRenewalOut, SubscriptionTransitionIn, SubscriptionFromTemplateIn, SubscriptionUpdateIn,
)
from app.services import subscriptions as service

router = APIRouter(tags=["subscriptions"])
DbSession = Annotated[Session, Depends(get_db)]
AnyActor = Annotated[Actor, Depends(get_current_actor)]


@router.get("/subscriptions", response_model=SubscriptionListOut)
def list_subscriptions(
    db: DbSession, actor: AnyActor,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> SubscriptionListOut:
    items, total = service.list_subscriptions(db, actor, page, page_size, status_filter)
    return SubscriptionListOut(items=service.as_detail_list(db, items), total=total, page=page, page_size=page_size)


@router.post("/subscriptions", response_model=SubscriptionDetailOut, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreateIn, db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.create_subscription(db, actor, payload))


@router.post("/subscriptions/from-template/{template_id}", response_model=SubscriptionDetailOut, status_code=status.HTTP_201_CREATED)
def create_from_template(
    template_id: Annotated[int, Path(gt=0)], payload: SubscriptionFromTemplateIn,
    db: DbSession, actor: AnyActor,
) -> SubscriptionDetailOut:
    return service.as_detail(db, service.create_from_template(db, actor, template_id, payload.customer_id, payload.start_date))


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionDetailOut)
def get_subscription(subscription_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.get_subscription(db, actor, subscription_id))


@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionDetailOut)
def update_subscription(subscription_id: Annotated[int, Path(gt=0)], payload: SubscriptionUpdateIn,
                        db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.update_subscription(db, actor, subscription_id, payload))


@router.post("/subscriptions/{subscription_id}/transition", response_model=SubscriptionDetailOut)
def transition_subscription(
    subscription_id: Annotated[int, Path(gt=0)], payload: SubscriptionTransitionIn, db: DbSession, actor: AnyActor,
) -> SubscriptionDetailOut:
    return service.as_detail(db, service.transition(db, actor, subscription_id, payload.to))


@router.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionDetailOut)
def pause_subscription(subscription_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.pause(db, actor, subscription_id))


@router.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionDetailOut)
def resume_subscription(subscription_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.resume(db, actor, subscription_id))


@router.post("/subscriptions/{subscription_id}/close", response_model=SubscriptionDetailOut)
def close_subscription(subscription_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> SubscriptionDetailOut:
    return service.as_detail(db, service.close(db, actor, subscription_id))


@router.post("/subscriptions/{subscription_id}/renew", response_model=SubscriptionRenewalOut, status_code=status.HTTP_201_CREATED)
def renew_subscription(subscription_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> SubscriptionRenewalOut:
    return SubscriptionRenewalOut(subscription=service.as_detail(db, service.renew(db, actor, subscription_id)))
