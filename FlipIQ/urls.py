from django.contrib import admin
from django.urls import path, include
from FlipIQ_APP import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # ✅ Landing page
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout/password views
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
]   