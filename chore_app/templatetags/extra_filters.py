from django import template

register = template.Library()

@register.filter(name='halve')
def halve(value):
    try:
        return str(int(value / 2))
    except (ValueError, TypeError):
        return str(int(value))
    
@register.filter(name='abs_filter')
def abs_filter(value):
    try:
        return str(int(abs(value)))
    except (ValueError, TypeError):
        return str(int(value))