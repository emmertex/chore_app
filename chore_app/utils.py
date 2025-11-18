"""
Utility functions for the chore application.
"""

import logging
from django.http import Http404
from django.shortcuts import redirect
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_pk(pk):
    """
    Validate that pk is a positive integer.
    
    Args:
        pk: The primary key to validate
        
    Returns:
        int: The validated pk as an integer
        
    Raises:
        Http404: If pk is not a valid positive integer
    """
    try:
        pk_int = int(pk)
        if pk_int <= 0:
            raise ValueError("PK must be positive")
        return pk_int
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid pk parameter: {pk}, error: {e}")
        raise Http404("Invalid ID provided")


def safe_get_object_or_404(model_class, pk, error_message="Object not found"):
    """
    Safely get an object by pk with proper error handling.

    Args:
        model_class: The model class to query
        pk: The primary key to look up
        error_message: Custom error message for logging

    Returns:
        The model instance

    Raises:
        Http404: If the object is not found
    """
    try:
        validated_pk = validate_pk(pk)
        return model_class.objects.get(pk=validated_pk)
    except model_class.DoesNotExist:
        logger.warning(f"{error_message}: {model_class.__name__} with pk={pk} not found")
        raise Http404(f"{error_message}")


def has_run_today(job_code):
    """
    Check if a job has already run today.

    Args:
        job_code: The job code to check

    Returns:
        bool: True if the job has run today, False otherwise
    """
    from chore_app.models import RunLog  # Import here to avoid circular imports
    last_run = RunLog.objects.filter(job_code=job_code).order_by('-run_date').first()
    if not last_run:
        return False
    current_date = datetime.now().date()
    return last_run.run_date == current_date


def nightly_action(approver=None):
    """
    Perform the nightly maintenance actions for the chore app.

    This includes:
    - Auto-approving pending chores
    - Applying penalties for incomplete chores
    - Applying daily bonuses
    - Calculating leaderboard rewards
    - Resetting daily chores

    Args:
        approver: The user performing the action (for logging)
    """
    from chore_app.models import User, Settings  # Import here to avoid circular imports
    from .cron import (  # Import functions from cron module
        auto_approve, incomplete_chore_penalty, apply_daily_bonus,
        apply_leaderboard_scoring, reset_daily_chores
    )

    try:
        children = User.objects.filter(role='Child')
        settings = {
            setting['key']: setting['value'] for setting in Settings.objects.values('key', 'value')}

        # Log initial balances
        for child in children:
            logging.info(f"Initial balance for {child.username}: points={child.points_balance}, pocket_money={child.pocket_money}")

    except Exception as e:
        logging.error(e)
        raise

    auto_approve(approver, settings)

    # Process each child's incomplete chores penalties and bonuses
    for child in children:
        try:
            incomplete_chore_penalty(approver=approver, child=child, settings=settings)
            apply_daily_bonus(approver=approver, child=child, settings=settings)
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

    # Log final balances
    children_final = User.objects.filter(role='Child')
    for child in children_final:
        logging.info(f"Final balance for {child.username}: points={child.points_balance}, pocket_money={child.pocket_money}")

