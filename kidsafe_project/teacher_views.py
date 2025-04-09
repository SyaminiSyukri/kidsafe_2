from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import CustomUser, Classroom, Student, Teacher, Subject, ExamTitle, ExamResult, Timetable, Attendance, TeacherNotification
from django.contrib import messages
from django.db.models import F
from django.db.models import Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import datetime


@login_required(login_url='/')
def home(request):
    # Fetch the logged-in teacher's details
    try:
        teacher = Teacher.objects.get(admin=request.user)  # Get the teacher object linked to the logged-in user
    except Teacher.DoesNotExist:
        return HttpResponse("Teacher details not found.", status=404)

    # Fetch the teacher's classroom
    classroom = teacher.classroom_id

    # Calculate total students in the classroom
    total_students = Student.objects.filter(classroom_id=classroom).count()

    # Calculate total present students (students who have scanned their attendance today)
    today = timezone.now().date()
    total_present = Attendance.objects.filter(
        student__classroom_id=classroom,
        arrival_time__date=today,
        departure_time__isnull=True  # Students who are still in school
    ).count()

    # Calculate total absent students
    total_absent = total_students - total_present

    context = {
        'teacher': teacher,  # Pass the teacher object to the template
        'total_students': total_students,
        'total_present': total_present,
        'total_absent': total_absent,
    }
    return render(request, 'teacher/home.html', context)


@login_required(login_url='/')
def view_student(request):
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id

    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Fetch students in the teacher's classroom
    students = Student.objects.filter(classroom_id=classroom)

    # Apply search filter (by student name)
    if search_query:
        students = students.filter(
            admin__first_name__icontains=search_query
        ) | students.filter(
            admin__last_name__icontains=search_query
        )

    # Add a warning message if no students are found
    if search_query and not students.exists():
        messages.warning(request, f'No students found: {search_query}')

    context = {
        'teacher': teacher,
        'classroom': classroom,
        'students': students,
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'teacher/view_student.html', context)


@login_required(login_url='/')
def add_student(request):
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id 

    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect('teacher_add_student')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect('teacher_add_student') 
        
        else:
            user = CustomUser(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                profile_pic=profile_pic,
                user_type=3  # Student
            )
            user.set_password(password)
            user.save()

            student = Student(
                admin=user,
                gender=gender,
                classroom_id=classroom,
            )
            student.save()
            messages.success(request, user.first_name + " " + user.last_name + ' Successfully Added!')
            return redirect('teacher_view_student')

    context = {
        'classroom': classroom,  # Pass the teacher's classroom to the template
    }

    return render(request, 'teacher/add_student.html', context)


@login_required(login_url='/')
def edit_student(request, id):
    teacher = Teacher.objects.get(admin=request.user)
    student = get_object_or_404(Student, id=id, classroom_id=teacher.classroom_id)

    context = {
        'student': student,  # Pass a single student object
    }
    return render(request, 'teacher/edit_student.html', context)


@login_required(login_url='/')
def update_student(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id, classroom_id=request.user.teacher.classroom_id)

        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

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

        student.gender = gender
        classroom = Classroom.objects.get(id=classroom_id)
        student.classroom_id = classroom
        student.save()

        # Include the student's name in the success message
        messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully updated!')
        return redirect('teacher_view_student')

    return redirect('teacher_view_student')


@login_required(login_url='/')
def delete_student(request, admin):
    student = get_object_or_404(Student, admin_id=admin, classroom_id=request.user.teacher.classroom_id)
    user = student.admin

    # Include the student's name in the delete confirmation message
    messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully deleted!')
    user.delete()
    return redirect('teacher_view_student')


@login_required(login_url='/')
def add_exam_title(request):
    if request.method == "POST":
        title = request.POST.get('title')  # Get the exam title from the form

        # Check if the title already exists
        if ExamTitle.objects.filter(title=title).exists():
            messages.warning(request, 'This exam title already exists.')
        else:
            # Save the new exam title
            exam_title = ExamTitle(title=title)
            exam_title.save()
            messages.success(request, 'Exam Title Added Successfully!')
        return redirect('add_exam_result')

    # Fetch all exam titles for display
    exam_titles = ExamTitle.objects.all().order_by('-created_at')
    context = {
        'exam_titles': exam_titles,
    }
    return render(request, 'teacher/add_exam_title.html', context)


@login_required(login_url='/')
def delete_exam_title(request, id):
    exam_title = get_object_or_404(ExamTitle, id=id)
    exam_title.delete()
    messages.success(request, 'Exam Title Deleted Successfully!')
    return redirect('add_exam_title')


@login_required(login_url='/')
def add_exam_result(request):
    teacher = Teacher.objects.get(admin=request.user)
    subjects = Subject.objects.all()  # Fetch all subjects
    students = Student.objects.filter(classroom_id=teacher.classroom_id)  # Get students in the teacher's classroom
    exam_titles = ExamTitle.objects.all()  # Fetch all exam titles

    if request.method == "POST":
        exam_title_id = request.POST.get('exam_title_id')  # Get the selected exam title ID
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        marks = float(request.POST.get('marks'))  # Convert marks to float

        # Validate marks
        if marks < 0 or marks > 100:
            messages.warning(request, 'Marks must be between 0 and 100.')
            return redirect('add_exam_result')

        # Fetch the student, subject, and exam title objects
        student = Student.objects.get(id=student_id)
        subject = Subject.objects.get(id=subject_id)
        exam_title = ExamTitle.objects.get(id=exam_title_id)

        # Check if the student has already taken this subject for the selected exam title
        if ExamResult.objects.filter(
            exam_title_id=exam_title_id,
            student_id=student_id,
            subject_id=subject_id
        ).exists():
            # Create a descriptive error message
            error_message = (
                f"{student.admin.first_name} {student.admin.last_name}'s {subject.name} results have been taken for {exam_title.title}"
            )
            messages.warning(request, error_message)
            return redirect('add_exam_result')

        # Save the exam result
        exam_result = ExamResult(
            exam_title_id=exam_title_id,
            student_id=student_id,
            subject_id=subject_id,
            marks=marks,
        )
        exam_result.save()

        # Create a descriptive success message
        success_message = (
            f"Exam result for {student.admin.first_name} {student.admin.last_name} "
            f"in {subject.name} has been added successfully!"
        )
        messages.success(request, success_message)
        return redirect('view_exam_result')

    context = {
        'subjects': subjects,  # Pass all subjects to the template
        'students': students,
        'exam_titles': exam_titles,  # Pass all exam titles to the template
    }
    return render(request, 'teacher/add_exam_result.html', context)


@login_required(login_url='/')
def view_exam_result(request):
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id
    students = Student.objects.filter(classroom_id=classroom)
    exam_titles = ExamTitle.objects.all()

    search_query = request.GET.get('search', '')
    exam_title_id = request.GET.get('exam_title_id')

    # Fetch exam results for the teacher's classroom
    exam_results = ExamResult.objects.filter(student__in=students).select_related('student', 'subject', 'exam_title')

    # Apply search filter (by student name)
    if search_query:
        exam_results = exam_results.filter(
            student__admin__first_name__icontains=search_query
        ) | exam_results.filter(
            student__admin__last_name__icontains=search_query
        )

    # Apply exam title filter
    if exam_title_id:
        exam_results = exam_results.filter(exam_title_id=exam_title_id)

    # Group results by student name and then by exam title
    grouped_results = {}
    for result in exam_results:
        student_name = f"{result.student.admin.first_name} {result.student.admin.last_name}"
        exam_title = result.exam_title.title

        if student_name not in grouped_results:
            grouped_results[student_name] = {}
        if exam_title not in grouped_results[student_name]:
            grouped_results[student_name][exam_title] = []
        grouped_results[student_name][exam_title].append(result)

    # Sort grouped_results by student name (alphabetically)
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
    exam_result = get_object_or_404(ExamResult, id=id)
    teacher = Teacher.objects.get(admin=request.user)
    students = Student.objects.filter(classroom_id=teacher.classroom_id)  # Get students in the teacher's classroom
    subjects = Subject.objects.all()  # Fetch all subjects

    if request.method == "POST":
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        marks = float(request.POST.get('marks'))  # Convert marks to float

        # Validate marks
        if marks < 0 or marks > 100:
            messages.warning(request, 'Marks must be between 0 and 100.')
            return redirect('edit_exam_result', id=id)

        student = Student.objects.get(id=student_id)
        subject = Subject.objects.get(id=subject_id)

        # Update the exam result (excluding the exam title)
        exam_result.student = student
        exam_result.subject = subject
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
    exam_result = get_object_or_404(ExamResult, id=id)
    exam_result.delete()
    messages.success(request, 'Exam Result Deleted Successfully!')
    return redirect('view_exam_result')


@login_required(login_url='/')
def teacher_view_attendance(request):
    # Get the logged-in teacher
    teacher = request.user.teacher

    # Get the teacher's classroom
    classroom = teacher.classroom_id

    # Get the date filter and student name search query from the request
    date_filter = request.GET.get('date', '')
    student_name = request.GET.get('student_name', '')

    # Fetch attendance records for students in the teacher's classroom
    attendance_records = Attendance.objects.filter(student__classroom_id=classroom).order_by('-arrival_time')

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

    # Apply student name filter (only after date filter is applied)
    if student_name:
        attendance_records = attendance_records.filter(
            student__admin__first_name__icontains=student_name
        ) | attendance_records.filter(
            student__admin__last_name__icontains=student_name
        )

    context = {
        'attendance_records': attendance_records,
        'selected_date': date_filter,  # Pass the selected date to the template
        'classroom': classroom,  # Pass the classroom to the template
    }
    return render(request, 'teacher/teacher_view_attendance.html', context)


@login_required(login_url='/')
def add_timetable(request):
    teacher = Teacher.objects.get(admin=request.user)
    classroom = teacher.classroom_id

    if request.method == "POST":
        title = request.POST.get('title')
        timetable_image = request.FILES.get('timetable_image')

        timetable = Timetable(
            teacher=teacher,
            classroom=classroom,
            title=title,
            timetable_image=timetable_image,
        )
        timetable.save()
        messages.success(request, 'Timetable added successfully!')
        return redirect('view_timetable')

    return render(request, 'teacher/add_timetable.html')


@login_required(login_url='/')
def view_timetable(request):
    teacher = Teacher.objects.get(admin=request.user)
    timetables = Timetable.objects.filter(teacher=teacher)

    context = {
        'timetables': timetables,
    }
    return render(request, 'teacher/view_timetable.html', context)


@login_required(login_url='/')
def edit_timetable(request, id):
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
    timetable = get_object_or_404(Timetable, id=id, teacher__admin=request.user)
    timetable.delete()
    messages.success(request, 'Timetable deleted successfully!')
    return redirect('view_timetable')


@login_required(login_url='/')
def view_teacher_notifications(request):
    teacher = Teacher.objects.get(admin=request.user)  # Get the logged-in teacher
    notifications = TeacherNotification.objects.filter(teacher=teacher).order_by('-created_at')
    
    # Count unread notifications
    unread_count = TeacherNotification.objects.filter(teacher=teacher, read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,  # Pass the unread count to the template
    }
    return render(request, 'teacher/view_teacher_notifications.html', context)

@login_required(login_url='/')
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(TeacherNotification, id=notification_id)
    notification.read = True
    notification.save()
    return redirect('view_teacher_notifications')