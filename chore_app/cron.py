import logging
from django_cron import CronJobBase, Schedule
from django.db.models import F, Q, Sum
import chore_app.models as models
import chore_app.views as views
import datetime

class NightlyAction(CronJobBase):
    # Scheduled to run nightly at 11:30 PM
    RUN_AT_TIMES = ['23:30']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'chore_app.cron.nightly_action' 

    def do(self):
        try:
            # Execute the nightly action task
            nightly_action()
            logging.info("Nightly job is running!")
        except Exception as e:
            # Log any exceptions that occur
            logging.exception(f"Error occurred during the nightly action: {e}")


def nightly_action(approver=None):

    try:
        children = models.User.objects.filter(role='Child')
        settings = {
            setting['key']: setting['value'] for setting in models.Settings.objects.values('key', 'value')}
    except Exception as e:
        logging.error(e)
        raise

    auto_approve(approver, settings)

    # Process each child's incomplete chores penalties and bonusses
    for child in children:
        try:
            points_penalty = incomplete_chore_penalty(
                approver=approver, child=child, children=children, settings=settings)
            apply_daily_bonus(approver=approver, child=child,
                              incomplete_chores_sum=points_penalty, settings=settings)
        except Exception as e:
            logging.error(e)
            raise

    try:
        apply_leaderboard_scoring(
            approver=approver, children=children, settings=settings)
    except Exception as e:
        logging.error(e) 
        raise

    # Reset all chores
    try:
        reset_daily_chores()
    except Exception as e:
        logging.error(e)
        raise

    return



# Leaderboard Scoring
def apply_leaderboard_scoring(approver, children, settings):

    # Sum all the points each child earned from chores today
    chore_points = models.PointLog.objects.filter(date_recorded__date=datetime.date.today()).exclude(
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
        children.filter(pk=chore_points[0]['user']).update(
            place_1=F('place_1') + 1)
        children.filter(pk=chore_points[0]['user']).update(
            points_balance=F('points_balance') + settings['leaderboard_awards'])
        models.PointLog.objects.create(user=models.User.objects.get(
            pk=chore_points[0]['user']), points_change=settings['leaderboard_awards'], reason=leaderboard_text, approver=approver)
    if len(chore_points) > 1:
        children.filter(pk=chore_points[1]['user']).update(
            place_2=F('place_2') + 1)
        children.filter(pk=chore_points[1]['user']).update(
            points_balance=F('points_balance') + (settings['leaderboard_awards'] / 2))
        models.PointLog.objects.create(user=models.User.objects.get(
            pk=chore_points[1]['user']), points_change=settings['leaderboard_awards'] / 2, reason=leaderboard_text, approver=approver)
    if len(chore_points) > 2:
        children.filter(pk=chore_points[2]['user']).update(
            place_3=F('place_3') + 1)
        children.filter(pk=chore_points[2]['user']).update(
            points_balance=F('points_balance') + (settings['leaderboard_awards'] / 5))
        models.PointLog.objects.create(user=models.User.objects.get(
            pk=chore_points[2]['user']), points_change=settings['leaderboard_awards'] / 5, reason=leaderboard_text, approver=approver)
    if len(chore_points) > 3:
        for i in range(3, len(chore_points)):
            models.PointLog.objects.create(user=models.User.objects.get(
                pk=chore_points[i]['user']), points_change=0, reason=leaderboard_text, approver=approver)


# Daily Bonus
def apply_daily_bonus(approver, child, incomplete_chores_sum, settings):
    child.points_balance += incomplete_chores_sum
    points_balance = child.points_balance
    pocket_money = child.pocket_money

    if points_balance < settings['min_points']:
        points_balance = settings['min_points']
    points_balance += settings['daily_bonus']
    if points_balance > settings['max_points']:
        pocket_money += ((points_balance - settings['max_points']) * settings['point_value'])
        points_balance = settings['max_points']


    models.User.objects.filter(pk=child.pk).update(
        points_balance=points_balance, pocket_money=pocket_money)

    models.PointLog.objects.create(user=child, points_change=points_balance - child.points_balance,
                                   penalty=0, reason='Daily Points', chore='', approver=approver)


# Incomplete Chores Penalty
def incomplete_chore_penalty(approver, child, children, settings):
    available_chores = models.Chore.objects.filter(available=True, persistent=False)

    if available_chores and settings['incomplete_chores_penalty'] > 0:
        complete_chores = models.ChoreClaim.objects.filter(approved__gt=0)
        completed_by_child = models.ChoreClaim.objects.filter(user=child, approved__gt=0)
        
        incomplete_chores_sum = -sum(chore.points for chore in available_chores)
        complete_chores_sum = sum(chore.points for chore in complete_chores)
        completed_by_child_sum = sum(chore.points for chore in completed_by_child)

        penalty_multiplier = settings['incomplete_chores_penalty'] / 100

        incomplete_chores_penalty = penalty_multiplier * incomplete_chores_sum * (1 - completed_by_child_sum / complete_chores_sum)

        models.PointLog.objects.create(
            user=child, 
            points_change=incomplete_chores_penalty, 
            penalty=settings['incomplete_chores_penalty'],
            reason='Incomplete Chores Penalty',
            chore='', 
            approver=approver
        )
        return incomplete_chores_penalty

    return 0

# Automatically approve pending claimed chores
def auto_approve(approver, settings):
    if settings['auto_approve'] >= 0:
        unapproved_chores = models.ChoreClaim.objects.filter(approved=0).select_related('chore')
        penalty = 100 - settings['auto_approve']
        
        for chore_claim in unapproved_chores:
            views.approve_chore_claim(None, chore_claim.pk, penalty, auto=True)

# Reset Daily Chores to Available, and clear claimed chores
def reset_daily_chores():
    models.ChoreClaim.objects.filter(approved__gt=0).delete()
    models.ChoreClaim.objects.filter(approved__lt=0).delete()
    models.Chore.objects.filter(daily=True).update(available=True)
