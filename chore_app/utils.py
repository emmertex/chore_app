"""
Utility functions for the chore application.
"""

import logging
from django.http import Http404
from django.shortcuts import redirect

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

