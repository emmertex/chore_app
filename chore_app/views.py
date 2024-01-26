import datetime

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.shortcuts import redirect, render

import chore_app.forms as forms
import chore_app.models as models
from chore_app.cron import nightly_action, has_run_today

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
            form = forms.EditSettingsForm(
                instance=models.Settings.objects.get(pk=pk))
        return render(request, 'edit_settings.html', {'form': form, 'settings': models.Settings.objects.get(pk=pk)})
    except:
        return redirect('parent_profile')

@login_required
def messages(request):
    if request.user.role == 'Parent':
        context = {
            'messages': models.Text.objects.all()
        }
        response = render(request, 'messages.html', context)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    else:
        return redirect('child_profile')

@login_required
def edit_text(request, pk):
    try:
        text = models.Text.objects.get(pk=pk)
        if request.method == 'POST':
            form = forms.EditTextForm(request.POST, instance=text)
            if form.is_valid():
                form.save()
                return redirect('parent_profile')
        else:
            form = forms.EditTextForm(instance=text)
        return render(request, 'edit_text.html', {'form': form, 'text': models.Text.objects.get(pk=pk)})
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

    chore_points = models.PointLog.objects.filter(
        date_recorded__date=datetime.date.today()
    ).exclude(
        chore=''
    ).values(
        'user', 'user__username'
    ).annotate(
        total_points=Sum('points_change')
    ).order_by('-total_points')

    daily_task_ran = not has_run_today('chore_app.cron.nightly_action')

    context = {
        'available_chores': models.Chore.objects.filter(available=True),
        'unavailable_chores': models.Chore.objects.filter(available=False),
        'claimed_chores': models.ChoreClaim.objects.filter(approved=0).select_related('chore'),
        'chore_points': chore_points,
        'point_logs': page_obj,
        'children': models.User.objects.filter(role='Child'),
        'daily_task_ran': daily_task_ran
    }
    response = render(request, 'parent_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
def child_profile(request):
    current_time = datetime.datetime.now().time()
    bonus = current_time <= datetime.time(models.Settings.objects.get(
        key='bonus_end_time').value) and current_time > datetime.time(5)

    point_logs = models.PointLog.objects.filter(
        user=request.user).order_by('-date_recorded')
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
    claimed_chores = models.ChoreClaim.objects.filter(
        user=request.user).select_related('chore')
    filtered_chores = chores.exclude(
        name__in=claimed_chores.values_list('choreName', flat=True)
    ).exclude(
        (Q(availableTime__gte=0, availableTime__gt=current_time.hour) |
         Q(availableTime__lt=0, availableTime__gt=-current_time.hour)) &
        ~Q(availableTime__exact=0)
    )

    settings = {setting.key: setting.value for setting in models.Settings.objects.all()}

    context = {
        'minimum_points': models.Settings.objects.get(key='max_points').value / 2,
        'pocket_money': request.user.pocket_money / 100,
        'pocket_money_amount': models.Settings.objects.get(key='point_value').value,
        'bonus': bonus,
        'points': request.user.points_balance,
        'chores': filtered_chores,
        'chore_points': chore_points,
        'point_logs': page_obj,  # Use the paginated page_obj instead of the original queryset
        'claimed_chores': claimed_chores,
        'max_points': settings['max_points'],
        'min_points': settings['min_points'],
        'leaderboard_awards': settings['leaderboard_awards'],
        'incomplete_chores_penalty': settings['incomplete_chores_penalty'],
        'daily_message': models.Text.objects.get(key='daily_message')
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
            user.pocket_money += 100 * \
                models.Settings.objects.get(key='point_value').value
            user.points_balance -= 100
            user.save()
            models.PointLog.objects.create(user=user, points_change=-100, penalty=0,
                                           reason='Conversion to Pocket Money', chore='', approver=user)
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
                addPoints = chore.points * \
                    ((models.Settings.objects.get(key='bonus_percent').value + 100) / 100)
                comment = 'Early Bonus of ' + \
                    str(chore.earlyBonus) + ' points: ' + chore.comment
            else:
                addPoints = chore.points
                comment = chore.comment
            models.ChoreClaim.objects.create(
                chore=chore, user=request.user, choreName=chore.name, points=addPoints, comment=comment)
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
def approve_chore_claim(request, pk, penalty, auto=False):
    try:
        choreClaim = models.ChoreClaim.objects.get(pk=pk)
        models.PointLog.objects.create(user=choreClaim.user, points_change=(choreClaim.points - (choreClaim.points * (
            penalty / 100))), penalty=penalty, reason='Approved', chore=choreClaim.choreName, approver=request.user)
        user = models.User.objects.get(pk=choreClaim.user.pk)
        user.points_balance += (choreClaim.points -
                                (choreClaim.points * (penalty / 100)))
        user.save()
        choreClaim.approved = (choreClaim.points -
                               (choreClaim.points * (penalty / 100)))
        choreClaim.save()
    except:
        pass
    
    if not auto:
        return redirect('parent_profile')
    else:
        return

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
        models.PointLog.objects.create(user=choreClaim.user, points_change=0, penalty=100,
                                       reason='Rejected', chore=choreClaim.choreName, approver=request.user)
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

@login_required
def daily_action(request):
    nightly_action(approver=request.user)
    return redirect('parent_profile')
