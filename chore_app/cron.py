import logging
from django_cron import CronJobBase, Schedule
import chore_app.models as models
from chore_app.utils import has_run_today
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class NightlyAction(CronJobBase):
    RUN_AT_TIMES = ['23:30']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'chore_app.cron.nightly_action'

    def mark_as_run(self):
        models.RunLog.objects.update_or_create(
            job_code=self.code, defaults={'run_date': timezone.localdate()})

    def do(self):
        if not has_run_today(self.code):
            try:
                reset_daily_chores()
                self.mark_as_run()
                logger.info("Nightly job completed: daily chores reset.")
            except Exception:
                logger.exception("Error occurred during the nightly action")
        else:
            logger.debug("Nightly job has already been run today; skipping execution.")



# Reset Daily Chores to Available, and clear settled claims.
# Pending claims (approved == 0) are deliberately kept so a parent can still
# approve yesterday's work.
def reset_daily_chores():
    with transaction.atomic():
        models.ChoreClaim.objects.exclude(approved=0).delete()
        models.Chore.objects.filter(daily=True).update(available=True)
