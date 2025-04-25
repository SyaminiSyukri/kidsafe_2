from django.shortcuts import redirect
from django.contrib import messages

class SessionVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for login/logout pages
        if request.path in ['/login', '/doLogin', '/doLogout']:
            return self.get_response(request)
            
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Verify session matches logged-in user
            if 'user_id' not in request.session or request.session['user_id'] != request.user.id:
                messages.error(request, 'Session conflict detected. Please login again.')
                return redirect('doLogout')
                
        return self.get_response(request)