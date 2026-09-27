from django import template

from apps.diagnostics.api import share_paint

register = template.Library()


@register.filter
def score_fill(score, maximum):
    painted = share_paint(score, maximum)
    if painted is None:
        return ""
    return painted["fill"]


@register.filter
def score_percent(score, maximum):
    painted = share_paint(score, maximum)
    if painted is None:
        return ""
    return painted["percent_text"]
