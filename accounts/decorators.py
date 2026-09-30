from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
        if not request.user.is_admin_user:
            raise PermissionDenied("Only administrators can access this section.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

def telecaller_required(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
