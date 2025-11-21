from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('librarian', 'Librarian'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.student_id}"


class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='assignments')
    assigned_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    completion_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.title} - {self.student.user.username}"


class Attendance(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    present = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date']
    
    def __str__(self):
        status = "Present" if self.present else "Absent"
        return f"{self.student.user.username} - {self.date} - {status}"
