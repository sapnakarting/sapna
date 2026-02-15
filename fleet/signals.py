from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, DailyOdoRegistry


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        # Only create if profile doesn't already exist
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'FUEL_AGENT'}
        )


@receiver(post_save, sender=DailyOdoRegistry)
def update_truck_odometer(sender, instance, created, **kwargs):
    """Update truck's current odometer when a daily odometer entry is saved."""
    if instance.closing_odometer is not None:
        truck = instance.truck
        # Only update if the new closing odometer is greater than current
        # This prevents overwriting with older data
        if truck.current_odometer <= instance.closing_odometer:
            truck.current_odometer = instance.closing_odometer
            truck.save(update_fields=['current_odometer'])
