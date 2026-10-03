from .models import Notification

def notification_processor(request):
    if request.user.is_authenticated:
        # Single query: fetch up to 6 unread notifications (5 for display + 1 to detect "more")
        unread_notifications = list(
            Notification.objects.filter(recipient=request.user, is_read=False)
            .order_by('-created_at')[:6]
        )
        # If we got 6, there are more than 5 unread
        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count() if len(unread_notifications) > 5 else len(unread_notifications)
        return {
            'unread_notifications': unread_notifications[:5],
            'unread_notification_count': unread_count
        }
    return {
        'unread_notifications': [],
        'unread_notification_count': 0
    }
