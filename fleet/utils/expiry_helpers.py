from django.utils import timezone


def get_expiry_color_code(expiry_date):
    """Get color code based on expiry date"""
    if not expiry_date:
        return "green"
    today = timezone.now().date()
    days_until_expiry = (expiry_date - today).days

    if days_until_expiry <= 0 or days_until_expiry <= 7:
        return "red"
    if days_until_expiry <= 14:
        return "amber"
    return "green"


def get_expiry_status_text(expiry_date):
    """Get human-readable expiry status"""
    if not expiry_date:
        return "Not Set"
    today = timezone.now().date()
    days_until_expiry = (expiry_date - today).days

    if days_until_expiry <= 0:
        return f"Expired {abs(days_until_expiry)} days ago"
    if days_until_expiry == 1:
        return "Expires Tomorrow"
    return f"Expires in {days_until_expiry} days"
