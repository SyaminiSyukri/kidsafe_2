from .models import TeacherNotification

def notification_count(request):
    if request.user.is_authenticated:
        unread_count = TeacherNotification.objects.filter(teacher__admin=request.user, read=False).count()
    else:
        unread_count = 0
    return {'unread_count': unread_count}