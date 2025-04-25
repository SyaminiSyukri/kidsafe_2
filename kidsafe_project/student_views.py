from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import Student, Teacher, Dietary, ExamTitle, ExamResult, Timetable, Attendance, StudentAccount, StudentNotification, FeedbackToAdmin
from django.contrib import messages
from django.utils import timezone
from datetime import datetime


@login_required(login_url='/')
def home(request):
    """
    Student dashboard view showing:
    - Basic student information
    - Classroom teacher details
    - Current account balance
    """
    try:
        # Get the student object linked to the logged-in user
        student = Student.objects.get(admin=request.user)
        # Get the teacher for the student's classroom (first teacher if multiple)
        teacher = Teacher.objects.filter(classroom_id=student.classroom_id).first()
    except Student.DoesNotExist:
        # Handle case where student profile doesn't exist
        return HttpResponse("Student details not found.", status=404)
    
    try:
        # Retrieve student's financial account information
        student_account = StudentAccount.objects.get(student=student)
        balance = student_account.balance
    except StudentAccount.DoesNotExist:
        # Default balance if no account record exists
        balance = 0.00

    context = {
        'student': student,
        'teacher': teacher, 
        'balance': balance,
    }
    return render(request, 'student/home.html', context)


@login_required(login_url='/')
def dietary_details(request):
    """
    Manage student's dietary restrictions and allergies.
    Supports adding new items and displays existing ones.
    """
    student = get_object_or_404(Student, admin=request.user)
    
    # Get existing dietary details or create new record if none exists
    dietary_detail, created = Dietary.objects.get_or_create(student=student)

    if request.method == "POST":
        food_allergy = request.POST.get('food_allergy')
        dietary_restriction = request.POST.get('dietary_restriction')

        # Handle food allergy updates
        if food_allergy:
            if dietary_detail.food_allergy:
                # Append to existing comma-separated allergies
                dietary_detail.food_allergy += f", {food_allergy}"
            else:
                # First allergy entry
                dietary_detail.food_allergy = food_allergy
            messages.success(request, 'Food allergy added successfully!')

        # Handle dietary restriction updates
        if dietary_restriction:
            if dietary_detail.dietary_restriction:
                # Append to existing comma-separated restrictions
                dietary_detail.dietary_restriction += f", {dietary_restriction}"
            else:
                # First restriction entry
                dietary_detail.dietary_restriction = dietary_restriction
            messages.success(request, 'Dietary restriction added successfully!')

        dietary_detail.save()
        return redirect('dietary_details')

    # Prepare lists for template display by splitting comma-separated strings
    food_allergies = dietary_detail.food_allergy.split(', ') if dietary_detail.food_allergy else []
    dietary_restrictions = dietary_detail.dietary_restriction.split(', ') if dietary_detail.dietary_restriction else []

    context = {
        'dietary_detail': dietary_detail,
        'food_allergies': food_allergies,
        'dietary_restrictions': dietary_restrictions,
    }
    return render(request, 'student/dietary_details.html', context)


@login_required(login_url='/')
def delete_dietary_detail(request, item_type, item):
    """
    Remove specific dietary items (allergies or restrictions) from student's record.
    """
    student = get_object_or_404(Student, admin=request.user)
    dietary_detail = get_object_or_404(Dietary, student=student)

    if item_type == 'food_allergy':
        # Process food allergy removal
        allergies = dietary_detail.food_allergy.split(', ')
        allergies.remove(item)
        dietary_detail.food_allergy = ', '.join(allergies)
        messages.success(request, 'Food allergy deleted successfully!')
    elif item_type == 'dietary_restriction':
        # Process dietary restriction removal
        restrictions = dietary_detail.dietary_restriction.split(', ')
        restrictions.remove(item)
        dietary_detail.dietary_restriction = ', '.join(restrictions)
        messages.success(request, 'Dietary restriction deleted successfully!')

    dietary_detail.save()
    return redirect('dietary_details')


@login_required(login_url='/')
def academic_results(request):
    """
    Display student's exam results with filtering capability by exam type.
    """
    student = get_object_or_404(Student, admin=request.user)
    exam_titles = ExamTitle.objects.all()  # All available exam types for filter dropdown
    selected_exam_title_id = request.GET.get('exam_title_id')

    # Base query - all results for current student with related subjects and exam titles
    results = ExamResult.objects.filter(student=student).select_related('subject', 'exam_title')

    # Apply exam title filter if selected
    if selected_exam_title_id:
        results = results.filter(exam_title_id=selected_exam_title_id)

    # Organize results by exam title for grouped display
    grouped_results = {}
    for result in results:
        exam_title = result.exam_title.title
        if exam_title not in grouped_results:
            grouped_results[exam_title] = []
        grouped_results[exam_title].append(result)

    context = {
        'grouped_results': grouped_results,
        'exam_titles': exam_titles,
        'selected_exam_title_id': selected_exam_title_id,
    }
    return render(request, 'student/academic_results.html', context)


@login_required(login_url='/')
def view_timetable(request):
    """
    Display the class timetable for the student's classroom.
    """
    student = get_object_or_404(Student, admin=request.user)
    classroom = student.classroom_id
    timetables = Timetable.objects.filter(classroom=classroom)

    context = {
        'timetables': timetables,
    }
    return render(request, 'student/view_timetable.html', context)


@login_required(login_url='/')
def student_attendance(request):
    """
    Show student's attendance records with date filtering.
    Defaults to showing today's attendance if no date specified.
    """
    student = request.user.student
    date_filter = request.GET.get('date', '')

    # Base query - all attendance records for student, newest first
    attendance_records = Attendance.objects.filter(student=student).order_by('-arrival_time')

    if date_filter:
        try:
            # Apply date filter if valid date provided
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            attendance_records = attendance_records.filter(arrival_time__date=filter_date)
        except ValueError:
            # Silently handle invalid date format
            pass
    else:
        # Default to today's records if no date specified
        today = timezone.localdate()
        attendance_records = attendance_records.filter(arrival_time__date=today)
        date_filter = today.isoformat()

    context = {
        'attendance_records': attendance_records,
        'selected_date': date_filter,
    }
    return render(request, 'student/student_attendance.html', context)


@login_required(login_url='/')
def view_account_balance(request):
    """
    Display the student's current account balance.
    Shows $0.00 if no account record exists.
    """
    student = request.user.student

    try:
        student_account = StudentAccount.objects.get(student=student)
        balance = student_account.balance
    except StudentAccount.DoesNotExist:
        balance = 0.00

    context = {
        'balance': balance,
    }
    return render(request, 'student/view_account_balance.html', context)


@login_required(login_url='/')
def view_student_notifications(request):
    """
    Display all notifications for the student, sorted newest first.
    Includes count of unread notifications.
    """
    notifications = StudentNotification.objects.filter(
        student__admin=request.user
    ).order_by('-created_at')
    
    return render(request, 'student/view_student_notifications.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(read=False).count()
    })


@login_required(login_url='/')
def mark_notification_as_read(request, notification_id):
    """
    Mark a specific notification as read.
    Ensures student can only mark their own notifications.
    """
    notification = get_object_or_404(
        StudentNotification, 
        id=notification_id,
        student__admin=request.user  # Security check - only own notifications
    )
    notification.read = True
    notification.save()
    return redirect('view_student_notifications')


@login_required
def send_student_feedback(request):
    """
    Handle submission of feedback from student to admin.
    Supports text messages and optional file attachments.
    """
    if request.method == 'POST':
        FeedbackToAdmin.objects.create(
            sender=request.user,
            sender_type='student',
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            attachment=request.FILES.get('attachment')
        )
        messages.success(request, 'Feedback sent to admin!')
        return redirect('send_student_feedback')
    
    return render(request, 'student/send_feedback.html')