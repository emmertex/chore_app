from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
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
    settings = get_object_or_404(models.Settings, pk=pk)
    if request.method == 'POST':
        form = forms.EditSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = forms.EditSettingsForm(instance=models.Settings.objects.get(pk=pk))
    return render(request, 'edit_settings.html', {'form': form, 'settings': models.Settings.objects.get(pk=pk)})

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
        'claimed_chores': models.ChoreClaim.objects.all().select_related('chore'),
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

    context = {
        'minimum_points': models.Settings.objects.get(key='max_points').value / 2,
        'pocket_money': request.user.pocket_money / 100,
        'pocket_money_amount': models.Settings.objects.get(key='point_value').value,
        'bonus': bonus,
        'points': request.user.points_balance,
        'chores': models.Chore.objects.filter(available=True),
        'point_logs': page_obj,  # Use the paginated page_obj instead of the original queryset
        'claimed_chores': models.ChoreClaim.objects.filter(user=request.user).select_related('chore')
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
    chore = get_object_or_404(models.Chore, pk=pk)
    if request.method == 'POST':
        form = forms.EditChoreForm(request.POST, instance=chore)
        if form.is_valid():
            form.save()
            return redirect('parent_profile')
    else:
        form = forms.EditChoreForm(instance=chore)
    return render(request, 'edit_chore.html', {'form': form, 'chore': chore})

@login_required
def toggle_availability(request, pk):
    chore = get_object_or_404(models.Chore, pk=pk)
    chore.available = not chore.available
    chore.save()
    return redirect('parent_profile')

@login_required
def convert_points_to_money(request, pk):
    user = get_object_or_404(models.User, pk=pk)
    if user.points_balance > models.Settings.objects.get(key='max_points').value / 2:
        user.pocket_money += 100 * models.Settings.objects.get(key='point_value').value
        user.points_balance -= 100
        user.save()
        models.PointLog.objects.create(user=user, points_change=-100, penalty=0, reason='Conversion to Pocket Money', chore='Payout', approver=user)
    return redirect('child_profile')

@login_required
def delete_chore(request, pk):
    chore = get_object_or_404(models.Chore, pk=pk)
    chore.delete()
    return redirect('parent_profile')

@login_required
def claim_chore(request, pk):
    current_time = datetime.datetime.now().time()
    chore = get_object_or_404(models.Chore, pk=pk)
    if chore.available:
        if current_time <= datetime.time(models.Settings.objects.get(key='bonus_end_time').value) and current_time > datetime.time(5):
            addPoints = chore.points * ((models.Settings.objects.get(key='bonus_percent').value + 100) / 100)
            comment = 'Early Bonus'
        else:
            addPoints = chore.points
            comment = ''
        models.ChoreClaim.objects.create(chore=chore, user=request.user, choreName=chore.name, points=addPoints, comment=comment)
        if not chore.persistent:
            chore.available = False
            chore.save()
    return redirect('child_profile')

@login_required
def return_chore(request, pk):
    choreClaim = get_object_or_404(models.ChoreClaim, pk=pk)
    try:
        chore = get_object_or_404(models.Chore, pk=choreClaim.chore.pk)
        chore.available = True
        chore.save()
    except:
        pass
    choreClaim.delete()
    return redirect('child_profile')

@login_required
def approve_chore_claim(request, pk, penalty):
    choreClaim = get_object_or_404(models.ChoreClaim, pk=pk)
    models.PointLog.objects.create(user=choreClaim.user, points_change=(choreClaim.points - (choreClaim.points * (penalty / 100))), penalty=penalty, reason='Approved', chore=choreClaim.choreName, approver=request.user)
    user = get_object_or_404(models.User, pk=choreClaim.user.pk)
    user.points_balance += (choreClaim.points - (choreClaim.points * (penalty / 100)))
    user.save()
    choreClaim.delete()
    return redirect('parent_profile')

@login_required
def reject_chore_claim(request, pk):
    choreClaim = get_object_or_404(models.ChoreClaim, pk=pk)
    try:
        chore = get_object_or_404(models.Chore, pk=choreClaim.chore.pk)
        chore.available = True
        chore.save()
    except:
        pass
    models.PointLog.objects.create(user=choreClaim.user, points_change=0, penalty=100, reason='Rejected', chore=choreClaim.choreName, approver=request.user)
    choreClaim.delete()
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
    children = models.User.objects.filter(role='Child')
    for child in children:
        # Incomplete Chore Penalty
        available_chores = models.Chore.objects.filter(available=True, persistent=False)
        if available_chores:
            incomplete_chores = 0
            for chores in available_chores:
                incomplete_chores -= chores.points / 2
            models.PointLog.objects.create(user=child, points_change=incomplete_chores, penalty=50, reason='Incomplete Chores Penalty', chore='Daily Summary', approver=request.user)
        
        # Daily Bonus
        points_balance = child.points_balance + incomplete_chores
        old_points_balance = points_balance
        pocket_money = child.pocket_money
        points_balance += models.Settings.objects.get(key='daily_bonus').value
        if points_balance > models.Settings.objects.get(key='max_points').value:
            pocket_money += (points_balance - models.Settings.objects.get(key='max_points').value) * models.Settings.objects.get(key='point_value').value
            points_balance = models.Settings.objects.get(key='max_points').value
        if points_balance < models.Settings.objects.get(key='min_points').value:
            points_balance = models.Settings.objects.get(key='min_points').value
        models.User.objects.filter(pk=child.pk).update(points_balance=points_balance, pocket_money=pocket_money)
        
        models.PointLog.objects.create(user=child, points_change=points_balance-old_points_balance, penalty=0, reason='Daily Points', chore='Daily Points', approver=request.user) 
    
    # Reset all chores
    chores = models.Chore.objects.filter(daily=True)
    for chore in chores:
        chore.available = True
        chore.save()
    return redirect('parent_profile')

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
