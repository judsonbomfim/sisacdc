from django import template
from datetime import timedelta, datetime

register = template.Library()

@register.simple_tag
def dateaddday(a, b):
    b = int(b)
    day_ = b - 1
    td = timedelta(days=day_)
    addDay = a + td
    addF = addDay.strftime('%d/%m/%Y')
    return addF