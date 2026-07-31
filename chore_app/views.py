import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages as django_messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

import chore_app.forms as forms
import chore_app.models as models
from chore_app.utils import safe_get_object_or_404
from chore_app.constants import (
    DAILY_MESSAGE_KEY, EARLY_BONUS_PERCENT, EARLY_BONUS_START_HOUR,
    POINT_LOGS_PER_PAGE, CHILD_POINT_LOGS_PER_PAGE
)

UserModel = get_user_model()

# Set up logging
logger = logging.getLogger(__name__)


def early_bonus_active(chore, now=None):
    """True if `chore`'s early bonus applies at `now` (defaults to local time)."""
    if not chore.early_bonus:
        return False
    current_hour = (now or timezone.localtime()).hour
    return EARLY_BONUS_START_HOUR <= current_hour < chore.bonus_end_time


def early_bonus_points(chore):
    """Extra points awarded for claiming `chore` early, as a Decimal."""
    return chore.points * Decimal(EARLY_BONUS_PERCENT) / Decimal(100)


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = UserModel
        fields = ('username', 'email', 'role')


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
    # Settings model removed - redirect to parent profile
    if request.user.role == 'Parent':
        return redirect('parent_profile')
    else:
        return redirect('child_profile')

@login_required
def messages(request):
    if request.user.role == 'Parent':
        # There is no "create Text" screen, so make sure the row the child
        # dashboard reads always exists and is therefore editable here.
        models.Text.objects.get_or_create(key=DAILY_MESSAGE_KEY)
        # Named 'texts', not 'messages': the latter collides with the
        # django.contrib.messages context processor.
        context = {
            'texts': models.Text.objects.all().order_by('key')
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
    
    text = safe_get_object_or_404(models.Text, pk, "Text not found")
    if request.method == 'POST':
        form = forms.EditTextForm(request.POST, instance=text)
        if form.is_valid():
            form.save()
            return redirect('messages')
    else:
        form = forms.EditTextForm(instance=text)
    return render(request, 'edit_text.html', {'form': form, 'text': text})

@login_required
def parent_profile(request):
    if request.user.role != 'Parent':
        return redirect('child_profile')

    point_logs = models.PointLog.objects.all().order_by('-date_recorded')
    paginator = Paginator(point_logs, POINT_LOGS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'available_chores': models.Chore.objects.filter(available=True),
        'unavailable_chores': models.Chore.objects.filter(available=False),
        'claimed_chores': models.ChoreClaim.objects.filter(approved=0).select_related('chore', 'user'),
        'point_logs': page_obj,
        'children': models.User.objects.filter(role='Child'),
    }
    response = render(request, 'parent_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
def child_profile(request):
    point_logs = models.PointLog.objects.filter(
        user=request.user).order_by('-date_recorded')
    paginator = Paginator(point_logs, CHILD_POINT_LOGS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Optimize queries to avoid N+1 problems
    chores = models.Chore.objects.filter(available=True).prefetch_related('assigned_children')
    claimed_chores = models.ChoreClaim.objects.filter(
        user=request.user).select_related('chore')
    
    # Get claimed chore names for filtering
    claimed_chore_names = list(claimed_chores.values_list('chore_name', flat=True))
    
    # Filter chores: show if assigned to this child, or if no children assigned (available to all).
    # distinct() is required: the OR across the assigned_children join can duplicate rows.
    filtered_chores = chores.exclude(
        name__in=claimed_chore_names
    ).filter(
        Q(assigned_children=request.user) | Q(assigned_children__isnull=True)
    ).distinct()

    claimed_chore_ids = set(claimed_chores.exclude(chore__isnull=True).values_list('chore_id', flat=True))

    # Resolve the early bonus here rather than in the template: template `{% now %}`
    # yields a string, which cannot be compared against the integer bonus_end_time.
    now = timezone.localtime()
    chore_list = list(filtered_chores)
    for chore in chore_list:
        chore.bonus_active = early_bonus_active(chore, now)
        chore.bonus_points = early_bonus_points(chore) if chore.bonus_active else None

    context = {
        'points': request.user.points_balance,
        'chores': chore_list,
        'point_logs': page_obj,
        'claimed_chores': claimed_chores,
        'claimed_chore_ids': claimed_chore_ids,
        'daily_message': models.Text.objects.filter(key=DAILY_MESSAGE_KEY).first(),
    }
    response = render(request, 'child_profile.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
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
    except models.Chore.DoesNotExist:
        django_messages.error(request, 'Chore not found.')
        return redirect('parent_profile')

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


@login_required
@require_POST
def toggle_availability(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        chore = models.Chore.objects.get(pk=pk)
        chore.available = not chore.available
        chore.save()
        status = "available" if chore.available else "unavailable"
        django_messages.success(request, f'Chore is now {status}!')
    except models.Chore.DoesNotExist:
        django_messages.error(request, 'Chore not found.')
    except Exception:
        logger.exception("Error in toggle_availability")
        django_messages.error(request, 'Error updating chore availability.')
    return redirect('parent_profile')





@login_required
@require_POST
def delete_chore(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        models.Chore.objects.get(pk=pk).delete()
        django_messages.success(request, 'Chore deleted.')
    except models.Chore.DoesNotExist:
        django_messages.error(request, 'Chore not found.')
    except Exception:
        logger.exception("Error in delete_chore")
        django_messages.error(request, 'Error deleting chore.')
    return redirect('parent_profile')




@login_required
@require_POST
def claim_chore(request, pk):
    if request.user.role != 'Child':
        return redirect('parent_profile')

    try:
        with transaction.atomic():
            chore = models.Chore.objects.select_for_update().get(pk=pk)
            
            if not chore.available:
                django_messages.warning(request, 'This chore is no longer available.')
                return redirect('child_profile')
            
            # Check eligibility: assigned children only, or any child if none assigned
            if chore.assigned_children.exists():
                if not chore.assigned_children.filter(id=request.user.id).exists():
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
            addPoints = chore.points
            comment = chore.comment
            if early_bonus_active(chore):
                bonus_points = early_bonus_points(chore)
                addPoints = chore.points + bonus_points
                comment = f'Early Bonus of {bonus_points:.0f} points: {chore.comment}'

            # Create the chore claim
            models.ChoreClaim.objects.create(
                chore=chore,
                user=request.user,
                chore_name=chore.name,
                points=addPoints,
                comment=comment
            )
            
            # Chore becomes unavailable after being claimed, unless several children
            # were assigned to it and each still owes their own claim.
            if chore.assigned_children.count() <= 1:
                chore.available = False
                chore.save()

            django_messages.success(request, f'Successfully claimed "{chore.name}"!')
            
    except models.Chore.DoesNotExist:
        django_messages.error(request, 'Chore not found.')
    except Exception:
        logger.exception("Error in claim_chore")
        django_messages.error(request, 'Error claiming chore. Please try again.')

    return redirect('child_profile')


@login_required
@require_POST
def return_chore(request, pk):
    try:
        with transaction.atomic():
            # Scope to the requesting user: a claim pk alone must not let one child
            # return another child's claim.
            choreClaim = models.ChoreClaim.objects.select_for_update().get(
                pk=pk, user=request.user)
            if choreClaim.approved == 0:
                if choreClaim.chore:
                    choreClaim.chore.available = True
                    choreClaim.chore.save()
                choreClaim.delete()
    except models.ChoreClaim.DoesNotExist:
        django_messages.error(request, 'Claimed chore not found.')
    except Exception:
        logger.exception("Error in return_chore")
        django_messages.error(request, 'Error returning chore.')
    return redirect('child_profile')


@login_required
def approve_chore_claim(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                choreClaim = models.ChoreClaim.objects.select_for_update().get(pk=pk)
                
                # Check if already processed
                if choreClaim.approved != 0:
                    django_messages.warning(request, 'This chore claim has already been processed.')
                    return redirect('parent_profile')
                
                points_awarded = choreClaim.points

                # `approved` doubles as the flag and the amount, so a zero-point
                # claim would stay pending and could be approved (and paid) twice.
                if points_awarded == 0:
                    django_messages.error(
                        request,
                        'This claim is worth 0 points. Adjust the points before approving.')
                    return redirect('parent_profile')

                # Create point log entry
                models.PointLog.objects.create(
                    user=choreClaim.user,
                    points_change=points_awarded,
                    reason='Approved',
                    chore=choreClaim.chore_name,
                    approver=request.user
                )
                
                # Update user's points balance
                user = models.User.objects.select_for_update().get(pk=choreClaim.user.pk)
                user.points_balance += points_awarded
                user.save()
                
                # Update chore claim
                choreClaim.approved = points_awarded
                choreClaim.save()
                
                # For non-daily chores, ensure they remain unavailable after completion
                if choreClaim.chore and not choreClaim.chore.daily:
                    choreClaim.chore.available = False
                    choreClaim.chore.save()
                
                django_messages.success(request, f'Chore claim approved for {points_awarded} points!')
                
        except models.ChoreClaim.DoesNotExist:
            django_messages.error(request, 'Chore claim not found.')
            return redirect('parent_profile')
        except models.User.DoesNotExist:
            django_messages.error(request, 'User not found.')
            return redirect('parent_profile')
        except Exception:
            logger.exception("Error in approve_chore_claim")
            django_messages.error(request, 'Error approving chore claim.')
            return redirect('parent_profile')
    
    return redirect('parent_profile')

@login_required
@require_POST
def reject_chore_claim(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        with transaction.atomic():
            choreClaim = models.ChoreClaim.objects.select_for_update().get(pk=pk)
            if choreClaim.approved != 0:
                django_messages.warning(request, 'This chore claim has already been processed.')
                return redirect('parent_profile')
            if choreClaim.chore:
                choreClaim.chore.available = True
                choreClaim.chore.save()
            models.PointLog.objects.create(
                user=choreClaim.user, points_change=0, reason='Rejected',
                chore=choreClaim.chore_name, approver=request.user)
            choreClaim.delete()
            django_messages.success(request, 'Chore claim rejected.')
    except models.ChoreClaim.DoesNotExist:
        django_messages.error(request, 'Chore claim not found.')
    except Exception:
        logger.exception("Error in reject_chore_claim")
        django_messages.error(request, 'Error rejecting chore claim.')
    return redirect('parent_profile')


@login_required
def point_adjustment(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')

    try:
        child = models.User.objects.get(pk=pk, role='Child')
    except models.User.DoesNotExist:
        django_messages.error(request, 'Child not found.')
        return redirect('parent_profile')

    if request.method == 'POST':
        form = forms.PointAdjustmentForm(request.POST)
        if form.is_valid():
            points_change = form.cleaned_data['points_change']
            with transaction.atomic():
                # Re-read under lock so concurrent approvals cannot clobber the balance.
                user = models.User.objects.select_for_update().get(pk=child.pk)
                point_log = form.save(commit=False)
                point_log.user = user
                point_log.approver = request.user
                point_log.chore = point_log.chore or 'Manual adjustment'
                point_log.save()

                user.points_balance += points_change
                user.save()

            logger.info(
                "Point adjustment for %s by %s: change=%s",
                user.username, request.user.username, points_change)
            django_messages.success(
                request, f'Adjusted {user.username} by {points_change} points.')
            return redirect('parent_profile')
    else:
        form = forms.PointAdjustmentForm()
    return render(request, 'point_adjustment.html', {'form': form, 'child': child})




@login_required
def child_chore(request):
    if request.user.role != 'Child':
        return redirect('parent_profile')

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


# ==================== Rewards System ====================

@login_required
def rewards_list(request):
    """
    List all available rewards.
    For parents: shows all rewards with management options.
    For children: shows only available, unredeemed rewards they can afford.
    """
    if request.user.role == 'Parent':
        rewards = models.Reward.objects.all().order_by('points_cost')
        context = {
            'rewards': rewards,
            'is_parent': True,
        }
    else:
        # Children see only available rewards they haven't already claimed
        rewards = models.Reward.objects.filter(available=True).exclude(
            Q(availability_type=models.Reward.AVAILABILITY_ONCE, redeemed_by__isnull=False)
        ).exclude(
            Q(availability_type=models.Reward.AVAILABILITY_ONCE_PER_CHILD, redeemed_by_children=request.user)
        ).order_by('points_cost').distinct()
        context = {
            'rewards': rewards,
            'is_parent': False,
            'user_points': request.user.points_balance,
        }
    response = render(request, 'rewards_list.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
def create_reward(request):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    if request.method == 'POST':
        form = forms.RewardForm(request.POST)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Reward created successfully!')
            return redirect('rewards_list')
    else:
        form = forms.RewardForm()
    
    return render(request, 'create_reward.html', {'form': form})


@login_required
def edit_reward(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        reward = models.Reward.objects.get(pk=pk)
    except models.Reward.DoesNotExist:
        django_messages.error(request, 'Reward not found.')
        return redirect('rewards_list')

    if request.method == 'POST':
        form = forms.RewardForm(request.POST, instance=reward)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Reward updated successfully!')
            return redirect('rewards_list')
    else:
        form = forms.RewardForm(instance=reward)

    return render(request, 'edit_reward.html', {'form': form, 'reward': reward})


@login_required
@require_POST
def delete_reward(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        reward = models.Reward.objects.get(pk=pk)
        reward.delete()
        django_messages.success(request, 'Reward deleted successfully!')
    except models.Reward.DoesNotExist:
        django_messages.error(request, 'Reward not found.')
    except Exception:
        logger.exception("Error in delete_reward")
        django_messages.error(request, 'Error deleting reward.')
    return redirect('rewards_list')


@login_required
@require_POST
def toggle_reward_availability(request, pk):
    if request.user.role != 'Parent':
        return redirect('child_profile')
    
    try:
        reward = models.Reward.objects.get(pk=pk)
        reward.available = not reward.available
        reward.save()
        status = "available" if reward.available else "unavailable"
        django_messages.success(request, f'Reward is now {status}!')
    except models.Reward.DoesNotExist:
        django_messages.error(request, 'Reward not found.')
    except Exception:
        logger.exception("Error in toggle_reward_availability")
        django_messages.error(request, 'Error updating reward availability.')
    return redirect('rewards_list')


@login_required
@require_POST
def claim_reward(request, pk):
    """
    Child claims a reward by spending points.
    Marks the reward as redeemed_by this user (one-time use).
    """
    if request.user.role != 'Child':
        return redirect('rewards_list')

    try:
        with transaction.atomic():
            reward = models.Reward.objects.select_for_update().get(pk=pk)
            
            # Check if reward is available
            if not reward.available:
                django_messages.warning(request, 'This reward is no longer available.')
                return redirect('rewards_list')
            
            # Check if already redeemed, based on the reward's availability type
            if reward.availability_type == models.Reward.AVAILABILITY_ONCE and reward.redeemed_by is not None:
                django_messages.warning(request, 'This reward has already been claimed.')
                return redirect('rewards_list')
            if reward.availability_type == models.Reward.AVAILABILITY_ONCE_PER_CHILD \
                    and reward.redeemed_by_children.filter(pk=request.user.pk).exists():
                django_messages.warning(request, 'You have already claimed this reward.')
                return redirect('rewards_list')

            # Check if user has enough points
            user = models.User.objects.select_for_update().get(pk=request.user.pk)
            if user.points_balance < reward.points_cost:
                django_messages.warning(
                    request,
                    f'You do not have enough points. You need {reward.points_cost:.0f} points but only have {user.points_balance:.0f}.'
                )
                return redirect('rewards_list')
            
            # Deduct points
            user.points_balance -= reward.points_cost
            user.save()
            
            # Log the point deduction
            models.PointLog.objects.create(
                user=user,
                points_change=-reward.points_cost,
                reason=f'Reward claimed: {reward.name}',
                chore=reward.name,
                approver=None  # self-service; no parent approves a reward claim
            )
            
            # Mark reward as redeemed, based on its availability type
            if reward.availability_type == models.Reward.AVAILABILITY_ONCE:
                reward.redeemed_by = user
                reward.save()
            elif reward.availability_type == models.Reward.AVAILABILITY_ONCE_PER_CHILD:
                reward.redeemed_by_children.add(user)

            django_messages.success(request, f'You have claimed "{reward.name}"! Enjoy your reward.')
    
    except models.Reward.DoesNotExist:
        django_messages.error(request, 'Reward not found.')
    except Exception:
        logger.exception("Error in claim_reward")
        django_messages.error(request, 'Error claiming reward. Please try again.')
    
    return redirect('rewards_list')


