from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .models import Profile


def home(request):
    """Render the home page after login/signup."""
    return render(request, 'FlipIQ_APP/home.html')


@require_http_methods(["GET", "POST"])
def signup(request):
    """Handles user signup with role selection."""
    form = UserCreationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            # ✅ Create user
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = form.cleaned_data.get('username', '').strip()
            user.save()

            # ✅ Handle role selection
            role = request.POST.get('role', Profile.ROLE_STUDENT)
            if role not in dict(Profile.ROLE_CHOICES):
                role = Profile.ROLE_STUDENT

            Profile.objects.create(user=user, role=role)

            # ✅ Log in user automatically
            login(request, user)
            messages.success(request, "Account created successfully! Welcome to FlipIQ.")
            return redirect('home')

        else:
            # ❌ Debug and show errors in console
            print("Form not valid:", form.errors)

    # ⬇ Always render template (with form + errors)
    return render(request, 'registration/signup.html', {'form': form})


def profile(request):
    """Render the user's profile page."""
    return render(request, 'FlipIQ_APP/profile.html')