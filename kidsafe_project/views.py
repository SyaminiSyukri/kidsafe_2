from django.shortcuts import render, redirect, get_object_or_404
from kidsafe_app.emailbackend import emailbackend
from django.contrib.auth import authenticate, logout, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from kidsafe_app.models import CustomUser


def BASE(request):
    return render(request, 'base.html')


def LOGIN(request):
    return render(request, 'login.html')


def doLogin(request):
    """
    Handles user authentication and login process.
    Sets up session data and redirects based on user type.
    """
    if request.method == "POST":
        # Clear any existing session data before new login
        # This prevents session fixation attacks
        request.session.flush()
        
        # Authenticate user with email and password
        user = emailbackend.authenticate(
            request,
            username=request.POST.get('email'), 
            password=request.POST.get('password'),
        )
        
        if user is not None:
            # Login successful - set up session and redirect
            login(request, user)
            
            # Store essential user data in session for quick access
            request.session['user_id'] = user.id
            request.session['user_type'] = user.user_type
            request.session.set_expiry(1209600)  # Session expires in 2 weeks (in seconds)
            
            # Redirect based on user type (RBAC - Role Based Access Control)
            # User types:
            # 1 = Admin, 2 = Teacher, 3 = Student, 4 = Canteen staff
            if user.user_type == '1':
                return redirect('admin_home')
            elif user.user_type == '2':
                return redirect('teacher_home')
            elif user.user_type == '3':
                return redirect('student_home')
            elif user.user_type == '4':
                return redirect('canteen_home')
        
        # Authentication failed - show error and redirect back to login
        messages.error(request, 'Email and Password Are Invalid!')
        return redirect('login')
    
    # If not a POST request, redirect to login page
    return redirect('login')
        

def doLogout(request):
    """
    Handles user logout by clearing session data.
    Important for security to properly clean up sessions.
    """
    # Clear all session data to prevent session fixation
    request.session.flush()
    logout(request)
    return redirect('login')


@login_required(login_url='/')
def profile(request):
    """
    Displays user profile. 
    Requires login - unauthorized users are redirected to login page.
    """
    # Get current user from database
    user = CustomUser.objects.get(id=request.user.id)
    
    context = {
        "user": user,
    }
    return render(request, 'profile.html', context)


@login_required(login_url='/')
def profile_update(request):
    """
    Handles profile updates including:
    - Basic info (first/last name)
    - Password changes
    - Profile picture updates
    """
    if request.method == "POST":
        # Get form data
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')

        try:
            # Get current user object
            customuser = CustomUser.objects.get(id=request.user.id)

            # Update basic info
            customuser.first_name = first_name
            customuser.last_name = last_name

            # Handle password change if provided
            if password is not None and password != "":
                # Uses set_password to properly hash the password
                customuser.set_password(password)

            # Handle profile picture update if provided
            if profile_pic is not None and profile_pic != "":
                customuser.profile_pic = profile_pic 

            # Save all changes
            customuser.save()
            messages.success(request, 'Your Profile Updated Successfully!')
            return redirect('profile')

        except Exception as e:
            # Log the error in production
            messages.error(request, 'Failed To Update Your Profile')

    return render(request, 'profile.html')


@login_required
def profile_delete(request, user_id):
    """
    Handles deletion of profile picture.
    Includes permission checks to ensure only authorized users can delete.
    """
    # Authorization check - only certain user types can delete profile pictures
    # In this case, only user types 1 (admin), 2 (teacher), or 3 (student)
    if request.user.user_type not in ['1', '2', '3']: 
        messages.error(request, 'You do not have permission to delete this profile picture.')
        return redirect('profile')

    # Get user object or return 404 if not found
    user = get_object_or_404(CustomUser, id=user_id)

    # Delete profile picture if it exists
    if user.profile_pic:
        # Delete the actual file from storage
        user.profile_pic.delete()
        # Clear the reference in the database
        user.profile_pic = ""
        user.save()
        messages.success(request, 'Profile picture deleted successfully!')
    else:
        messages.warning(request, 'No profile picture to delete.')

    # Redirect to 'next' parameter if provided, otherwise to profile page
    next_url = request.GET.get('next', 'profile')
    return redirect(next_url)