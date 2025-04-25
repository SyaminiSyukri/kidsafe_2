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
    if request.method == "POST":
        # Clear any existing session data before new login
        request.session.flush()
        
        user = emailbackend.authenticate(
            request,
            username=request.POST.get('email'),
            password=request.POST.get('password'),
        )
        
        if user is not None:
            login(request, user)
            # Store user-specific data in session
            request.session['user_id'] = user.id
            request.session['user_type'] = user.user_type
            request.session.set_expiry(1209600)  # 2 weeks
            
            # Redirect based on user type
            if user.user_type == '1':
                return redirect('admin_home')
            elif user.user_type == '2':
                return redirect('teacher_home')
            elif user.user_type == '3':
                return redirect('student_home')
            elif user.user_type == '4':
                return redirect('canteen_home')
        
        messages.error(request, 'Email and Password Are Invalid!')
        return redirect('login')
    
    return redirect('login')
        

def doLogout(request):
    # Clear all session data
    request.session.flush()
    logout(request)
    return redirect('login')


@login_required (login_url='/')
def profile(request):
    user = CustomUser.objects.get(id = request.user.id)
    
    context = {
        "user": user,
    }
    return render(request, 'profile.html',context)


@login_required (login_url='/')
def profile_update(request):
    if request.method == "POST":
        profile_pic = request.FILES.get('profile_pic')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        #email = request.POST.get('email')
        #username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            customuser = CustomUser.objects.get(id = request.user.id)

            customuser.first_name = first_name
            customuser.last_name = last_name
            #customuser.profile_pic = profile_pic 

            if password !=None and password != "":
                customuser.set_password(password)

            if profile_pic !=None and profile_pic != "":
                customuser.profile_pic = profile_pic 

            customuser.save()
            messages.success(request, 'Your Profile Updated Successfully!')
            return redirect('profile')

        except:
            messages.error(request, 'Failed To Update Your Profile')

    return render(request, 'profile.html')


@login_required
def profile_delete(request, user_id):
    # Ensure the user is deleting their own profile picture or has permission
    if request.user.user_type not in ['1', '2', '3']: 
        messages.error(request, 'You do not have permission to delete this profile picture.')
        return redirect('profile')

    # Fetch the user whose profile picture is being deleted
    user = get_object_or_404(CustomUser , id=user_id)

    # Delete the profile picture if it exists
    if user.profile_pic:
        user.profile_pic.delete()  # Delete the file from storage
        user.profile_pic = ""  # Clear the profile picture field
        user.save()
        messages.success(request, 'Profile picture deleted successfully!')
    else:
        messages.warning(request, 'No profile picture to delete.')

    # Redirect back to the page specified in the 'next' parameter or fallback to profile
    next_url = request.GET.get('next', 'profile')
    return redirect(next_url)


