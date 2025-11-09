from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import CustomUser, Attendance, Assignment, StudentProfile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    role = request.user.role
    
    if role == 'student':
        return redirect('student_view')
    elif role == 'teacher':
        return redirect('teacher_dashboard')
    elif role == 'librarian':
        return redirect('librarian_dashboard')
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('login')


@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    students = StudentProfile.objects.all()
    context = {
        'students': students,
        'user': request.user
    }
    return render(request, 'teacher_dashboard.html', context)


@login_required
def teacher_attendance_edit(request):
    if request.user.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    students = StudentProfile.objects.all()
    
    if request.method == 'POST':
        date = request.POST.get('date', timezone.now().date())
        for student in students:
            present = request.POST.get(f'present_{student.id}', 'off') == 'on'
            attendance, created = Attendance.objects.get_or_create(
                student=student,
                date=date,
                defaults={'present': present}
            )
            if not created:
                attendance.present = present
                attendance.save()
        
        messages.success(request, 'Attendance updated successfully.')
        return redirect('teacher_attendance_edit')
    
    # Get today's date for default
    today = timezone.now().date()
    # Get attendance for today and create a list with student and attendance status
    students_with_attendance = []
    for student in students:
        try:
            att = Attendance.objects.get(student=student, date=today)
            is_present = att.present
        except Attendance.DoesNotExist:
            is_present = False
        students_with_attendance.append({
            'student': student,
            'is_present': is_present
        })
    
    context = {
        'students_with_attendance': students_with_attendance,
        'today': today,
        'user': request.user
    }
    return render(request, 'teacher_attendance_edit.html', context)


@login_required
def teacher_assignment_edit(request):
    if request.user.role != 'teacher':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    students = StudentProfile.objects.all()
    assignments = Assignment.objects.all().order_by('-assigned_date')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            due_date = request.POST.get('due_date')
            max_marks = request.POST.get('max_marks', 100)
            student_ids = request.POST.getlist('students')
            
            for student_id in student_ids:
                student = get_object_or_404(StudentProfile, id=student_id)
                Assignment.objects.create(
                    title=title,
                    description=description,
                    student=student,
                    due_date=due_date if due_date else None,
                    max_marks=max_marks
                )
            messages.success(request, 'Assignment created successfully.')
        
        elif action == 'update_marks':
            assignment_id = request.POST.get('assignment_id')
            marks = request.POST.get('marks')
            assignment = get_object_or_404(Assignment, id=assignment_id)
            if marks:
                assignment.marks = marks
                assignment.save()
                messages.success(request, 'Marks updated successfully.')
        
        elif action == 'update_status':
            assignment_id = request.POST.get('assignment_id')
            completion_status = request.POST.get('completion_status') == 'on'
            assignment = get_object_or_404(Assignment, id=assignment_id)
            assignment.completion_status = completion_status
            assignment.save()
            messages.success(request, 'Completion status updated successfully.')
        
        return redirect('teacher_assignment_edit')
    
    context = {
        'students': students,
        'assignments': assignments,
        'user': request.user
    }
    return render(request, 'teacher_assignment_edit.html', context)


@login_required
def student_view(request):
    if request.user.role != 'student':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    try:
        student = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('dashboard')
    
    attendance_records = Attendance.objects.filter(student=student).order_by('-date')[:30]
    assignments = Assignment.objects.filter(student=student).order_by('-assigned_date')
    
    # Calculate attendance percentage
    total_attendance = attendance_records.count()
    present_count = attendance_records.filter(present=True).count()
    attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    context = {
        'student': student,
        'attendance_records': attendance_records,
        'assignments': assignments,
        'attendance_percentage': round(attendance_percentage, 2),
        'present_count': present_count,
        'total_attendance': total_attendance
    }
    return render(request, 'student_view.html', context)


@login_required
def librarian_dashboard(request):
    if request.user.role != 'librarian':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    students = StudentProfile.objects.all()
    context = {
        'students': students,
        'user': request.user
    }
    return render(request, 'librarian_dashboard.html', context)


@login_required
def librarian_marks_edit(request):
    if request.user.role != 'librarian':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    students = StudentProfile.objects.all()
    assignments = Assignment.objects.all().order_by('-assigned_date')
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        marks = request.POST.get('marks')
        assignment = get_object_or_404(Assignment, id=assignment_id)
        if marks:
            assignment.marks = marks
            assignment.save()
            messages.success(request, 'Marks updated successfully.')
        return redirect('librarian_marks_edit')
    
    context = {
        'students': students,
        'assignments': assignments,
        'user': request.user
    }
    return render(request, 'librarian_marks_edit.html', context)
