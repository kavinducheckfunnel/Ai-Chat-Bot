from celery import shared_task


@shared_task
def reset_monthly_sessions():
    """Reset sessions_this_month counter for all tenants on the 1st of each month."""
    from users.models import TenantProfile
    TenantProfile.objects.all().update(sessions_this_month=0)
