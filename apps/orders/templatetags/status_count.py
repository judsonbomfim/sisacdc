from django import template

register = template.Library()

@register.simple_tag
def status_filter(list, status):
    ord_status_c = list.filter(order_status=status).count()
    return ord_status_c