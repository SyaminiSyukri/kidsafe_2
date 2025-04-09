import logging
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import Classroom, CustomUser, Student, Teacher, Canteen, Subject, Card, Attendance, StudentAccount, TeacherNotification
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString
from django.shortcuts import render
from django.http import JsonResponse
from smartcard.Exceptions import NoCardException, CardConnectionException
from django.db import IntegrityError
from decimal import Decimal


@login_required(login_url='/')
def home(request):
    # Count total students, teachers, and canteen staff
    student_count = Student.objects.all().count()
    teacher_count = Teacher.objects.all().count()
    canteen_count = Canteen.objects.all().count()

    # Calculate total present students (students who have scanned their attendance today)
    today = timezone.now().date()
    total_present_students = Attendance.objects.filter(
        arrival_time__date=today,
        departure_time__isnull=True
    ).count()

    # Calculate card statistics
    total_registered_cards = Card.objects.all().count()
    total_assigned_cards = Card.objects.filter(student__isnull=False).count()
    total_active_cards = Card.objects.filter(is_active=True).count()
    total_inactive_cards = Card.objects.filter(is_active=False).count()

    context = {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'canteen_count': canteen_count,
        'total_present_students': total_present_students,
        'total_registered_cards': total_registered_cards,
        'total_assigned_cards': total_assigned_cards,
        'total_active_cards': total_active_cards,
        'total_inactive_cards': total_inactive_cards,
    }
    return render(request, 'administrator/home.html', context)

#STUDENT
@login_required(login_url='/')
def add_student(request):
    classroom = Classroom.objects.all()

    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_student')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_student')
        
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 3
            )
            user.set_password(password)
            user.save()

            classroom = Classroom.objects.get(id = classroom_id)

            student = Student (
                admin = user,
                gender = gender,
                classroom_id = classroom,
            )
            student.save()
            messages.success(request, user.first_name + " " + user.last_name + ' Successfully Added!')
            return redirect('view_student')

    context = {
        'classroom' : classroom,
    }

    return render(request, 'administrator/add_student.html', context)

@login_required(login_url='/')
def view_student(request):
    # Fetch all classrooms
    classrooms = Classroom.objects.all()
    
    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Create a dictionary to hold students grouped by classroom
    students_by_classroom = {}
    
    for classroom in classrooms:
        # Filter students by classroom and search query
        students = Student.objects.filter(classroom_id=classroom)
        if search_query:
            students = students.filter(
                admin__first_name__icontains=search_query
            ) | students.filter(
                admin__last_name__icontains=search_query
            )
        if students.exists():
            students_by_classroom[classroom] = students
    
    # Add a warning message if no students are found
    if search_query and not students_by_classroom:
        messages.warning(request, f'No students found: {search_query}')

    context = {
        'students_by_classroom': students_by_classroom,
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'administrator/view_student.html', context)

@login_required(login_url='/')
def edit_student(request, id):
    student = get_object_or_404(Student, id=id)  # Get a single student object
    classroom = Classroom.objects.all()

    context = {
        'student': student,  # Pass the student object directly
        'classroom': classroom,
    }
    return render(request, 'administrator/edit_student.html', context)

@login_required(login_url='/')
def update_student(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = CustomUser.objects.get(id=student_id)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        if password != None and password != "":
            user.set_password(password)

        if profile_pic != None and profile_pic != "":
            user.profile_pic = profile_pic
        user.save()

        student = Student.objects.get(admin=student_id)
        student.gender = gender

        classroom = Classroom.objects.get(id=classroom_id)
        student.classroom_id = classroom

        student.save()
        messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully updated!')
        return redirect('view_student')

    return render(request, 'administrator/edit_student.html')

@login_required(login_url='/')
def delete_student(request, admin):
    student = CustomUser.objects.get(id = admin)
    student.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_student')


#SUBJECT
@login_required(login_url='/')
def add_subject(request):
    teachers = Teacher.objects.all()

    if request.method == "POST":
        subject_name = request.POST.get('subject_name')
        teacher_id = request.POST.get('teacher_id')

        teacher = Teacher.objects.get(id=teacher_id)

        subject = Subject(
            name=subject_name,
            teacher=teacher,
        )
        subject.save()
        messages.success(request, f'{subject.name} Subject Added Successfully!')
        return redirect('view_subject')

    context = {
        'teachers': teachers,
    }
    return render(request, 'administrator/add_subject.html', context)

@login_required(login_url='/')
def view_subject(request):
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
    }
    return render(request, 'administrator/view_subject.html', context)

@login_required(login_url='/')
def edit_subject(request, id):
    subject = get_object_or_404(Subject, id=id)
    teachers = Teacher.objects.all()

    if request.method == "POST":
        subject_name = request.POST.get('subject_name')
        teacher_id = request.POST.get('teacher_id')

        teacher = Teacher.objects.get(id=teacher_id)

        subject.name = subject_name
        subject.teacher = teacher
        subject.save()
        messages.success(request, f'{subject.name} subject updated successfully!')
        return redirect('view_subject')

    context = {
        'subject': subject,
        'teachers': teachers,
    }
    return render(request, 'administrator/edit_subject.html', context)

@login_required(login_url='/')
def delete_subject(request, id):
    subject = get_object_or_404(Subject, id=id)
    subject.delete()
    messages.success(request, f'{subject.name} Subject Deleted Successfully!')
    return redirect('view_subject')


#TEACHER
@login_required(login_url='/')
def add_teacher(request):
    classroom = Classroom.objects.all()

    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_student')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_student')
        
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 2
            )
            user.set_password(password)
            user.save()

            classroom = Classroom.objects.get(id = classroom_id)

            teacher = Teacher (
                admin = user,
                gender = gender,
                classroom_id = classroom,
            )
            teacher.save()
            messages.success(request, user.first_name + " " + user.last_name + ' Successfully Added!')
            return redirect('view_teacher')

    context = {
        'classroom' : classroom,
    }

    return render(request, 'administrator/add_teacher.html', context)

@login_required(login_url='/')
def view_teacher(request):
    teacher = Teacher.objects.all()
    
    context = {
        'teacher':teacher,
    }
    return render(request, 'administrator/view_teacher.html', context)

@login_required(login_url='/')
def edit_teacher(request, id):
    teacher = get_object_or_404(Teacher, id=id)  # Get a single teacher object
    classroom = Classroom.objects.all()

    context = {
        'teacher': teacher,  # Pass the teacher object directly
        'classroom': classroom,
    }
    return render(request, 'administrator/edit_teacher.html', context)

@login_required(login_url='/')
def update_teacher(request):
    if request.method == "POST":
        teacher_id = request.POST.get('teacher_id')
        print(teacher_id)
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = CustomUser.objects.get(id=teacher_id)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        if password != None and password != "":
            user.set_password(password)

        if profile_pic != None and profile_pic != "":
            user.profile_pic = profile_pic
        user.save()

        teacher = Teacher.objects.get(admin=teacher_id)
        teacher.gender = gender

        classroom = Classroom.objects.get(id=classroom_id)
        teacher.classroom_id = classroom

        teacher.save()
        messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully updated!')
        return redirect('view_teacher')

    return render(request, 'administrator/edit_teacher.html')

@login_required(login_url='/')
def delete_teacher(request, admin):
    teacher = CustomUser.objects.get(id = admin)
    teacher.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_teacher')


#CANTEEN
@login_required(login_url='/')
def add_canteen(request):
    canteen = Canteen.objects.all()

    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_student')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_student')
        
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 4
            )
            user.set_password(password)
            user.save()

            canteen = Canteen (
                admin = user,
            )
            canteen.save()
            messages.success(request, user.first_name + " " + user.last_name + ' Successfully Added!')
            return redirect('view_canteen')


    return render (request, 'administrator/add_canteen.html')

@login_required(login_url='/')
def view_canteen(request):
    canteen = Canteen.objects.all()
    
    context = {
        'canteen':canteen,
    }
    return render(request, 'administrator/view_canteen.html', context)

@login_required(login_url='/')
def edit_canteen(request, id):
    canteen = get_object_or_404(Canteen, id=id)
    context = {
        'canteen': canteen,
    }
    return render(request, 'administrator/edit_canteen.html', context)      

@login_required(login_url='/')
def update_canteen(request):
    if request.method == "POST":
        canteen_id = request.POST.get('canteen_id')
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = CustomUser.objects.get(id=canteen_id)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = username

        if password != None and password != "":
            user.set_password(password)

        if profile_pic != None and profile_pic != "":
            user.profile_pic = profile_pic
        user.save()

        canteen = Canteen.objects.get(admin=canteen_id)
        canteen.save()
        messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully updated!')
        return redirect('view_canteen')

    return render(request, 'administrator/edit_canteen.html')

@login_required(login_url='/')
def delete_canteen(request, admin):
    canteen = CustomUser.objects.get(id = admin)
    canteen.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_canteen')


#CARD
@login_required(login_url='/')
def register_card(request):
    if request.method == 'POST':
        card_id = request.POST.get('card_id')

        # Check if the card ID is already registered
        if Card.objects.filter(card_id=card_id).exists():
            messages.error(request, 'This card ID is already registered in the system.')
            return redirect('register_card')

        # Register the new card
        card = Card(card_id=card_id)
        card.save()
        messages.success(request, 'Card successfully registered.')
        return redirect('register_card')

    return render(request, 'administrator/register_card.html')

def view_registered_cards(request):
    cards = Card.objects.all()  # Fetch all registered cards
    context = {
        'cards': cards,
    }
    return render(request, 'administrator/view_registered_cards.html', context)

@login_required(login_url='/')
def read_card(request):
    if request.method == 'GET' and not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Render the HTML template for normal GET requests
        return render(request, 'administrator/read_card.html')
    
    # Handle AJAX requests for reading the card
    try:
        reader_list = readers()
        #if not reader_list:
            #return JsonResponse({'error': 'No NFC reader found. Please connect the reader and try again.'}, status=400)

        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()

        SELECT = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # APDU command to get UID
        data, sw1, sw2 = connection.transmit(SELECT)

        if sw1 == 0x90 and sw2 == 0x00:
            card_id = toHexString(data)

            # Check if the card is registered
            try:
                card = Card.objects.get(card_id=card_id)
                if card.student and card.is_active:
                    return JsonResponse({
                        'card_id': card_id,
                        'assigned': True,
                        'student_name': f"{card.student.admin.first_name} {card.student.admin.last_name}",
                        'classroom': card.student.classroom_id.name,
                        'issued_date': card.issued_date.strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    return JsonResponse({
                        'card_id': card_id,
                        'assigned': False,
                        'message': 'This card is not yet assigned to a student.'
                    })
            except Card.DoesNotExist:
                # Card is not registered
                return JsonResponse({
                    'card_id': card_id,
                    'registered': False,
                    'error': 'This card is not yet registered in the system.'
                })
        else:
            # Instead of returning an error, return an empty card_id
            return JsonResponse({'card_id': ''})  # No card detected, return empty card_id

    except NoCardException:
        return JsonResponse({'card_id': ''})  # No card detected, return empty card_id
    #except CardConnectionException:
        #return JsonResponse({'error': 'Unable to connect to the card. Please try again.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

logger = logging.getLogger(__name__)

@login_required(login_url='/')
def scan_and_assign_card(request):
    if request.method == 'POST':
        try:
            card_id = request.POST.get('card_id')
            student_id = request.POST.get('student_id')

            # Check if the card exists
            card = Card.objects.get(card_id=card_id)

            # Check if the student exists
            student = Student.objects.get(id=student_id)

            # Check if the card is already assigned to another active student
            if card.student and card.is_active:
                return JsonResponse({
                    'success': False,
                    'error': f'Card {card_id} is already assigned to {card.student.admin.first_name} {card.student.admin.last_name}.'
                })

            # Assign the student to the card
            card.student = student
            card.is_active = True
            card.save()

            # Return success message and assigned student details
            return JsonResponse({
                'success': True,
                'message': 'Card successfully assigned.',
                'student_name': f"{student.admin.first_name} {student.admin.last_name}",
                'card_id': card_id
            })

        #except Card.DoesNotExist:
            #return JsonResponse({'success': False, 'error': 'Card not found.'}, status=404)

        #except Student.DoesNotExist:
            #return JsonResponse({'success': False, 'error': 'Student not found.'}, status=404)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Handle GET requests (render the page)
    classrooms = Classroom.objects.all()
    return render(request, 'administrator/scan_and_assign_card.html', {'classrooms': classrooms})

@login_required(login_url='/')
def get_students_by_classroom(request):
    if request.method == 'GET':
        classroom_id = request.GET.get('classroom_id')
        if classroom_id:
            # Fetch students who are not assigned to any active card
            assigned_student_ids = Card.objects.filter(is_active=True).values_list('student_id', flat=True)
            students = Student.objects.filter(classroom_id=classroom_id).exclude(id__in=assigned_student_ids).select_related('admin')
            student_list = [{
                'id': student.id,
                'first_name': student.admin.first_name,
                'last_name': student.admin.last_name
            } for student in students]
            return JsonResponse({'students': student_list})
        return JsonResponse({'students': []})

@login_required(login_url='/')
def assigned_students(request):
    # Fetch all classrooms
    classrooms = Classroom.objects.all()

    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Create a dictionary to hold assigned cards grouped by classroom
    assigned_cards_by_classroom = {}

    for classroom in classrooms:
        # Fetch assigned cards for students in this classroom
        assigned_cards = Card.objects.filter(student__classroom_id=classroom, is_active=True).select_related('student')
        
        # Filter by student name if a search query is provided
        if search_query:
            assigned_cards = assigned_cards.filter(
                student__admin__first_name__icontains=search_query
            ) | assigned_cards.filter(
                student__admin__last_name__icontains=search_query
            )

        if assigned_cards.exists():
            assigned_cards_by_classroom[classroom] = assigned_cards

    # Add a warning message if no assigned students are found
    if search_query and not assigned_cards_by_classroom:
        messages.warning(request, f'No students found: {search_query}')

    context = {
        'assigned_cards_by_classroom': assigned_cards_by_classroom,
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'administrator/assigned_students.html', context)


@login_required(login_url='/')
def scan_attendance(request):
    if request.method == 'POST':
        card_id = request.POST.get('card_id')

        try:
            # Check if the card is registered and active
            card = Card.objects.get(card_id=card_id)
            if not card.is_active:
                return JsonResponse({'error': 'This card is not yet assigned and cannot be used for attendance.'}, status=400)

            student = card.student

            # Check if the student has an open attendance record (no departure time)
            attendance = Attendance.objects.filter(student=student, departure_time__isnull=True).last()

            if attendance:
                # Update departure time (second scan)
                attendance.departure_time = timezone.now()  # Use timezone.now() instead of datetime.now()
                attendance.save()

                # Convert UTC times to local timezone
                local_tz = timezone.get_current_timezone()
                arrival_time_local = timezone.localtime(attendance.arrival_time, timezone=local_tz)
                departure_time_local = timezone.localtime(attendance.departure_time, timezone=local_tz)

                return JsonResponse({
                    'success': True,
                    'message': f'{student.admin.first_name} {student.admin.last_name} has left.',
                    'student_name': f"{student.admin.first_name} {student.admin.last_name}",
                    'classroom': student.classroom_id.name,
                    'gender': student.gender,
                    'email': student.admin.email,
                    'profile_pic': student.admin.profile_pic.url if student.admin.profile_pic else '',
                    'arrival_time': arrival_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                    'departure_time': departure_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                })
            else:
                # Create a new arrival record (first scan)
                attendance = Attendance(student=student, arrival_time=timezone.now())  # Use timezone.now() for arrival_time
                attendance.save()

                # Convert UTC arrival time to local timezone
                local_tz = timezone.get_current_timezone()
                arrival_time_local = timezone.localtime(attendance.arrival_time, timezone=local_tz)

                return JsonResponse({
                    'success': True,
                    'message': f'{student.admin.first_name} {student.admin.last_name} has arrived.',
                    'student_name': f"{student.admin.first_name} {student.admin.last_name}",
                    'classroom': student.classroom_id.name,
                    'gender': student.gender,
                    'email': student.admin.email,
                    'profile_pic': student.admin.profile_pic.url if student.admin.profile_pic else '',
                    'arrival_time': arrival_time_local.strftime('%Y-%m-%d %H:%M:%S'),
                    'departure_time': 'Still in school',
                })

        except Card.DoesNotExist:
            return JsonResponse({'error': 'Card not found. Please register the card first.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # Render the attendance page for GET requests
    attendance_records = Attendance.objects.all().order_by('-arrival_time')
    return render(request, 'administrator/student_attendance.html', {'attendance_records': attendance_records})

def attendance_list(request):
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('date', '')

    # Fetch all attendance records
    attendance_records = Attendance.objects.select_related('student__classroom_id').all().order_by('student__classroom_id', '-arrival_time')

    # Apply search filter (by student name)
    if search_query:
        attendance_records = attendance_records.filter(
            student__admin__first_name__icontains=search_query
        ) | attendance_records.filter(
            student__admin__last_name__icontains=search_query
        )

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

    # Group attendance records by classroom
    classroom_attendance = {}
    for record in attendance_records:
        classroom_name = record.student.classroom_id.name
        if classroom_name not in classroom_attendance:
            classroom_attendance[classroom_name] = []
        classroom_attendance[classroom_name].append(record)

    context = {
        'classroom_attendance': classroom_attendance,
        'search_query': search_query,
        'selected_date': date_filter,  # Pass the selected date to the template
    }
    return render(request, 'administrator/attendance_list.html', context)


def deactivate_card(request, card_id):
    card = get_object_or_404(Card, card_id=card_id)

    if request.method == 'POST':
        deactivation_reason = request.POST.get('deactivation_reason')

        # Deactivate the card and remove the student association
        card.student = None  # Remove the student association
        card.is_active = False
        card.deactivated_date = datetime.now()
        card.deactivation_reason = deactivation_reason
        card.save()

        messages.success(request, 'Card successfully deactivated.')
        return redirect('assigned_students')

    context = {
        'card': card,
    }
    return render(request, 'administrator/deactivate_card.html', context)

def view_deactivated_cards(request):
    deactivated_cards = Card.objects.filter(is_active=False)  # Fetch only deactivated cards
    context = {
        'deactivated_cards': deactivated_cards,
    }
    return render(request, 'administrator/deactivated_cards.html', context)


def scan_and_add_balance(request):
    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        amount = request.POST.get('amount')

        try:
            # Check if the card exists and is assigned to a student
            card = Card.objects.get(card_id=card_id)
            if not card.student or not card.is_active:
                return JsonResponse({
                    'success': False,
                    'error': 'This card is not assigned to a student or is inactive.'
                })

            # Get or create the student's account
            student_account, created = StudentAccount.objects.get_or_create(student=card.student)

            if amount:
                # Convert the amount to Decimal before adding it to the balance
                try:
                    amount_decimal = Decimal(amount)
                    if amount_decimal < 0:
                        return JsonResponse({
                            'success': False,
                            'error': 'Amount cannot be negative.'
                        })
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid amount. Please enter a valid number.'
                    })

                student_account.balance += amount_decimal
                student_account.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Successfully added ${amount} to {card.student.admin.first_name} {card.student.admin.last_name}\'s account.',
                    'new_balance': str(student_account.balance)  # Convert Decimal to string for JSON serialization
                })
            else:
                # Return the current balance if no amount is provided
                return JsonResponse({
                    'success': True,
                    'current_balance': str(student_account.balance),  # Convert Decimal to string for JSON serialization
                    'student_name': f"{card.student.admin.first_name} {card.student.admin.last_name}"
                })

        except Card.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Card not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return render(request, 'administrator/scan_and_add_balance.html')


@login_required(login_url='/')
def send_teacher_notification(request):
    teachers = Teacher.objects.all()  # Get all teachers using Teacher model

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        selected_recipients = request.POST.getlist('recipients')  # Get selected recipients

        if not selected_recipients:
            messages.warning(request, 'Please select at least one recipient.')
            return redirect('send_teacher_notification')

        # Check if "All Teachers" was selected
        if 'all' in selected_recipients:
            # Create notification for all teachers
            for teacher in teachers:
                notification = TeacherNotification(
                    title=title,
                    description=description,
                    file=file,
                    teacher=teacher,
                    sender=request.user  # Set the sender to the current admin user
                )
                notification.save()
        else:
            # Create notification for selected teachers only
            for teacher_id in selected_recipients:
                teacher = Teacher.objects.get(id=teacher_id)
                notification = TeacherNotification(
                    title=title,
                    description=description,
                    file=file,
                    teacher=teacher,
                    sender=request.user
                )
                notification.save()

        messages.success(request, 'Notification sent successfully!')
        return redirect('send_teacher_notification')

    context = {
        'teachers': teachers,
    }
    return render(request, 'administrator/send_teacher_notification.html', context)