from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import CustomUser, Classroom, Student, Teacher, Subject, ExamTitle, ExamResult, Timetable, Attendance, TeacherNotification, FeedbackToAdmin
from django.contrib import messages
from django.utils import timezone
from datetime import datetime


@login_required(login_url='/')
def home(request):
    """
    Teacher dashboard view showing:
    - Teacher information
    - Classroom statistics (total students, present/absent counts)
    """
    try:
        # Get the teacher object linked to the logged-in user
        teacher = Teacher.objects.get(admin=request.user)
    except Teacher.DoesNotExist:
        return HttpResponse("Teacher details not found.", status=404)

    # Get the teacher's assigned classroom
    classroom = teacher.classroom_id

    # Calculate classroom statistics
    total_students = Student.objects.filter(classroom_id=classroom).count()
    
    # Get today's attendance data
    today = timezone.now().date()
    total_present = Attendance.objects.filter(
        student__classroom_id=classroom,
        arrival_time__date=today,
        departure_time__isnull=True  # Only count students currently in school
    ).count()
    
    total_absent = total_students - total_present  # Calculate absentees

    context = {
        'teacher': teacher,
        'total_students': total_students,
        'total_present': total_present,
        'total_absent': total_absent,
    }
    return render(request, 'teacher/home.html', context)


@login_required(login_url='/')
def view_student(request):
    """
    Display list of students in teacher's classroom with search functionality.
    """
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id

    # Get search query from request
    search_query = request.GET.get('search', '')

    # Base query - all students in teacher's classroom
    students = Student.objects.filter(classroom_id=classroom)

    # Apply name search filter if query exists
    if search_query:
        students = students.filter(
            admin__first_name__icontains=search_query
        ) | students.filter(
            admin__last_name__icontains=search_query
        )

        # Show warning if no results found
        if search_query and not students.exists():
            messages.warning(request, f'No students found: {search_query}')

    context = {
        'teacher': teacher,
        'classroom': classroom,
        'students': students,
        'search_query': search_query,
    }
    return render(request, 'teacher/view_student.html', context)


@login_required(login_url='/')
def add_student(request):
    """
    Handle new student creation for teacher's classroom.
    Includes validation for unique email/username.
    """
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id 

    if request.method == "POST":
        # Extract all form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Validate unique email
        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect('teacher_add_student')
        
        # Validate unique username
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect('teacher_add_student') 
        
        # Create new user and student record
        user = CustomUser(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            profile_pic=profile_pic,
            user_type=3  # Student type
        )
        user.set_password(password)
        user.save()

        student = Student(
            admin=user,
            gender=gender,
            classroom_id=classroom,
        )
        student.save()
        messages.success(request, f'{user.first_name} {user.last_name} Successfully Added!')
        return redirect('teacher_view_student')

    context = {
        'classroom': classroom,
    }
    return render(request, 'teacher/add_student.html', context)


@login_required(login_url='/')
def edit_student(request, id):
    """
    Display student edit form.
    Ensures teacher can only edit students in their classroom.
    """
    teacher = Teacher.objects.get(admin=request.user)
    student = get_object_or_404(Student, id=id, classroom_id=teacher.classroom_id)

    context = {
        'student': student,
    }
    return render(request, 'teacher/edit_student.html', context)


@login_required(login_url='/')
def update_student(request):
    """
    Handle student record updates.
    Supports partial updates (password/profile pic optional).
    """
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id, classroom_id=request.user.teacher.classroom_id)

        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Update user record
        user = student.admin
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        if password:
            user.set_password(password)
        if profile_pic:
            user.profile_pic = profile_pic
        user.save()

        # Update student record
        student.gender = gender
        classroom = Classroom.objects.get(id=classroom_id)
        student.classroom_id = classroom
        student.save()

        messages.success(request, f'{user.first_name} {user.last_name}\'s record updated!')
        return redirect('teacher_view_student')

    return redirect('teacher_view_student')


@login_required(login_url='/')
def delete_student(request, admin):
    """
    Delete student record.
    Includes confirmation message with student name.
    """
    student = get_object_or_404(Student, admin_id=admin, classroom_id=request.user.teacher.classroom_id)
    user = student.admin

    messages.success(request, f'{user.first_name} {user.last_name}\'s record deleted!')
    user.delete()
    return redirect('teacher_view_student')


@login_required(login_url='/')
def add_exam_title(request):
    """
    Manage exam titles (types of exams).
    Shows existing titles and handles new title creation.
    """
    if request.method == "POST":
        title = request.POST.get('title')

        # Validate unique title
        if ExamTitle.objects.filter(title=title).exists():
            messages.warning(request, 'This exam title already exists.')
        else:
            ExamTitle(title=title).save()
            messages.success(request, 'Exam Title Added Successfully!')
        return redirect('add_exam_result')

    # Get all exam titles sorted by creation date (newest first)
    exam_titles = ExamTitle.objects.all().order_by('-created_at')
    context = {
        'exam_titles': exam_titles,
    }
    return render(request, 'teacher/add_exam_title.html', context)


@login_required(login_url='/')
def delete_exam_title(request, id):
    """
    Delete an exam title.
    """
    exam_title = get_object_or_404(ExamTitle, id=id)
    exam_title.delete()
    messages.success(request, 'Exam Title Deleted Successfully!')
    return redirect('add_exam_title')


@login_required(login_url='/')
def add_exam_result(request):
    """
    Add exam results for students.
    Includes validation for marks range and duplicate entries.
    """
    teacher = Teacher.objects.get(admin=request.user)
    subjects = Subject.objects.all()
    students = Student.objects.filter(classroom_id=teacher.classroom_id)
    exam_titles = ExamTitle.objects.all()

    if request.method == "POST":
        # Extract form data
        exam_title_id = request.POST.get('exam_title_id')
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        marks = float(request.POST.get('marks'))

        # Validate marks range
        if marks < 0 or marks > 100:
            messages.warning(request, 'Marks must be between 0 and 100.')
            return redirect('add_exam_result')

        # Get related objects
        student = Student.objects.get(id=student_id)
        subject = Subject.objects.get(id=subject_id)
        exam_title = ExamTitle.objects.get(id=exam_title_id)

        # Check for duplicate result entry
        if ExamResult.objects.filter(
            exam_title_id=exam_title_id,
            student_id=student_id,
            subject_id=subject_id
        ).exists():
            error_message = (
                f"{student.admin.first_name} {student.admin.last_name}'s "
                f"{subject.name} results already exist for {exam_title.title}"
            )
            messages.warning(request, error_message)
            return redirect('add_exam_result')

        # Save new exam result
        ExamResult(
            exam_title_id=exam_title_id,
            student_id=student_id,
            subject_id=subject_id,
            marks=marks,
        ).save()

        success_message = (
            f"Exam result for {student.admin.first_name} {student.admin.last_name} "
            f"in {subject.name} added successfully!"
        )
        messages.success(request, success_message)
        return redirect('view_exam_result')

    context = {
        'subjects': subjects,
        'students': students,
        'exam_titles': exam_titles,
    }
    return render(request, 'teacher/add_exam_result.html', context)


@login_required(login_url='/')
def view_exam_result(request):
    """
    View exam results with filtering by exam title and student name search.
    Results grouped by student and exam title.
    """
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id
    students = Student.objects.filter(classroom_id=classroom)
    exam_titles = ExamTitle.objects.all()

    # Get filter parameters
    search_query = request.GET.get('search', '')
    exam_title_id = request.GET.get('exam_title_id')

    # Base query - all results for teacher's students
    exam_results = ExamResult.objects.filter(student__in=students).select_related('student', 'subject', 'exam_title')

    # Apply filters
    if search_query:
        exam_results = exam_results.filter(
            student__admin__first_name__icontains=search_query
        ) | exam_results.filter(
            student__admin__last_name__icontains=search_query
        )

    if exam_title_id:
        exam_results = exam_results.filter(exam_title_id=exam_title_id)

    # Group results by student name and exam title
    grouped_results = {}
    for result in exam_results:
        student_name = f"{result.student.admin.first_name} {result.student.admin.last_name}"
        exam_title = result.exam_title.title

        if student_name not in grouped_results:
            grouped_results[student_name] = {}
        if exam_title not in grouped_results[student_name]:
            grouped_results[student_name][exam_title] = []
        grouped_results[student_name][exam_title].append(result)

    # Sort results alphabetically by student name
    grouped_results = dict(sorted(grouped_results.items()))

    context = {
        'grouped_results': grouped_results,
        'exam_titles': exam_titles,
        'selected_exam_title_id': exam_title_id,
        'search_query': search_query,
    }
    return render(request, 'teacher/view_exam_result.html', context)


@login_required(login_url='/')
def edit_exam_result(request, id):
    """
    Edit existing exam result.
    Includes marks validation.
    """
    exam_result = get_object_or_404(ExamResult, id=id)
    teacher = Teacher.objects.get(admin=request.user)
    students = Student.objects.filter(classroom_id=teacher.classroom_id)
    subjects = Subject.objects.all()

    if request.method == "POST":
        # Extract form data
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        marks = float(request.POST.get('marks'))

        # Validate marks
        if marks < 0 or marks > 100:
            messages.warning(request, 'Marks must be between 0 and 100.')
            return redirect('edit_exam_result', id=id)

        # Update exam result
        exam_result.student = Student.objects.get(id=student_id)
        exam_result.subject = Subject.objects.get(id=subject_id)
        exam_result.marks = marks
        exam_result.save()

        messages.success(request, 'Exam Result Updated Successfully!')
        return redirect('view_exam_result')

    context = {
        'exam_result': exam_result,
        'students': students,
        'subjects': subjects,
    }
    return render(request, 'teacher/edit_exam_result.html', context)


@login_required(login_url='/')
def delete_exam_result(request, id):
    """
    Delete an exam result record.
    """
    exam_result = get_object_or_404(ExamResult, id=id)
    exam_result.delete()
    messages.success(request, 'Exam Result Deleted Successfully!')
    return redirect('view_exam_result')


@login_required(login_url='/')
def teacher_view_attendance(request):
    """
    View classroom attendance with date filtering and student search.
    Defaults to showing today's attendance.
    """
    teacher = request.user.teacher
    classroom = teacher.classroom_id

    # Get filter parameters
    date_filter = request.GET.get('date', '')
    student_name = request.GET.get('student_name', '')

    # Base query - attendance for teacher's classroom
    attendance_records = Attendance.objects.filter(
        student__classroom_id=classroom
    ).order_by('-arrival_time')

    # Apply date filter
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            attendance_records = attendance_records.filter(arrival_time__date=filter_date)
        except ValueError:
            pass  # Silently handle invalid date format
    else:
        # Default to today's records
        today = timezone.localdate()
        attendance_records = attendance_records.filter(arrival_time__date=today)
        date_filter = today.isoformat()

    # Apply student name filter
    if student_name:
        attendance_records = attendance_records.filter(
            student__admin__first_name__icontains=student_name
        ) | attendance_records.filter(
            student__admin__last_name__icontains=student_name
        )

    context = {
        'attendance_records': attendance_records,
        'selected_date': date_filter,
        'classroom': classroom,
    }
    return render(request, 'teacher/teacher_view_attendance.html', context)


@login_required(login_url='/')
def add_timetable(request):
    """
    Add new timetable for teacher's classroom.
    """
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id

    if request.method == "POST":
        title = request.POST.get('title')
        timetable_image = request.FILES.get('timetable_image')

        Timetable(
            teacher=teacher,
            classroom=classroom,
            title=title,
            timetable_image=timetable_image,
        ).save()
        messages.success(request, 'Timetable added successfully!')
        return redirect('view_timetable')

    return render(request, 'teacher/add_timetable.html')


@login_required(login_url='/')
def view_timetable(request):
    """
    View all timetables created by the teacher.
    """
    teacher = Teacher.objects.get(admin=request.user)
    timetables = Timetable.objects.filter(teacher=teacher)

    context = {
        'timetables': timetables,
    }
    return render(request, 'teacher/view_timetable.html', context)


@login_required(login_url='/')
def edit_timetable(request, id):
    """
    Edit existing timetable.
    """
    timetable = get_object_or_404(Timetable, id=id, teacher__admin=request.user)

    if request.method == "POST":
        title = request.POST.get('title')
        timetable_image = request.FILES.get('timetable_image')

        timetable.title = title
        if timetable_image:
            timetable.timetable_image = timetable_image
        timetable.save()
        messages.success(request, 'Timetable updated successfully!')
        return redirect('view_timetable')

    context = {
        'timetable': timetable,
    }
    return render(request, 'teacher/edit_timetable.html', context)


@login_required(login_url='/')
def delete_timetable(request, id):
    """
    Delete a timetable.
    """
    timetable = get_object_or_404(Timetable, id=id, teacher__admin=request.user)
    timetable.delete()
    messages.success(request, 'Timetable deleted successfully!')
    return redirect('view_timetable')


@login_required(login_url='/')
def view_teacher_notifications(request):
    """
    View teacher notifications with unread count.
    """
    teacher = Teacher.objects.get(admin=request.user)
    notifications = TeacherNotification.objects.filter(teacher=teacher).order_by('-created_at')
    
    # Calculate unread notifications count
    unread_count = TeacherNotification.objects.filter(teacher=teacher, read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'teacher/view_teacher_notifications.html', context)


@login_required(login_url='/')
def mark_notification_as_read(request, notification_id):
    """
    Mark a notification as read.
    """
    notification = get_object_or_404(TeacherNotification, id=notification_id)
    notification.read = True
    notification.save()
    return redirect('view_teacher_notifications')


@login_required
def send_teacher_feedback(request):
    """
    Handle teacher feedback submission to admin.
    Supports text and file attachments.
    """
    if request.method == 'POST':
        FeedbackToAdmin.objects.create(
            sender=request.user,
            sender_type='teacher',
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            attachment=request.FILES.get('attachment')
        )
        messages.success(request, 'Feedback sent to admin!')
        return redirect('send_teacher_feedback')
    
    return render(request, 'teacher/send_feedback.html')