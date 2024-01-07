from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, F, Q
import chore_app.forms as forms
import chore_app.models as models
import datetime
UserModel = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = UserModel
        fields = ('username', 'email', 'role', 'points_balance')


def register(request):
    form = CustomUserCreationForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('login')
    else:
        return render(request, 'registration/register.html', {'form': form})
    
def profile(request):
    if request.user is not None:
        if request.user.role == 'Parent':
            return redirect('parent_profile')
        else:
            return redirect('child_profile')
    else:
        return redirect('login')
    
@login_required
def settings(request):
    if request.user.role == 'Parent':
        context = {
            'settings': models.Settings.objects.all()
        }
        response = render(request, 'settings.html', context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    else:
        return redirect('child_profile')
    
@login_required
def edit_settings(request, pk):
    try:
        settings = models.Settings.objects.get(pk=pk)
        if request.method == 'POST':
            form = forms.EditSettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                return redirect('settings')
        else:
            form = forms.EditSettingsForm(instance=models.Settings.objects.get(pk=pk))
        return render(request, 'edit_settings.html', {'form': form, 'settings': models.Settings.objects.get(pk=pk)})
    except:
        return redirect('parent_profile')

@login_required
def parent_profile(request):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    point_logs = models.PointLog.objects.all().order_by('-date_recorded')
    paginator = Paginator(point_logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'available_chores': models.Chore.objects.filter(available=True),
        'unavailable_chores': models.Chore.objects.filter(available=False),
        'claimed_chores': models.ChoreClaim.objects.filter(approved=0).select_related('chore'),
        'point_logs': page_obj,
        'children': models.User.objects.filter(role='Child'),
    }
    response = render(request, 'parent_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@login_required
def child_profile(request):
    current_time = datetime.datetime.now().time()
    bonus =  current_time <= datetime.time(models.Settings.objects.get(key='bonus_end_time').value) and current_time > datetime.time(5)
    
    point_logs = models.PointLog.objects.filter(user=request.user).order_by('-date_recorded')
    paginator = Paginator(point_logs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    chore_points = models.PointLog.objects.filter(
        date_recorded__date=datetime.date.today()
    ).exclude(
        chore=''
    ).values(
        'user', 'user__username'
    ).annotate(
        total_points=Sum('points_change')
    ).order_by('-total_points')

    chores = models.Chore.objects.filter(available=True)
    claimed_chores = models.ChoreClaim.objects.filter(user=request.user).select_related('chore')
    filtered_chores = chores.exclude(
        name__in=claimed_chores.values_list('choreName', flat=True)
    ).exclude(
        (Q(availableTime__gte=0, availableTime__gt=current_time.hour) |
        Q(availableTime__lt=0, availableTime__gt=-current_time.hour)) &
        ~Q(availableTime__exact=0)
    )
    


    context = {
        'minimum_points': models.Settings.objects.get(key='max_points').value / 2,
        'pocket_money': request.user.pocket_money / 100,
        'pocket_money_amount': models.Settings.objects.get(key='point_value').value,
        'bonus': bonus,
        'points': request.user.points_balance,
        'chores': filtered_chores,
        'chore_points': chore_points,
        'point_logs': page_obj,  # Use the paginated page_obj instead of the original queryset
        'claimed_chores': claimed_chores
    }
    response = render(request, 'child_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@login_required
def create_chore(request):
    if request.method == 'POST':
        form = forms.ChoreForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('parent_profile')
    else:
        form = forms.ChoreForm()
    return render(request, 'create_chore.html', {'form': form})

@login_required
def edit_chore(request, pk):
    try:
        chore = models.Chore.objects.get(pk=pk)
        if request.method == 'POST':
            form = forms.EditChoreForm(request.POST, instance=chore)
            if form.is_valid():
                form.save()
                return redirect('parent_profile')
        else:
            form = forms.EditChoreForm(instance=chore)
        return render(request, 'edit_chore.html', {'form': form, 'chore': chore})
    except:
        return redirect('parent_profile')

@login_required
def toggle_availability(request, pk):
    try:
        chore = models.Chore.objects.get(pk=pk)
        chore.available = not chore.available
        chore.save()
    except:
        pass
    return redirect('parent_profile')

@login_required
def convert_points_to_money(request, pk):
    try:
        user = models.User.objects.get(pk=pk)
        if user.points_balance > models.Settings.objects.get(key='max_points').value / 2:
            user.pocket_money += 100 * models.Settings.objects.get(key='point_value').value
            user.points_balance -= 100
            user.save()
            models.PointLog.objects.create(user=user, points_change=-100, penalty=0, reason='Conversion to Pocket Money', chore='Payout', approver=user)
    except:
        pass
    return redirect('child_profile')

@login_required
def delete_chore(request, pk):
    try:
        chore = models.Chore.objects.get(pk=pk)
        chore.delete()
    except:
        pass
    return redirect('parent_profile')

@login_required
def claim_chore(request, pk):
    try:
        current_time = datetime.datetime.now().time()
        chore = models.Chore.objects.get(pk=pk)
        if chore.available:
            if current_time <= datetime.time(models.Settings.objects.get(key='bonus_end_time').value) \
                and current_time > datetime.time(5) \
                and chore.earlyBonus:
                addPoints = chore.points * ((models.Settings.objects.get(key='bonus_percent').value + 100) / 100)
                comment = 'Early Bonus of ' + str(chore.earlyBonus) + ' points: ' + chore.comment
            else:
                addPoints = chore.points
                comment = chore.comment
            models.ChoreClaim.objects.create(chore=chore, user=request.user, choreName=chore.name, points=addPoints, comment=comment)
            if not chore.persistent:
                chore.available = False
                chore.save()
    except:
        pass
    return redirect('child_profile')

@login_required
def return_chore(request, pk):
    try:
        choreClaim = models.ChoreClaim.objects.get(pk=pk)
        if choreClaim.approved == 0:
            try:
                chore = models.Chore.objects.get(pk=choreClaim.chore.pk)
                chore.available = True
                chore.save()
            except:
                pass
            choreClaim.delete()
    except:
        pass
    return redirect('child_profile')

@login_required
def approve_chore_claim(request, pk, penalty):
    try:
        choreClaim = models.ChoreClaim.objects.get(pk=pk)
        models.PointLog.objects.create(user=choreClaim.user, points_change=(choreClaim.points - (choreClaim.points * (penalty / 100))), penalty=penalty, reason='Approved', chore=choreClaim.choreName, approver=request.user)
        user = models.User.objects.get(pk=choreClaim.user.pk)
        user.points_balance += (choreClaim.points - (choreClaim.points * (penalty / 100)))
        user.save()
        choreClaim.approved = (choreClaim.points - (choreClaim.points * (penalty / 100)))
        choreClaim.save()
    except:
        pass
    return redirect('parent_profile')

@login_required
def reject_chore_claim(request, pk):
    try:
        choreClaim = models.ChoreClaim.objects.get(pk=pk)
        try:
            chore = models.Chore.objects.get(pk=choreClaim.chore.pk)
            chore.available = True
            chore.save()
        except:
            pass
        models.PointLog.objects.create(user=choreClaim.user, points_change=0, penalty=100, reason='Rejected', chore=choreClaim.choreName, approver=request.user)
        choreClaim.delete()
    except:
        pass
    return redirect('parent_profile')

@login_required
def point_adjustment(request, pk):
    if request.method == 'POST':
        form = forms.PointAdjustmentForm(request.POST) 
        if form.is_valid():
            user = models.User.objects.get(pk=pk)

            point_log = form.save(commit=False)
            point_log.user = user
            point_log.approver = request.user
            point_log.save()

            user.points_balance += form.cleaned_data['points_change']
            user.save()
            return redirect('parent_profile') 
    else:
        form = forms.PointAdjustmentForm()
    return render(request, 'point_adjustment.html', {'form': form})

@login_required
def pocket_money_adjustment(request, pk):
    if request.method == 'POST':
        form = forms.PocketMoneyAdjustmentForm(request.POST) 
        if form.is_valid():
            user = models.User.objects.get(pk=pk)

            user.pocket_money += form.cleaned_data['pocket_money']
            user.save()
            return redirect('parent_profile') 
    else:
        form = forms.PocketMoneyAdjustmentForm()
    return render(request, 'pocket_money_adjustment.html', {'form': form})

@login_required
def daily_action(request):
    try:
        children = models.User.objects.filter(role='Child')
        settings = {setting.key: setting.value for setting in models.Settings.objects.all()}
    except:
        return redirect('parent_profile')

    # Process each child's incomplete chores penalties and bonusses
    for child in children:
        try:
            points_penalty = incomplete_chore_penalty(approver=request.user, child=child, settings=settings)
            apply_daily_bonus(approver=request.user, child=child, incomplete_chores_sum=points_penalty, settings=settings)
        except:
            pass

    try:
        apply_leaderboard_scoring(approver=request.user, children=children, settings=settings)
    except:
        pass

    # Reset all chores
    try:
        reset_daily_chores()
    except:
        pass

    # Return to Profile
    return redirect('parent_profile')

# Leaderboard Scoring
def apply_leaderboard_scoring(approver, children, settings):

    # Sum all the points each child earned from chores today
    chore_points = models.PointLog.objects.filter(date_recorded__date=datetime.date.today()).exclude(
        chore='').values('user', 'user__username').annotate(total_points=Sum('points_change')).order_by('-total_points')
    
    # Create text for the Leaderboard
    if len (chore_points) > 0:
        leaderboard_text = "Leaderboard Results! \r\n" + \
            "1st Place 🏆" + chore_points[0]['user__username'] + "🏆 - " + str(chore_points[0]['total_points']) + \
                " points (+" + str(settings['leaderboard_awards']) + ") \r\n"
    if len (chore_points) > 1:
            leaderboard_text += "2nd Place " + chore_points[1]['user__username'] + " - " + str(chore_points[1]['total_points']) + \
                " points (+" + str(int(settings['leaderboard_awards'] / 2)) + ") \r\n"
    if len (chore_points) > 2:
            leaderboard_text += "3rd Place " + chore_points[2]['user__username'] + " - " + str(chore_points[2]['total_points']) + \
                " points (+" + str(int(settings['leaderboard_awards'] / 5)) + ") \r\n"

    # Apply the medals and points
    if len(chore_points) > 0 :
        children.filter(pk=chore_points[0]['user']).update(place_1=F('place_1') + 1)
        children.filter(pk=chore_points[0]['user']).update(points_balance= F('points_balance') + settings['leaderboard_awards'])
        models.PointLog.objects.create(user=models.User.objects.get(pk=chore_points[0]['user']), points_change=settings['leaderboard_awards'], reason=leaderboard_text, approver=approver)
    if len(chore_points) > 1 :
        children.filter(pk=chore_points[1]['user']).update(place_2=F('place_2') + 1)
        children.filter(pk=chore_points[1]['user']).update(points_balance= F('points_balance') + (settings['leaderboard_awards'] / 2))
        models.PointLog.objects.create(user=models.User.objects.get(pk=chore_points[1]['user']), points_change=settings['leaderboard_awards'] / 2, reason=leaderboard_text, approver=approver)
    if len(chore_points) > 2 :
        children.filter(pk=chore_points[2]['user']).update(place_3=F('place_3') + 1)
        children.filter(pk=chore_points[2]['user']).update(points_balance= F('points_balance') + (settings['leaderboard_awards'] / 5))
        models.PointLog.objects.create(user=models.User.objects.get(pk=chore_points[2]['user']), points_change=settings['leaderboard_awards'] / 5, reason=leaderboard_text, approver=approver)
    if len(chore_points) > 3 :
        for i in range(3, len(chore_points)):
            models.PointLog.objects.create(user=models.User.objects.get(pk=chore_points[i]['user']), points_change=0, reason=leaderboard_text, approver=approver)


# Daily Bonus
def apply_daily_bonus(approver, child, incomplete_chores_sum, settings):
    points_balance = child.points_balance - incomplete_chores_sum
    old_points_balance = points_balance
    pocket_money = child.pocket_money

    if points_balance < settings['min_points']:
        points_balance = settings['min_points']
    points_balance += settings['daily_bonus']
    if points_balance > settings['max_points']:
        pocket_money += (points_balance - settings['max_points'] * settings['point_value'])
        points_balance = settings['max_points']

    models.User.objects.filter(pk=child.pk).update(points_balance=points_balance, pocket_money=pocket_money)
    
    models.PointLog.objects.create(user=child, points_change=points_balance-old_points_balance, penalty=0, reason='Daily Points', chore='', approver=approver) 


# Incomplete Chores Penalty
def incomplete_chore_penalty(approver, child, settings):
    available_chores = models.Chore.objects.filter(available=True, persistent=False)
    if available_chores and settings['incomplete_chores_penalty'] > 0:
        incomplete_chores_sum = -sum(chore.points / (100 / settings['incomplete_chores_penalty']) for chore in available_chores)
        models.PointLog.objects.create(user=child, points_change=incomplete_chores_sum, penalty=settings['incomplete_chores_penalty'],
                                   reason='Incomplete Chores Penalty',
                                   chore='', approver=approver)
        return incomplete_chores_sum

    return 0

# Reset Daily Chores to Available, and clear claimed chores
def reset_daily_chores():
    models.ChoreClaim.objects.filter(approved__gt=0).delete()
    models.ChoreClaim.objects.filter(approved__lt=0).delete()       # Young kids can be weird
    models.Chore.objects.filter(daily=True).update(available=True)

@login_required
def child_chore(request):
    if request.method == 'POST':
        form = forms.CustomChildChore(request.POST)  
        if form.is_valid():
            chore_claim = form.save(commit=False)
            chore_claim.user = request.user
            chore_claim.save()
            return redirect('child_profile') 
    else:
        form = forms.CustomChildChore()
    return render(request, 'child_chore.html', {'form': form})
