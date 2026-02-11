from datetime import datetime

from django.utils import timezone


def get_today_date():
    """Get today's date in local timezone"""
    return timezone.now().date()


def format_date(date_obj, format_str="%d-%m-%Y"):
    """Format date object to string"""
    if not date_obj:
        return ""
    return date_obj.strftime(format_str)


def parse_date(date_str, format_str="%d-%m-%Y"):
    """Parse date string to date object"""
    if not date_str:
        return None
    return datetime.strptime(date_str, format_str).date()
