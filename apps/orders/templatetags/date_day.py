from django import template
from datetime import timedelta

register = template.Library()

@register.simple_tag
def dateaddday(a, b):
    """Soma ``b - 1`` dias a ``a``. Data ou prazo ausente devolve ``-``."""
    if a is None or b is None or b == '':
        return '-'
    try:
        end = a + timedelta(days=int(b) - 1)
    except (TypeError, ValueError):
        return '-'
    return end.strftime('%d/%m/%Y')
