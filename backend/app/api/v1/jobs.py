from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import Actor, get_db, require_roles
from app.jobs import tasks
from app.services import billing

router = APIRouter(prefix="/admin/jobs", tags=["jobs"])
DbSession = Annotated[Session, Depends(get_db)]
Admin = Annotated[Actor, Depends(require_roles("admin"))]


@router.get("/expired-quotations")
def get_expired_quotations(db: DbSession, actor: Admin):
    ids = tasks.expired_quotations(db)
    return {"count": len(ids), "subscription_ids": ids}


@router.get("/renewal-reminders")
def get_renewal_reminders(db: DbSession, actor: Admin):
    items = tasks.renewal_reminders(db)
    return {"count": len(items), "items": items}


@router.post("/{job_name}/run")
def run_job(job_name: str, db: DbSession, actor: Admin, as_of: date = Query(default_factory=date.today)):
    if job_name == "activate_subscriptions":
        return {"changed": tasks.activate_subscriptions(db, as_of)}
    if job_name == "auto_close_expired":
        return {"changed": tasks.auto_close_expired(db, as_of)}
    if job_name == "generate_invoices":
        result = billing.generate_due_invoices(db, as_of)
        return result.model_dump()
    if job_name == "expire_quotations":
        ids = tasks.expired_quotations(db, as_of)
        return {"count": len(ids), "subscription_ids": ids}
    if job_name == "renewal_reminders":
        items = tasks.renewal_reminders(db, as_of)
        return {"count": len(items), "items": items}
    if job_name == "daily_cfo_brief":
        tasks.run_daily_brief()
        return {"queued": True}
    raise HTTPException(status_code=404, detail="Unknown job")
