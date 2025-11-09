from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Teacher routes
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/attendance/', views.teacher_attendance_edit, name='teacher_attendance_edit'),
    path('teacher/assignments/', views.teacher_assignment_edit, name='teacher_assignment_edit'),
    
    # Student routes
    path('student/view/', views.student_view, name='student_view'),
    
    # Librarian routes
    path('librarian/dashboard/', views.librarian_dashboard, name='librarian_dashboard'),
    path('librarian/marks/', views.librarian_marks_edit, name='librarian_marks_edit'),
]
