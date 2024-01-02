from django import template

register = template.Library()

@register.filter()
def halve(value):
    try:
        return str(int(value / 2))
    except (ValueError, TypeError):
        return str(int(value))