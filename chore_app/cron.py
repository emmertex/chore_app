import logging
from django_cron import CronJobBase, Schedule
from django.db.models import F, Q, Sum
import chore_app.models as models
import chore_app.views as views
from chore_app.utils import has_run_today, nightly_action
from datetime import datetime


class NightlyAction(CronJobBase):
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        )
    RUN_AT_TIMES = ['23:30']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'chore_app.cron.nightly_action'

    def mark_as_run(self):
        models.RunLog.objects.update_or_create(
            job_code=self.code, defaults={'run_date': datetime.now().date()})

    def do(self):
        if not has_run_today(self.code):
            try:
                # Get a parent user as approver for automated actions
                approver = models.User.objects.filter(role='Parent').first()
                nightly_action(approver=approver)
                logging.debug("Nightly job is running!")  # Change logging level to debug
                self.mark_as_run() 
            except Exception as e:
                logging.exception(f"Error occurred during the nightly action: {e}")
        else:
            logging.debug("Nightly job has already been run today; skipping execution.")





# Leaderboard Scoring
def apply_leaderboard_scoring(approver, children, settings):

    # Sum all the points each child earned from chores today
    chore_points = models.PointLog.objects.filter(date_recorded__date=datetime.now().date()).exclude(
        chore='').values('user', 'user__username').annotate(total_points=Sum('points_change')).order_by('-total_points')

    # Create text for the Leaderboard
    leaderboard_text = ""
    if len(chore_points) > 0:
        leaderboard_text = f"Leaderboard Results! \r\n1st Place 🏆{chore_points[0]['user__username']}🏆 - {chore_points[0]['total_points']} points (+{settings['leaderboard_awards']}) \r\n"
    if len(chore_points) > 1:
        leaderboard_text += f"2nd Place {chore_points[1]['user__username']} - {chore_points[1]['total_points']} points (+{int(settings['leaderboard_awards'] / 2)}) \r\n"
    if len(chore_points) > 2:
        leaderboard_text += f"3rd Place {chore_points[2]['user__username']} - {chore_points[2]['total_points']} points (+{int(settings['leaderboard_awards'] / 5)}) \r\n"

    # Apply the medals and points
    if len(chore_points) > 0:
        # Ensure leaderboard_awards is not zero to prevent division by zero
        leaderboard_awards = settings.get('leaderboard_awards', 0)
        if leaderboard_awards > 0:
            children.filter(pk=chore_points[0]['user']).update(
                place_1=F('place_1') + 1)
            children.filter(pk=chore_points[0]['user']).update(
                points_balance=F('points_balance') + leaderboard_awards)
            models.PointLog.objects.create(user=models.User.objects.get(
                pk=chore_points[0]['user']), points_change=leaderboard_awards, reason=leaderboard_text, chore='', approver=approver)
    if len(chore_points) > 1:
        leaderboard_awards = settings.get('leaderboard_awards', 0)
        if leaderboard_awards > 0:
            second_place_award = leaderboard_awards / 2
            children.filter(pk=chore_points[1]['user']).update(
                place_2=F('place_2') + 1)
            children.filter(pk=chore_points[1]['user']).update(
                points_balance=F('points_balance') + second_place_award)
            models.PointLog.objects.create(user=models.User.objects.get(
                pk=chore_points[1]['user']), points_change=second_place_award, reason=leaderboard_text, chore='', approver=approver)
    if len(chore_points) > 2:
        leaderboard_awards = settings.get('leaderboard_awards', 0)
        if leaderboard_awards > 0:
            third_place_award = leaderboard_awards / 5
            children.filter(pk=chore_points[2]['user']).update(
                place_3=F('place_3') + 1)
            children.filter(pk=chore_points[2]['user']).update(
                points_balance=F('points_balance') + third_place_award)
            models.PointLog.objects.create(user=models.User.objects.get(
                pk=chore_points[2]['user']), points_change=third_place_award, reason=leaderboard_text, chore='', approver=approver)
    if len(chore_points) > 3:
        for i in range(3, len(chore_points)):
            models.PointLog.objects.create(user=models.User.objects.get(
                pk=chore_points[i]['user']), points_change=0, reason=leaderboard_text, chore='', approver=approver)
    return


# Daily Bonus
def apply_daily_bonus(approver, child, settings):
    original_balance = child.points_balance
    points_balance = original_balance
    pocket_money = child.pocket_money

    if points_balance < settings['min_points']:
        points_balance = settings['min_points']
    points_balance += settings['daily_bonus']
    if points_balance > settings['max_points']:
        pocket_money += ((points_balance - settings['max_points']) * settings['point_value'])
        points_balance = settings['max_points']

    # Get the actual change in points
    points_change = points_balance - original_balance
    
    models.User.objects.filter(pk=child.pk).update(
        points_balance=points_balance, pocket_money=pocket_money)

    models.PointLog.objects.create(user=child, points_change=points_change,
                                   penalty=0, reason='Daily Points', chore='', approver=approver)
    return

# Incomplete Chores Penalty
def incomplete_chore_penalty(approver, child, settings):
    available_chores = models.Chore.objects.filter(available=True)

    if available_chores and settings['incomplete_chores_penalty'] > 0:
        # Get completed chore IDs for this child
        completed_by_child_ids = set(models.ChoreClaim.objects.filter(
            user=child, approved__gt=0
        ).values_list('chore_id', flat=True))

        # Calculate incomplete chores sum - points from available chores not completed by this child
        incomplete_chores_sum = available_chores.exclude(
            id__in=completed_by_child_ids
        ).aggregate(total=Sum('points'))['total'] or 0

        if incomplete_chores_sum == 0:
            return  # No incomplete chores, no penalty

        # Convert to Decimal to avoid type errors with Decimal fields
        from decimal import Decimal
        penalty_percentage = Decimal(str(settings['incomplete_chores_penalty']))

        # Calculate penalty amount as percentage of incomplete chores points
        penalty_amount = (penalty_percentage / 100) * incomplete_chores_sum

        # Refresh child object to get current balance (handles case where bonus was applied first)
        child.refresh_from_db()

        # Create point log entry
        models.PointLog.objects.create(
            user=child,
            points_change=-penalty_amount,
            penalty=penalty_percentage,
            reason=f'Incomplete Chores Penalty ({penalty_percentage}% of {incomplete_chores_sum} points)',
            chore='',
            approver=approver
        )

        # Update user's points balance using F() to ensure atomic operation
        models.User.objects.filter(pk=child.pk).update(points_balance=F('points_balance') - penalty_amount)

    return

# Automatically approve pending claimed chores
def auto_approve(approver, settings):
    if settings['auto_approve'] >= 0:
        unapproved_chores = models.ChoreClaim.objects.filter(approved=0).select_related('chore')
        penalty = 100 - settings['auto_approve']

        for chore_claim in unapproved_chores:
            # Call approval logic directly, bypassing view decorators
            _approve_chore_claim_direct(chore_claim.pk, penalty, approver)
    return


def _approve_chore_claim_direct(chore_claim_pk, penalty, approver):
    """
    Direct approval of chore claims for auto-approval, bypassing view decorators.
    """
    from django.db import transaction
    from decimal import Decimal

    try:
        with transaction.atomic():
            # Validate penalty is within acceptable range
            if penalty < 0 or penalty > 100:
                logging.error(f"Invalid penalty percentage: {penalty}")
                return

            chore_claim = models.ChoreClaim.objects.select_for_update().get(pk=chore_claim_pk)

            # Check if already processed
            if chore_claim.approved != 0:
                logging.warning(f"Chore claim {chore_claim_pk} already processed")
                return

            # Convert penalty to Decimal to avoid type errors
            penalty_decimal = Decimal(str(penalty))
            points_awarded = chore_claim.points - (chore_claim.points * (penalty_decimal / 100))

            # Validate points_awarded is not negative
            if points_awarded < 0:
                points_awarded = 0

            # Create point log entry
            models.PointLog.objects.create(
                user=chore_claim.user,
                points_change=points_awarded,
                penalty=penalty,
                reason='Approved',
                chore=chore_claim.chore_name,
                approver=approver
            )

            # Update user's points balance
            user = models.User.objects.select_for_update().get(pk=chore_claim.user.pk)
            user.points_balance += points_awarded
            user.save()

            # Update chore claim
            chore_claim.approved = points_awarded
            chore_claim.save()

            # For non-daily chores, ensure they remain unavailable after completion
            if chore_claim.chore and not chore_claim.chore.daily:
                chore_claim.chore.available = False
                chore_claim.chore.save()

    except models.ChoreClaim.DoesNotExist:
        logging.error(f"Chore claim {chore_claim_pk} not found")
    except models.User.DoesNotExist:
        logging.error(f"User not found for chore claim {chore_claim_pk}")
    except Exception as e:
        logging.error(f"Error in _approve_chore_claim_direct: {e}")

# Reset Daily Chores to Available, and clear claimed chores
def reset_daily_chores():
    models.ChoreClaim.objects.filter(approved__gt=0).delete()
    models.ChoreClaim.objects.filter(approved__lt=0).delete()
    models.Chore.objects.filter(daily=True).update(available=True)
    return
