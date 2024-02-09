from django import template

register = template.Library()


@register.filter(name='halve')
def halve(value):
    try:
        return str(int(value / 2))
    except (ValueError, TypeError):
        return str(int(value))

@register.filter(name='fifth')
def fifth(value):
    try:
        return str(int(value / 5))
    except (ValueError, TypeError):
        return str(int(value))

@register.filter(name='abs_filter')
def abs_filter(value):
    try:
        return str(int(abs(value)))
    except (ValueError, TypeError):
        return str(int(value))

@register.filter(name='div_ten')
def abs_filter(value):
    try:
        return str(float(value / 10))
    except (ValueError, TypeError):
        return str(int(value))
