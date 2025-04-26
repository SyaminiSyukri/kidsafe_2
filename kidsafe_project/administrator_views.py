import logging
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from kidsafe_app.models import Classroom, CustomUser, Student, Teacher, Canteen, Subject, Card, Attendance, StudentAccount, TeacherNotification, StudentNotification, CanteenNotification, FeedbackToAdmin
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
    """
    Administrator dashboard showing key system statistics:
    - User counts (students, teachers, canteen staff)
    - Attendance data
    - Card management statistics
    """
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


# ADMIN
@login_required(login_url='/')
def add_admin(request):
    """
    Create new administrator accounts with full privileges.
    Validates email/username uniqueness.
    """
    if request.method == "POST":
        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if email is changed and already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect('add_admin')
        
        # Check if username is changed and already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect('add_admin')
        
        # Create new admin user with full privileges
        else:
            user = CustomUser(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                profile_pic=profile_pic,
                user_type=1,  # 1 for Administrator
                is_staff=True,  # Give staff permissions
                is_superuser=True  # Give superuser permissions
            )
            user.set_password(password)
            user.save()
            messages.success(request, f'Admin {user.first_name} {user.last_name} Successfully Added!')
            return redirect('view_admin')

    return render(request, 'administrator/add_admin.html')

@login_required(login_url='/')
def view_admin(request):
    """
    List all administrator accounts in the system.
    """
    # Get all users with user_type=1 (Administrators)
    admins = CustomUser.objects.filter(user_type=1).order_by('first_name')
    
    context = {
        'admins': admins,
    }
    return render(request, 'administrator/view_admin.html', context)

@login_required(login_url='/')
def edit_admin(request, id):
    """
    Edit administrator account details.
    Prevents email/username conflicts with other users.
    """
    admin = get_object_or_404(CustomUser, id=id, user_type=1)
    
    if request.method == "POST":
        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if email is changed and already exists
        if email != admin.email and CustomUser.objects.filter(email=email).exclude(id=admin.id).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect('edit_admin', id=id)
        
        # Check if username is changed and already exists
        if username != admin.username and CustomUser.objects.filter(username=username).exclude(id=admin.id).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect('edit_admin', id=id)

        # Update admin details
        admin.first_name = first_name
        admin.last_name = last_name
        admin.email = email
        admin.username = username

        if password:    # Only update password if provided
            admin.set_password(password)

        if profile_pic: # Only update profile pic if provided
            admin.profile_pic = profile_pic

        admin.save()
        messages.success(request, 'Admin updated successfully!')
        return redirect('view_admin')

    context = {
        'admin': admin,
    }
    return render(request, 'administrator/edit_admin.html', context)

@login_required(login_url='/')
def delete_admin(request, id):
    """
    Delete administrator account.
    Prevents self-deletion for security.
    """
    # Prevent admins from deleting their own account
    if request.user.id == int(id):
        messages.error(request, 'You cannot delete your own account!')
        return redirect('view_admin')
    
    admin = get_object_or_404(CustomUser, id=id, user_type=1)
    admin.delete()
    messages.success(request, 'Admin deleted successfully!')
    return redirect('view_admin')


# STUDENT
@login_required(login_url='/')
def add_student(request):
    """
    Create new student accounts.
    Assigns students to classrooms during creation.
    """
    classroom = Classroom.objects.all()

    if request.method == "POST":
        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if email is changed and already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_student')
        
        # Check if username is changed and already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_student')
        
        # Create new student user
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 3   # Student
            )
            user.set_password(password)
            user.save()

            # Create student profile linked to the user
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
    """
    List all students grouped by classroom.
    Supports searching by student name.
    """
    # Fetch all classrooms
    classrooms = Classroom.objects.all()
    
    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Group students by classroom with search filtering
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
    
    # Show warning if search returns no results
    if search_query and not students_by_classroom:
        messages.warning(request, f'No students found: {search_query}')

    context = {
        'students_by_classroom': students_by_classroom,
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'administrator/view_student.html', context)

@login_required(login_url='/')
def edit_student(request, id):
    """
    Display student edit form.
    """
    student = get_object_or_404(Student, id=id)  # Get a single student object
    classroom = Classroom.objects.all()

    context = {
        'student': student,  # Pass the student object directly
        'classroom': classroom,
    }
    return render(request, 'administrator/edit_student.html', context)

@login_required(login_url='/')
def update_student(request):
    """
    Update student records.
    Handles optional password and profile picture updates.
    """
    if request.method == "POST":
        # Extract form data
        student_id = request.POST.get('student_id')
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Update student account
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

        # Update student profile
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
    """
    Delete student account and profile.
    """
    student = CustomUser.objects.get(id = admin)
    student.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_student')


# SUBJECT
@login_required(login_url='/')
def add_subject(request):
    """
    Create new subjects and assign teachers.
    """
    teachers = Teacher.objects.all()

    # Create new subject with assigned teacher
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
    """
    List all subjects in the system.
    """
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
    }
    return render(request, 'administrator/view_subject.html', context)

@login_required(login_url='/')
def edit_subject(request, id):
    """
    Edit subject details and teacher assignment.
    """
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
    """
    Delete subject from system.
    """
    subject = get_object_or_404(Subject, id=id)
    subject.delete()
    messages.success(request, f'{subject.name} Subject Deleted Successfully!')
    return redirect('view_subject')


# TEACHER
@login_required(login_url='/')
def add_teacher(request):
    """
    Create new teacher accounts and assign classrooms.
    """
    classroom = Classroom.objects.all()

    if request.method == "POST":
        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        classroom_id = request.POST.get('classroom_id')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if email is changed and already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_teacher')
        
        # Check if username is changed and already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_teacher')
        
        # Create new teacher user
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 2   # Teacher
            )
            user.set_password(password)
            user.save()

            # Create teacher profile linked to the user
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
    """
    List all teachers in the system.
    """
    teacher = Teacher.objects.all()
    
    context = {
        'teacher':teacher,
    }
    return render(request, 'administrator/view_teacher.html', context)

@login_required(login_url='/')
def edit_teacher(request, id):
    """
    Display teacher edit form.
    """
    teacher = get_object_or_404(Teacher, id=id)  # Get a single teacher object
    classroom = Classroom.objects.all()

    context = {
        'teacher': teacher,  # Pass the teacher object directly
        'classroom': classroom,
    }
    return render(request, 'administrator/edit_teacher.html', context)

@login_required(login_url='/')
def update_teacher(request):
    """
    Update teacher records.
    Handles optional password and profile picture updates.
    """
    if request.method == "POST":
        # Extract form data
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

        # Update teacher account
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

        # Update teacher profile
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
    """
    Delete teacher account and profile.
    """
    teacher = CustomUser.objects.get(id = admin)
    teacher.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_teacher')


# CANTEEN
@login_required(login_url='/')
def add_canteen(request):
    """
    Create new canteen staff accounts.
    """
    canteen = Canteen.objects.all()

    if request.method == "POST":
        # Extract form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if email is changed and already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.warning(request, 'Email Is Already Taken')
            return redirect ('add_canteen')
        
        # Check if username is changed and already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.warning(request, 'Username Is Already Taken')
            return redirect ('add_canteen')
        
        # Create new canteen staff user
        else:
            user = CustomUser (
                first_name = first_name,
                last_name = last_name,
                username = username,
                email = email,
                profile_pic = profile_pic,
                user_type = 4   # Canteen staff
            )
            user.set_password(password)
            user.save()

            # Create canteen profile linked to the user
            canteen = Canteen (
                admin = user,
            )
            canteen.save()
            messages.success(request, user.first_name + " " + user.last_name + ' Successfully Added!')
            return redirect('view_canteen')


    return render (request, 'administrator/add_canteen.html')

@login_required(login_url='/')
def view_canteen(request):
    """
    List all canteen staff in the system.
    """
    canteen = Canteen.objects.all()
    
    context = {
        'canteen':canteen,
    }
    return render(request, 'administrator/view_canteen.html', context)

@login_required(login_url='/')
def edit_canteen(request, id):
    """
    Display canteen staff edit form.
    """
    canteen = get_object_or_404(Canteen, id=id)
    context = {
        'canteen': canteen,
    }
    return render(request, 'administrator/edit_canteen.html', context)      

@login_required(login_url='/')
def update_canteen(request):
    """
    Update canteen staff records.
    Handles optional password and profile picture updates.
    """
    if request.method == "POST":
        # Extract form data
        canteen_id = request.POST.get('canteen_id')
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Update canteen account
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

        # Update canteen profile
        canteen = Canteen.objects.get(admin=canteen_id)
        canteen.save()
        messages.success(request, f'{user.first_name} {user.last_name}\'s record has been successfully updated!')
        return redirect('view_canteen')

    return render(request, 'administrator/edit_canteen.html')

@login_required(login_url='/')
def delete_canteen(request, admin):
    """
    Delete canteen staff account and profile.
    """
    canteen = CustomUser.objects.get(id = admin)
    canteen.delete()
    messages.success(request, 'Record Are Successfully Deleted!')
    return redirect('view_canteen')


# CARD
@login_required(login_url='/')
def register_card(request):
    """
    Register new NFC cards in the system.
    Validates card ID uniqueness.
    """
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
    """
    List all registered cards in the system.
    """
    cards = Card.objects.all()  # Fetch all registered cards
    context = {
        'cards': cards,
    }
    return render(request, 'administrator/view_registered_cards.html', context)

@login_required(login_url='/')
def read_card(request):
    """
    Handle NFC card reading functionality.
    Supports both direct page access and AJAX requests.
    """
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

        # APDU command to get card UID
        SELECT = [0xFF, 0xCA, 0x00, 0x00, 0x00] 
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
    """
    Assign registered cards to students.
    Includes validation to prevent duplicate assignments.
    """
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
    """
    AJAX endpoint to get students by classroom.
    Filters out students who already have active cards.
    """
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
    """
    List all students with assigned cards, grouped by classroom.
    Supports searching by student name.
    """
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

    # Show warning if search returns no results
    if search_query and not assigned_cards_by_classroom:
        messages.warning(request, f'No students found: {search_query}')

    context = {
        'assigned_cards_by_classroom': assigned_cards_by_classroom,
        'search_query': search_query,  # Pass the search query to the template
    }
    return render(request, 'administrator/assigned_students.html', context)

@login_required(login_url='/')
def scan_attendance(request):
    """
    Handle student attendance scanning via NFC cards.
    Tracks arrival and departure times.
    """
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
    """
    List attendance records with filtering by date and student name.
    Groups records by classroom for better organization.
    """
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
    """
    Deactivate student card assignment.
    Records reason for deactivation.
    """
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
    """
    List all deactivated cards with deactivation details.
    """
    deactivated_cards = Card.objects.filter(is_active=False)  # Fetch only deactivated cards
    context = {
        'deactivated_cards': deactivated_cards,
    }
    return render(request, 'administrator/deactivated_cards.html', context)

def scan_and_add_balance(request):
    """
    Add funds to student accounts via card scanning.
    Validates amount and card status.
    """
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


# NOTIFICATION
@login_required(login_url='/')
def send_teacher_notification(request):
    """
    Send notifications to teachers.
    Supports sending to individual teachers or all at once.
    """
    teachers = Teacher.objects.all()

    if request.method == "POST":
        # Extract notification details
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

@login_required(login_url='/')
def send_canteen_notification(request):
    """
    Send notifications to canteen staff.
    Similar functionality to teacher notifications.
    """
    canteens = Canteen.objects.all()  # Get all canteen staff

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        selected_recipients = request.POST.getlist('recipients')  # Get selected recipients

        if not selected_recipients:
            messages.warning(request, 'Please select at least one recipient.')
            return redirect('send_canteen_notification')

        # Check if "All Canteen Staff" was selected
        if 'all' in selected_recipients:
            # Create notification for all canteen staff
            for canteen in canteens:
                notification = CanteenNotification(
                    title=title,
                    description=description,
                    file=file,
                    canteen=canteen,
                    sender=request.user  # Set the sender to the current admin user
                )
                notification.save()
        else:
            # Create notification for selected canteen staff only
            for canteen_id in selected_recipients:
                canteen = Canteen.objects.get(id=canteen_id)
                notification = CanteenNotification(
                    title=title,
                    description=description,
                    file=file,
                    canteen=canteen,
                    sender=request.user
                )
                notification.save()

        messages.success(request, 'Notification sent successfully!')
        return redirect('send_canteen_notification')

    context = {
        'canteens': canteens,
    }
    return render(request, 'administrator/send_canteen_notification.html', context)

@login_required(login_url='/')
def send_student_notification(request):
    """
    Send notifications to students by classroom.
    Supports sending to all students or specific classrooms.
    Handles file attachments.
    """
    classrooms = Classroom.objects.all()

    if request.method == "POST":
        # Extract notification details
        title = request.POST.get('title')
        description = request.POST.get('description')
        file = request.FILES.get('file')
        selected_classrooms = request.POST.getlist('classrooms')

        if not selected_classrooms:
            messages.warning(request, 'Please select at least one classroom.')
            return redirect('send_student_notification')

        students = Student.objects.all()
        if 'all' not in selected_classrooms:
            students = students.filter(classroom_id__in=selected_classrooms)

        # Create individual notification for each student
        for student in students:
            StudentNotification.objects.create(
                student=student,
                title=title,
                description=description,
                file=file,
                sender=request.user
            )

        messages.success(request, 'Notification sent successfully!')
        return redirect('send_student_notification')

    return render(request, 'administrator/send_student_notification.html', {'classrooms': classrooms})


# FEEDBACK
@login_required(login_url='/')
def view_teacher_feedback(request):
    """
    Display feedback received from teachers.
    Shows unread count and sorts by most recent.
    """
    feedback_list = FeedbackToAdmin.objects.filter(
        sender_type='teacher'
    ).order_by('-sent_at')
    return render(request, 'administrator/teacher_feedback.html', {
        'feedback_list': feedback_list,
        'teacher_feedback_unread': feedback_list.filter(is_read=False).count()
    })

@login_required(login_url='/')
def view_student_feedback(request):
    """
    Display feedback received from students.
    Shows unread count and sorts by most recent.
    """
    feedback_list = FeedbackToAdmin.objects.filter(
        sender_type='student'
    ).order_by('-sent_at')
    return render(request, 'administrator/student_feedback.html', {
        'feedback_list': feedback_list,
        'student_feedback_unread': feedback_list.filter(is_read=False).count()
    })

@login_required(login_url='/')
def view_canteen_feedback(request):
    """
    Display feedback received from canteen staff.
    Shows unread count and sorts by most recent.
    """
    feedback_list = FeedbackToAdmin.objects.filter(
        sender_type='canteen'
    ).order_by('-sent_at')
    return render(request, 'administrator/canteen_feedback.html', {
        'feedback_list': feedback_list,
        'canteen_feedback_unread': feedback_list.filter(is_read=False).count()
    })

@login_required(login_url='/')
def mark_feedback_read(request, pk):
    """
    Mark specific feedback item as read.
    Redirects back to the appropriate feedback list.
    """
    feedback = get_object_or_404(FeedbackToAdmin, pk=pk)
    feedback.is_read = True
    feedback.save()
    return redirect(f'view_{feedback.sender_type}_feedback')