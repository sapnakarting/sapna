from datetime import timedelta


def calculate_attribution_date(date, entry_type):
    """Calculate attribution date based on fuel entry type"""
    if entry_type == "FULL_TANK":
        return date - timedelta(days=1)
    return date
