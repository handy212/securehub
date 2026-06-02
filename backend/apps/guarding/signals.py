from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="alarms.AlarmEvent")
def auto_dispatch_from_alarm(sender, instance, created, **kwargs):
    if not created:
        return
    from .dispatch_bridge import create_dispatch_from_alarm

    create_dispatch_from_alarm(instance)
