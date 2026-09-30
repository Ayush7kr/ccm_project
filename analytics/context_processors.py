from .models import Notification

def notification_processor(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False)[:5]
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'unread_notifications': unread_notifications,
            'unread_notification_count': unread_count
        }
    return {
        'unread_notifications': [],
        'unread_notification_count': 0
    }
