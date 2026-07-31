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
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Root sends users to the profile matching their role; the parent/child
    # dashboards keep their own named routes below.
    path('', views.profile, name='home'),
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
    path('approve_chore_claim/<int:pk>/',
         views.approve_chore_claim, name='approve_chore_claim'),
    path('reject_chore_claim/<int:pk>/',
         views.reject_chore_claim, name='reject_chore_claim'),

    path('point_adjustment/<int:pk>/',
         views.point_adjustment, name='point_adjustment'),


    path('settings/', views.settings, name='settings'),
    path('messages/', views.messages, name='messages'),
    path('edit_text/<int:pk>/', views.edit_text, name='edit_text'),

    # Rewards
    path('rewards/', views.rewards_list, name='rewards_list'),
    path('create_reward/', views.create_reward, name='create_reward'),
    path('edit_reward/<int:pk>/', views.edit_reward, name='edit_reward'),
    path('delete_reward/<int:pk>/', views.delete_reward, name='delete_reward'),
    path('toggle_reward_availability/<int:pk>/', views.toggle_reward_availability, name='toggle_reward_availability'),
    path('claim_reward/<int:pk>/', views.claim_reward, name='claim_reward'),

]
