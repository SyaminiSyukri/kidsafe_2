from .models import TeacherNotification, CanteenNotification, StudentNotification, FeedbackToAdmin

def notification_count(request):
    if not request.user.is_authenticated:
        return {'unread_count': 0}
    
    unread_count = 0
    
    if request.user.user_type == '2':  # Teacher
        unread_count = TeacherNotification.objects.filter(
            teacher__admin=request.user, 
            read=False
        ).count()
    elif request.user.user_type == '3':  # Student
        unread_count = StudentNotification.objects.filter(
            student__admin=request.user, 
            read=False
        ).count()
    elif request.user.user_type == '4':  # Canteen
        unread_count = CanteenNotification.objects.filter(
            canteen__admin=request.user, 
            read=False
        ).count()
    
    return {'unread_count': unread_count}

# context_processors.py
def feedback_counts(request):
    if not request.user.is_authenticated:
        return {}
    
    counts = {}
    
    if request.user.user_type == '1':  # Admin
        counts.update({
            'teacher_feedback_unread': FeedbackToAdmin.objects.filter(
                sender_type='teacher', 
                is_read=False
            ).count(),
            'student_feedback_unread': FeedbackToAdmin.objects.filter(
                sender_type='student', 
                is_read=False
            ).count(),
            'canteen_feedback_unread': FeedbackToAdmin.objects.filter(
                sender_type='canteen', 
                is_read=False
            ).count(),
            'total_feedback_unread': FeedbackToAdmin.objects.filter(
                is_read=False
            ).count(),
        })
    else:  # Non-admin users
        # Using sender_id since recipient field doesn't exist
        counts['total_feedback_unread'] = FeedbackToAdmin.objects.filter(
            sender_id=request.user.id,
            is_read=False
        ).count()
    
    return counts