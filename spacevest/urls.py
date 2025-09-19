"""
URL configuration for spacevest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.views import dashboard_view, home_view, login_view, register_view, password_reset_confirm
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home_view, name='home'),
    path('api/users/', include('users.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/crypto/', include('crypto.urls')),
    path('api/banking/', include('banking.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    
    # Password reset URLs
    path('reset-password/<str:uidb64>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
    
    # Password reset complete view
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
