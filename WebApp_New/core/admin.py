from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, StudentProfile, Assignment, Attendance


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'student_id', 'date_of_birth', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'student_id']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'assigned_date', 'due_date', 'marks', 'max_marks', 'completion_status']
    list_filter = ['assigned_date', 'due_date', 'completion_status']
    search_fields = ['title', 'student__user__username']
    date_hierarchy = 'assigned_date'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'present', 'created_at']
    list_filter = ['date', 'present', 'created_at']
    search_fields = ['student__user__username']
    date_hierarchy = 'date'
