from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import Student, Teacher, Dietary, ExamTitle, ExamResult, Timetable, Attendance, StudentAccount, StudentNotification, FeedbackToAdmin, Transaction
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
        # Get the teacher for the student's classroom 
        teacher = Teacher.objects.filter(classroom_id=student.classroom_id).first() 
    except Student.DoesNotExist:
        # If the student doesn't exist, redirect or show an error
        return HttpResponse("Student details not found.", status=404)
    
    try:
        # Retrieve student's financial account information
        student_account = StudentAccount.objects.get(student=student)
        balance = student_account.balance
    except StudentAccount.DoesNotExist:
        balance = 0.00  # Default balance if no account exists

    context = {
        'student': student,
        'teacher': teacher, 
        'balance': balance,
    }
    return render(request, 'student/home.html', context)


@login_required
def dietary_details(request):
    student = get_object_or_404(Student, admin=request.user)
    dietary, created = Dietary.objects.get_or_create(student=student)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_allergy':
            allergy = request.POST.get('allergy')
            if allergy and allergy not in dietary.food_allergy:
                dietary.food_allergy.append(allergy)
                messages.success(request, 'Allergy added successfully')
        
        elif action == 'remove_allergy':
            allergy = request.POST.get('allergy')
            if allergy in dietary.food_allergy:
                dietary.food_allergy.remove(allergy)
                messages.success(request, 'Allergy removed successfully')
        
        elif action == 'add_restriction':
            restriction = request.POST.get('restriction')
            if restriction and restriction not in dietary.dietary_restriction:
                dietary.dietary_restriction.append(restriction)
                messages.success(request, 'Restriction added successfully')
        
        elif action == 'remove_restriction':
            restriction = request.POST.get('restriction')
            if restriction in dietary.dietary_restriction:
                dietary.dietary_restriction.remove(restriction)
                messages.success(request, 'Restriction removed successfully')
        
        dietary.save()
        return redirect('dietary_details')
    
    return render(request, 'student/dietary_details.html', {
        'dietary': dietary,
        'allergy_choices': Dietary.FOOD_ALLERGY_CHOICES,
        'restriction_choices': Dietary.DIETARY_RESTRICTION_CHOICES})
        

@login_required(login_url='/')
def academic_results(request):
    """
    Display student's exam results with filtering capability by exam type.
    """
    student = get_object_or_404(Student, admin=request.user)
    exam_titles = ExamTitle.objects.all()  # Fetch all exam titles
    selected_exam_title_id = request.GET.get('exam_title_id')

    # Fetch all results for the student
    results = ExamResult.objects.filter(student=student).select_related('subject', 'exam_title')

    # Filter results based on the selected exam title
    if selected_exam_title_id:
        results = results.filter(exam_title_id=selected_exam_title_id)

    # Group results by exam title
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
    # Get the logged-in student
    student = request.user.student

    # Get the date filter from the request
    date_filter = request.GET.get('date', '')

    # Fetch attendance records for the logged-in student
    attendance_records = Attendance.objects.filter(student=student).order_by('-arrival_time')

    # Apply date filter
    if date_filter:
        try:
            # Convert the date string to a datetime object
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            # Filter records by the selected date
            attendance_records = attendance_records.filter(arrival_time__date=filter_date)
        except ValueError:
            # Handle invalid date format
            pass
    else:
        # Default to today's date in the server's timezone
        today = timezone.localdate()  # Use localdate() to get the current date in the server's timezone
        attendance_records = attendance_records.filter(arrival_time__date=today)
        date_filter = today.isoformat()  # Set the default date to today

    context = {
        'attendance_records': attendance_records,
        'selected_date': date_filter,  # Pass the selected date to the template
    }
    return render(request, 'student/student_attendance.html', context)


@login_required(login_url='/')
def view_account_balance(request):
    """
    Display the student's current account balance.
    Shows $0.00 if no account record exists.
    """
    # Get the logged-in student
    student = request.user.student

    # Get the student's account balance
    try:
        student_account = StudentAccount.objects.get(student=student)
        balance = student_account.balance
    except StudentAccount.DoesNotExist:
        balance = 0.00  # Default balance if no account exists

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
        student__admin=request.user
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


@login_required
def student_transaction_history(request):
    student = request.user.student 
    selected_date = request.GET.get('date')
    
    transactions = Transaction.objects.filter(student=student).order_by('-transaction_date')
    if selected_date:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date=date_obj)
        except ValueError:
            pass

    context = {
        'transactions': transactions,
        'selected_date': selected_date,
    }
    return render(request, 'student/transaction_history.html', context)