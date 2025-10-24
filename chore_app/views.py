import datetime
import logging

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages as django_messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

import chore_app.forms as forms
import chore_app.models as models
from chore_app.cron import nightly_action, has_run_today
from chore_app.constants import (
    POINTS_TO_MONEY_CONVERSION_RATE, POINT_VALUE_MULTIPLIER, EARLY_BONUS_START_HOUR,
    POINT_LOGS_PER_PAGE, CHILD_POINT_LOGS_PER_PAGE, MAX_PENALTY_PERCENTAGE,
    REJECTION_PENALTY, ALWAYS_AVAILABLE_TIME
)
from chore_app.utils import safe_get_object_or_404

UserModel = get_user_model()

# Set up logging
logger = logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = UserModel
        fields = ('username', 'email', 'role', 'points_balance')


def register(request):
    """
    Handle user registration.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered registration page or redirect to login on success
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    """
    Redirect user to appropriate profile based on their role.
    
    Args:
        request: HTTP request object with authenticated user
        
    Returns:
        Redirect to parent_profile or child_profile
    """
    if request.user.role == 'Parent':
        return redirect('parent_profile')
    else:
        return redirect('child_profile')


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
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        settings = safe_get_object_or_404(models.Settings, pk, "Settings not found")
        if request.method == 'POST':
            form = forms.EditSettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                return redirect('settings')
        else:
            form = forms.EditSettingsForm(instance=settings)
        return render(request, 'edit_settings.html', {'form': form, 'settings': settings})
    except (models.Settings.DoesNotExist, Exception) as e:
        logger.error(f"Error in edit_settings: {e}")
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
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        text = safe_get_object_or_404(models.Text, pk, "Text not found")
        if request.method == 'POST':
            form = forms.EditTextForm(request.POST, instance=text)
            if form.is_valid():
                form.save()
                return redirect('parent_profile')
        else:
            form = forms.EditTextForm(instance=text)
        return render(request, 'edit_text.html', {'form': form, 'text': text})
    except (models.Text.DoesNotExist, Exception) as e:
        logger.error(f"Error in edit_text: {e}")
        return redirect('parent_profile')

@login_required
def parent_profile(request):
    if request.user.role != 'Parent':
        return redirect('child_profile')

    point_logs = models.PointLog.objects.all().order_by('-date_recorded')
    paginator = Paginator(point_logs, POINT_LOGS_PER_PAGE)
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

    daily_task_can_run = not has_run_today('chore_app.cron.nightly_action')

    context = {
        'available_chores': models.Chore.objects.filter(available=True),
        'unavailable_chores': models.Chore.objects.filter(available=False),
        'claimed_chores': models.ChoreClaim.objects.filter(approved=0).select_related('chore', 'user'),
        'chore_points': chore_points,
        'point_logs': page_obj,
        'children': models.User.objects.filter(role='Child'),
        'daily_task_can_run': daily_task_can_run
    }
    response = render(request, 'parent_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
def child_profile(request):
    current_time = datetime.datetime.now().time()
    current_hour = current_time.hour

    point_logs = models.PointLog.objects.filter(
        user=request.user).order_by('-date_recorded')
    paginator = Paginator(point_logs, CHILD_POINT_LOGS_PER_PAGE)
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

    # Optimize queries to avoid N+1 problems
    chores = models.Chore.objects.filter(available=True).prefetch_related('assigned_children')
    claimed_chores = models.ChoreClaim.objects.filter(
        user=request.user).select_related('chore')
    
    # Get claimed chore names for filtering
    claimed_chore_names = list(claimed_chores.values_list('chore_name', flat=True))
    
    # Filter chores based on assignment type and user eligibility using database queries
    # Use Q objects to combine conditions instead of union
    eligible_chores_qs = chores.filter(
        Q(assignment_type__in=['any_child', 'all_children']) |
        Q(assignment_type__in=['any_selected', 'all_selected'], assigned_children=request.user)
    )
    
    # Apply time-based filtering
    # Available chores: always available OR (positive time and current time >= available_time) OR (negative time and current time <= abs(available_time))
    available_time_filter = (
        Q(available_time__exact=ALWAYS_AVAILABLE_TIME) |
        Q(available_time__gte=0, available_time__lte=current_hour) |
        Q(available_time__lt=0, available_time__lte=-current_hour)
    )
    
    # Future chores: positive time and current time < available_time
    future_time_filter = Q(available_time__gte=0, available_time__gt=current_hour)
    
    # Missed chores: negative time and current time > abs(available_time)
    # For negative available_time, missed means current_time.hour > abs(available_time)
    # This means: available_time < 0 AND current_time.hour > abs(available_time)
    # Which is equivalent to: available_time < 0 AND -available_time < current_time.hour
    # In Django Q: available_time < 0 AND -available_time < current_hour
    # Which is: available_time < 0 AND available_time > -current_hour
    missed_time_filter = Q(available_time__lt=0) & Q(available_time__gt=-current_hour)
    
    # The issue is that both available and missed conditions can be true for the same chore
    # We need to prioritize missed over available for negative time values
    # So available should exclude missed chores
    available_time_filter = available_time_filter & ~missed_time_filter
    
    filtered_chores = eligible_chores_qs.exclude(
        name__in=claimed_chore_names
    ).filter(available_time_filter)
    
    future_chores = eligible_chores_qs.exclude(
        name__in=claimed_chore_names
    ).filter(future_time_filter)
    
    missed_chores = eligible_chores_qs.exclude(
        name__in=claimed_chore_names
    ).filter(missed_time_filter)
    

    settings = {setting.key: setting.value for setting in models.Settings.objects.all()}

    context = {
        'minimum_points': settings['max_points'] / 2,
        'pocket_money': request.user.pocket_money / 100,
        'pocket_money_amount': settings['point_value'],
        'points': request.user.points_balance,
        'chores': filtered_chores,
        'chore_points': chore_points,
        'point_logs': page_obj,  # Use the paginated page_obj instead of the original queryset
        'claimed_chores': claimed_chores,
        'future_chores': future_chores,
        'missed_chores': missed_chores,
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
@require_POST
def create_chore(request):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        form = forms.ChoreForm(request.POST)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Chore created successfully!')
            return redirect('parent_profile')
    else:
        form = forms.ChoreForm()
    
    children = models.User.objects.filter(role='Child')
    return render(request, 'create_chore.html', {'form': form, 'children': children})


@login_required
def edit_chore(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        chore = models.Chore.objects.get(pk=pk)
        if request.method == 'POST':
            form = forms.EditChoreForm(request.POST, instance=chore)
            if form.is_valid():
                form.save()
                django_messages.success(request, 'Chore updated successfully!')
                return redirect('parent_profile')
        else:
            form = forms.EditChoreForm(instance=chore)
        
        children = models.User.objects.filter(role='Child')
        return render(request, 'edit_chore.html', {'form': form, 'chore': chore, 'children': children})
    except (models.Chore.DoesNotExist, Exception) as e:
        logger.error(f"Error in edit_chore: {e}")
        return redirect('parent_profile')


@login_required
@require_POST
def toggle_availability(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            chore = models.Chore.objects.get(pk=pk)
            chore.available = not chore.available
            chore.save()
            status = "available" if chore.available else "unavailable"
            django_messages.success(request, f'Chore is now {status}!')
        except (models.Chore.DoesNotExist, Exception) as e:
            logger.error(f"Error in toggle_availability: {e}")
            django_messages.error(request, 'Error updating chore availability.')
    return redirect('parent_profile')


@login_required
@require_POST
def convert_points_to_money(request, pk):
    if request.user.role != 'Child' or request.user.pk != pk:
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = models.User.objects.select_for_update().get(pk=pk)
                
                # Get required settings
                try:
                    max_points_setting = models.Settings.objects.get(key='max_points')
                    point_value_setting = models.Settings.objects.get(key='point_value')
                except models.Settings.DoesNotExist as e:
                    logger.error(f"Required setting not found: {e}")
                    django_messages.error(request, 'System configuration error. Please contact administrator.')
                    return redirect('child_profile')
                
                # Validate user has enough points
                minimum_points = max_points_setting.value / 2
                if user.points_balance < minimum_points:
                    django_messages.warning(request, f'You need at least {minimum_points} points to convert to money.')
                    return redirect('child_profile')
                
                # Validate user has enough points for conversion
                if user.points_balance < POINTS_TO_MONEY_CONVERSION_RATE:
                    django_messages.warning(request, f'You need at least {POINTS_TO_MONEY_CONVERSION_RATE} points to convert.')
                    return redirect('child_profile')
                
                # Calculate money amount
                money_amount = POINTS_TO_MONEY_CONVERSION_RATE * point_value_setting.value
                
                # Update user's balance
                user.pocket_money += money_amount
                user.points_balance -= POINTS_TO_MONEY_CONVERSION_RATE
                user.save()
                
                # Create point log entry
                models.PointLog.objects.create(
                    user=user, 
                    points_change=-POINTS_TO_MONEY_CONVERSION_RATE, 
                    penalty=0,
                    reason='Conversion to Pocket Money', 
                    chore='', 
                    approver=user
                )
                django_messages.success(request, f'Successfully converted {POINTS_TO_MONEY_CONVERSION_RATE} points to ${money_amount:.2f} pocket money!')
                
        except (models.User.DoesNotExist, Exception) as e:
            logger.error(f"Error in convert_points_to_money: {e}")
            django_messages.error(request, 'Error converting points to money.')
    
    return redirect('child_profile')


@login_required
@require_POST
def delete_chore(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            chore = models.Chore.objects.get(pk=pk)
            chore.delete()
        except (models.Chore.DoesNotExist, Exception) as e:
            logger.error(f"Error in delete_chore: {e}")
    return redirect('parent_profile')

@login_required
@require_POST
def penalise_chore(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            chore = models.Chore.objects.get(pk=pk)
            chore.available = False
            chore.save()
            for child in models.User.objects.filter(role='Child'):
                models.ChoreClaim.objects.create(
                    chore=chore, user=child, chore_name=chore.name, points=(-chore.points), approved=(-chore.points), comment='Penalty for incomplete chore'
                )
        except (models.Chore.DoesNotExist, Exception) as e:
            logger.error(f"Error in penalise_chore: {e}")
    return redirect('parent_profile')


@login_required
@require_POST
def claim_chore(request, pk):
    try:
        current_time = datetime.datetime.now().time()
        
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            chore = models.Chore.objects.select_for_update().get(pk=pk)
            
            if not chore.available:
                django_messages.warning(request, 'This chore is no longer available.')
                return redirect('child_profile')
            
            # Check if user is allowed to claim this chore based on assignment type
            can_claim = False
            if chore.assignment_type == 'any_child':
                can_claim = True
            elif chore.assignment_type == 'all_children':
                can_claim = True
            elif chore.assignment_type == 'any_selected':
                can_claim = chore.assigned_children.filter(id=request.user.id).exists()
            elif chore.assignment_type == 'all_selected':
                can_claim = chore.assigned_children.filter(id=request.user.id).exists()
            
            if not can_claim:
                django_messages.warning(request, 'You are not allowed to claim this chore.')
                return redirect('child_profile')
            
            # Check if user has already claimed this chore
            existing_claim = models.ChoreClaim.objects.filter(
                chore=chore, 
                user=request.user, 
                approved=0
            ).exists()
            
            if existing_claim:
                django_messages.warning(request, 'You have already claimed this chore.')
                return redirect('child_profile')
            
            # Calculate points and bonus
            if current_time <= datetime.time(chore.bonus_end_time) \
                    and current_time > datetime.time(EARLY_BONUS_START_HOUR) \
                    and chore.early_bonus:
                try:
                    bonus_percent = models.Settings.objects.get(key='bonus_percent').value
                    addPoints = chore.points * ((bonus_percent + 100) / 100)
                    bonus_points = addPoints - chore.points
                    comment = f'Early Bonus of {bonus_points:.0f} points: {chore.comment}'
                except models.Settings.DoesNotExist:
                    addPoints = chore.points
                    comment = chore.comment
            else:
                addPoints = chore.points
                comment = chore.comment
            
            # Create the chore claim
            models.ChoreClaim.objects.create(
                chore=chore, 
                user=request.user, 
                chore_name=chore.name, 
                points=addPoints, 
                comment=comment
            )
            
            # Determine if chore should remain available after being claimed
            if chore.assignment_type == 'any_child':
                chore.available = False
                chore.save()
            elif chore.assignment_type == 'all_children':
                # Keep available for all children
                pass
            elif chore.assignment_type in ['any_selected', 'all_selected']:
                # Check if all selected children have claimed it
                selected_children = chore.assigned_children.all()
                claimed_by_selected = models.ChoreClaim.objects.filter(
                    chore=chore, 
                    user__in=selected_children
                ).values_list('user', flat=True).distinct()
                if set(claimed_by_selected) == set(selected_children.values_list('id', flat=True)):
                    chore.available = False
                    chore.save()
            
            django_messages.success(request, f'Successfully claimed "{chore.name}"!')
            
    except (models.Chore.DoesNotExist, models.Settings.DoesNotExist, Exception) as e:
        logger.error(f"Error in claim_chore: {e}")
        django_messages.error(request, 'Error claiming chore. Please try again.')
    
    return redirect('child_profile')


@login_required
@require_POST
def return_chore(request, pk):
    try:
        choreClaim = models.ChoreClaim.objects.get(pk=pk)
        if choreClaim.approved == 0:
            if choreClaim.chore:
                try:
                    chore = models.Chore.objects.get(pk=choreClaim.chore.pk)
                    chore.available = True
                    chore.save()
                except (models.Chore.DoesNotExist, Exception) as e:
                    logger.error(f"Error in return_chore (chore lookup): {e}")
            choreClaim.delete()
    except (models.ChoreClaim.DoesNotExist, Exception) as e:
        logger.error(f"Error in return_chore: {e}")
    return redirect('child_profile')


@login_required
def approve_chore_claim(request, pk, penalty, auto=False):
    if not auto and request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST' or auto:
        try:
            with transaction.atomic():
                # Validate penalty is within acceptable range
                if penalty < 0 or penalty > 100:
                    if not auto:
                        django_messages.error(request, 'Invalid penalty percentage.')
                        return redirect('parent_profile')
                    else:
                        logger.error(f"Invalid penalty percentage: {penalty}")
                        return HttpResponse("Error: Invalid penalty")
                
                choreClaim = models.ChoreClaim.objects.select_for_update().get(pk=pk)
                
                # Check if already processed
                if choreClaim.approved != 0:
                    if not auto:
                        django_messages.warning(request, 'This chore claim has already been processed.')
                        return redirect('parent_profile')
                    else:
                        logger.warning(f"Chore claim {pk} already processed")
                        return HttpResponse("Already processed")
                
                approver = request.user if not auto else None
                # Convert penalty to Decimal to avoid type errors
                from decimal import Decimal
                penalty_decimal = Decimal(str(penalty))
                points_awarded = choreClaim.points - (choreClaim.points * (penalty_decimal / 100))
                
                # Validate points_awarded is not negative
                if points_awarded < 0:
                    points_awarded = 0
                
                # Create point log entry
                models.PointLog.objects.create(
                    user=choreClaim.user, 
                    points_change=points_awarded, 
                    penalty=penalty, 
                    reason='Approved', 
                    chore=choreClaim.chore_name, 
                    approver=approver
                )
                
                # Update user's points balance
                user = models.User.objects.select_for_update().get(pk=choreClaim.user.pk)
                user.points_balance += points_awarded
                user.save()
                
                # Update chore claim
                choreClaim.approved = points_awarded
                choreClaim.save()
                
                if not auto:
                    django_messages.success(request, f'Chore claim approved for {points_awarded} points!')
                
        except models.ChoreClaim.DoesNotExist:
            if not auto:
                django_messages.error(request, 'Chore claim not found.')
                return redirect('parent_profile')
            else:
                logger.error(f"Chore claim {pk} not found")
                return HttpResponse("Error: Chore claim not found")
        except models.User.DoesNotExist:
            if not auto:
                django_messages.error(request, 'User not found.')
                return redirect('parent_profile')
            else:
                logger.error(f"User not found for chore claim {pk}")
                return HttpResponse("Error: User not found")
        except Exception as e:
            if not auto:
                logger.error(f"Error in approve_chore_claim: {e}")
                django_messages.error(request, 'Error approving chore claim.')
                return redirect('parent_profile')
            else:
                logger.error(f"Error in approve_chore_claim (auto): {e}")
                return HttpResponse("Error: Internal error")
    
    if not auto:
        return redirect('parent_profile')
    else:
        # For auto mode, return a simple success response
        from django.http import HttpResponse
        return HttpResponse("OK")

@login_required
@require_POST
def reject_chore_claim(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            choreClaim = models.ChoreClaim.objects.get(pk=pk)
            if choreClaim.chore:
                try:
                    chore = models.Chore.objects.get(pk=choreClaim.chore.pk)
                    chore.available = True
                    chore.save()
                except (models.Chore.DoesNotExist, Exception) as e:
                    logger.error(f"Error in reject_chore_claim (chore lookup): {e}")
            models.PointLog.objects.create(user=choreClaim.user, points_change=0, penalty=REJECTION_PENALTY,
                                           reason='Rejected', chore=choreClaim.chore_name, approver=request.user)
            choreClaim.delete()
        except (models.ChoreClaim.DoesNotExist, Exception) as e:
            logger.error(f"Error in reject_chore_claim: {e}")
    return redirect('parent_profile')


@login_required
def point_adjustment(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
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
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
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
    # Check if the daily task has already been run today
    if has_run_today('chore_app.cron.nightly_action'):
        # If it has already run, redirect back to parent profile with an error message
        return redirect('parent_profile')
    
    # Only allow parents to run the daily action
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        nightly_action(approver=request.user)
    except Exception as e:
        logger.error(f"Error in daily_action: {e}")
    
    return redirect('parent_profile')
