from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import Student, Teacher, Dietary, ExamTitle, ExamResult, Timetable, Attendance, StudentAccount, StudentNotification, FeedbackToAdmin
from django.contrib import messages
from django.utils import timezone
from datetime import datetime

@login_required(login_url='/')
def home(request):

    try:
        student = Student.objects.get(admin=request.user)  # Get the student object linked to the logged-in user
        teacher = Teacher.objects.filter(classroom_id=student.classroom_id).first()  # Get the teacher for the student's classroom
    except Student.DoesNotExist:
        # If the student doesn't exist, redirect or show an error
        return HttpResponse("Student details not found.", status=404)
    
    try:
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


@login_required(login_url='/')
def dietary_details(request):
    student = get_object_or_404(Student, admin=request.user)
    
    # Get or create the dietary details for the student
    dietary_detail, created = Dietary.objects.get_or_create(student=student)

    if request.method == "POST":
        food_allergy = request.POST.get('food_allergy')
        dietary_restriction = request.POST.get('dietary_restriction')

        # Append new food allergy to the existing list
        if food_allergy:
            if dietary_detail.food_allergy:
                dietary_detail.food_allergy += f", {food_allergy}"  # Append to existing allergies
            else:
                dietary_detail.food_allergy = food_allergy  # Add the first allergy
            messages.success(request, 'Food allergy added successfully!')

        # Append new dietary restriction to the existing list
        if dietary_restriction:
            if dietary_detail.dietary_restriction:
                dietary_detail.dietary_restriction += f", {dietary_restriction}"  # Append to existing restrictions
            else:
                dietary_detail.dietary_restriction = dietary_restriction  # Add the first restriction
            messages.success(request, 'Dietary restriction added successfully!')

        dietary_detail.save()
        return redirect('dietary_details')  # Redirect to the same page to see the updated list

    # Split the comma-separated strings into lists for the template
    food_allergies = dietary_detail.food_allergy.split(', ') if dietary_detail.food_allergy else []
    dietary_restrictions = dietary_detail.dietary_restriction.split(', ') if dietary_detail.dietary_restriction else []

    context = {
        'dietary_detail': dietary_detail,  # Pass the single dietary detail to the template
        'food_allergies': food_allergies,  # Pass the list of food allergies
        'dietary_restrictions': dietary_restrictions,  # Pass the list of dietary restrictions
    }
    return render(request, 'student/dietary_details.html', context)


@login_required(login_url='/')
def delete_dietary_detail(request, item_type, item):
    student = get_object_or_404(Student, admin=request.user)
    dietary_detail = get_object_or_404(Dietary, student=student)

    if item_type == 'food_allergy':
        # Remove the specific food allergy from the list
        allergies = dietary_detail.food_allergy.split(', ')
        allergies.remove(item)
        dietary_detail.food_allergy = ', '.join(allergies)
        messages.success(request, 'Food allergy deleted successfully!')
    elif item_type == 'dietary_restriction':
        # Remove the specific dietary restriction from the list
        restrictions = dietary_detail.dietary_restriction.split(', ')
        restrictions.remove(item)
        dietary_detail.dietary_restriction = ', '.join(restrictions)
        messages.success(request, 'Dietary restriction deleted successfully!')

    dietary_detail.save()
    return redirect('dietary_details')

@login_required(login_url='/')
def academic_results(request):
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
    student = get_object_or_404(Student, admin=request.user)
    classroom = student.classroom_id
    timetables = Timetable.objects.filter(classroom=classroom)

    context = {
        'timetables': timetables,
    }
    return render(request, 'student/view_timetable.html', context)


@login_required(login_url='/')
def student_attendance(request):
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


# student_views.py
@login_required(login_url='/')
def view_student_notifications(request):
    notifications = StudentNotification.objects.filter(
        student__admin=request.user
    ).order_by('-created_at')
    
    return render(request, 'student/view_student_notifications.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(read=False).count()
    })

@login_required(login_url='/')
def mark_notification_as_read(request, notification_id):
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