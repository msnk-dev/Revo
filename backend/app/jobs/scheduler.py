import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs import tasks

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(tasks.activate_due, CronTrigger(hour=0, minute=5), id="activate_subscriptions", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.add_job(tasks.auto_close_due, CronTrigger(hour=0, minute=10), id="auto_close_expired", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.add_job(tasks.generate_invoices, CronTrigger(hour=1, minute=0), id="generate_invoices", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.add_job(tasks.log_expired_quotations, CronTrigger(hour=0, minute=15), id="expire_quotations", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.add_job(tasks.log_renewal_reminders, CronTrigger(hour=0, minute=20), id="renewal_reminders", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.add_job(tasks.run_daily_brief, CronTrigger(hour=8, minute=0), id="daily_cfo_brief", replace_existing=True,
                      coalesce=True, max_instances=1, misfire_grace_time=3600)
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
