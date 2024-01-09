# your_app/cron.py

from django_cron import CronJobBase, Schedule
from django.db.models import F, Q, Sum
import chore_app.models as models

class NightlyAction(CronJobBase):
    RUN_AT_TIMES = ['23:30']

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'chore_app.nightly_action'  # a unique code for your cron job class

    def do(self):
        nightly_action()
        print("Nightly job is running!")


def nightly_action(approver=None):

    try:
        children = models.User.objects.filter(role='Child')
        settings = {
            setting.key: setting.value for setting in models.Settings.objects.all()}
    except Exception as e:
        print(e)
        return
        

    # Process each child's incomplete chores penalties and bonusses
    for child in children:
        try:
            points_penalty = incomplete_chore_penalty(
                approver=approver, child=child, settings=settings)
            apply_daily_bonus(approver=approver, child=child,
                              incomplete_chores_sum=points_penalty, settings=settings)
        except Exception as e:
            print(e)
            pass

    try:
        apply_leaderboard_scoring(
            approver=approver, children=children, settings=settings)
    except Exception as e:
        print(e) 
        pass

    # Reset all chores
    try:
        reset_daily_chores()
    except Exception as e:
        print(e)
        pass

    return



# Leaderboard Scoring
def apply_leaderboard_scoring(approver, children, settings):

    # Sum all the points each child earned from chores today
    chore_points = models.PointLog.objects.filter(date_recorded__date=datetime.date.today()).exclude(
        chore='').values('user', 'user__username').annotate(total_points=Sum('points_change')).order_by('-total_points')

    # Create text for the Leaderboard
    if len(chore_points) > 0:
        leaderboard_text = "Leaderboard Results! \r\n" + \
            "1st Place 🏆" + chore_points[0]['user__username'] + "🏆 - " + str(chore_points[0]['total_points']) + \
            " points (+" + str(settings['leaderboard_awards']) + ") \r\n"
    if len(chore_points) > 1:
        leaderboard_text += "2nd Place " + chore_points[1]['user__username'] + " - " + str(chore_points[1]['total_points']) + \
            " points (+" + \
            str(int(settings['leaderboard_awards'] / 2)) + ") \r\n"
    if len(chore_points) > 2:
        leaderboard_text += "3rd Place " + chore_points[2]['user__username'] + " - " + str(chore_points[2]['total_points']) + \
            " points (+" + \
            str(int(settings['leaderboard_awards'] / 5)) + ") \r\n"

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
    points_balance = child.points_balance - incomplete_chores_sum
    old_points_balance = points_balance
    pocket_money = child.pocket_money

    if points_balance < settings['min_points']:
        points_balance = settings['min_points']
    points_balance += settings['daily_bonus']
    if points_balance > settings['max_points']:
        pocket_money += (points_balance -
                         settings['max_points'] * settings['point_value'])
        points_balance = settings['max_points']

    models.User.objects.filter(pk=child.pk).update(
        points_balance=points_balance, pocket_money=pocket_money)

    models.PointLog.objects.create(user=child, points_change=points_balance-old_points_balance,
                                   penalty=0, reason='Daily Points', chore='', approver=approver)


# Incomplete Chores Penalty
def incomplete_chore_penalty(approver, child, settings):
    available_chores = models.Chore.objects.filter(
        available=True, persistent=False)
    if available_chores and settings['incomplete_chores_penalty'] > 0:
        incomplete_chores_sum = - \
            sum(chore.points / (100 /
                settings['incomplete_chores_penalty']) for chore in available_chores)
        models.PointLog.objects.create(user=child, points_change=incomplete_chores_sum, penalty=settings['incomplete_chores_penalty'],
                                       reason='Incomplete Chores Penalty',
                                       chore='', approver=approver)
        return incomplete_chores_sum

    return 0

# Reset Daily Chores to Available, and clear claimed chores


def reset_daily_chores():
    models.ChoreClaim.objects.filter(approved__gt=0).delete()
    models.ChoreClaim.objects.filter(
        approved__lt=0).delete()       # Young kids can be weird
    models.Chore.objects.filter(daily=True).update(available=True)
