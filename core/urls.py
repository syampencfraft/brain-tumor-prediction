from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('doctor-signup/', views.doctor_signup, name='doctor_signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard-redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor-profile/', views.doctor_profile, name='doctor_profile'),
    path('doctors/', views.list_doctors, name='list_doctors'),
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve-doctor/<int:doctor_id>/', views.approve_doctor, name='approve_doctor'),
    path('reject-doctor/<int:doctor_id>/', views.reject_doctor, name='reject_doctor'),
    path('appointment/update/<int:appointment_id>/<str:new_status>/', views.update_appointment_status, name='update_status'),
    path('predict/', views.index, name='index'),
    path('upload/', views.upload_image, name='upload_image'),
]
