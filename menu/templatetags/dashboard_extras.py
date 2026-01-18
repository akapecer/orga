from django import template
from menu.models import Menu
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.simple_tag
def get_recent_menus(limit=5):
    return Menu.objects.order_by('-data_creazione')[:limit]

@register.simple_tag
def get_recent_actions(days=7, limit=10):
    cutoff_date = timezone.now() - timedelta(days=days)
    return LogEntry.objects.filter(action_time__gte=cutoff_date).select_related('content_type', 'user')[:limit]