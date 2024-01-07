"""
URL configuration for chore_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.parent_profile, name='parent_profile'),
    # path('accounts/', include('allauth.urls')),
    # path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('accounts/profile/', views.profile, name='profile'),
    path('parent_profile/', views.parent_profile, name='parent_profile'),
    path('child_profile/', views.child_profile, name='child_profile'),
    path('child_chore/', views.child_chore, name='child_chore'),

    path('create_chore/', views.create_chore, name='create_chore'),
    path('edit_chore/<int:pk>/', views.edit_chore, name='edit_chore'),
    path('toggle_availability/<int:pk>/',
         views.toggle_availability, name='toggle_availability'),
    path('delete_chore/<int:pk>/', views.delete_chore, name='delete_chore'),

    path('claim_chore/<int:pk>/', views.claim_chore, name='claim_chore'),
    path('return_chore/<int:pk>/', views.return_chore, name='return_chore'),
    path('approve_chore_claim/<int:pk>/<int:penalty>/',
         views.approve_chore_claim, name='approve_chore_claim'),
    path('reject_chore_claim/<int:pk>/',
         views.reject_chore_claim, name='reject_chore_claim'),

    path('point_adjustment/<int:pk>/',
         views.point_adjustment, name='point_adjustment'),
    path('pocket_money_adjustment/<int:pk>/',
         views.pocket_money_adjustment, name='pocket_money_adjustment'),
    path('convert_points_to_money/<int:pk>/',
         views.convert_points_to_money, name='convert_points_to_money'),
    path('daily_action/', views.daily_action, name='daily_action'),

    path('settings/', views.settings, name='settings'),
    path('edit_settings/<int:pk>/', views.edit_settings, name='edit_settings'),

]
