from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .models import CustomUser, Attendance, Assignment, StudentProfile
from .ai_agent import predict_from_params



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


def signup_student(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        student_id = request.POST.get('student_id', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup_student.html')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'signup_student.html')
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='student',
            first_name=first_name,
            last_name=last_name
        )
        
        StudentProfile.objects.create(
            user=user,
            student_id=student_id if student_id else None
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'signup_student.html')


def signup_teacher(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup_teacher.html')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'signup_teacher.html')
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='teacher',
            first_name=first_name,
            last_name=last_name,
            is_staff=True
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'signup_teacher.html')


def signup_librarian(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup_librarian.html')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'signup_librarian.html')
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='librarian',
            first_name=first_name,
            last_name=last_name,
            is_staff=True
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'signup_librarian.html')


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
    
    # Get selected date from GET or POST, default to today
    selected_date = timezone.now().date()
    if request.method == 'GET' and 'date' in request.GET:
        try:
            selected_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            selected_date = timezone.now().date()
    
    if request.method == 'POST':
        date_str = request.POST.get('date', '')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()
        
        # Handle bulk actions
        bulk_action = request.POST.get('bulk_action')
        if bulk_action == 'mark_all_present':
            for student in students:
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    date=selected_date,
                    defaults={'present': True}
                )
                if not created:
                    attendance.present = True
                    attendance.save()
            messages.success(request, f'All students marked as present for {selected_date}.')
        elif bulk_action == 'mark_all_absent':
            for student in students:
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    date=selected_date,
                    defaults={'present': False}
                )
                if not created:
                    attendance.present = False
                    attendance.save()
            messages.success(request, f'All students marked as absent for {selected_date}.')
        else:
            # Handle individual student attendance
            for student in students:
                present = request.POST.get(f'present_{student.id}', 'off') == 'on'
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    date=selected_date,
                    defaults={'present': present}
                )
                if not created:
                    attendance.present = present
                    attendance.save()
            
            messages.success(request, f'Attendance updated successfully for {selected_date}.')
        
        # Redirect to the same date
        return redirect(f'{request.path}?date={selected_date}')
    
    # Get attendance for selected date
    students_with_attendance = []
    present_count = 0
    absent_count = 0
    
    for student in students:
        try:
            att = Attendance.objects.get(student=student, date=selected_date)
            is_present = att.present
        except Attendance.DoesNotExist:
            is_present = False
        
        if is_present:
            present_count += 1
        else:
            absent_count += 1
        
        students_with_attendance.append({
            'student': student,
            'is_present': is_present
        })
    
    total_students = len(students_with_attendance)
    attendance_percentage = (present_count / total_students * 100) if total_students > 0 else 0
    
    context = {
        'students_with_attendance': students_with_attendance,
        'selected_date': selected_date,
        'today': timezone.now().date(),
        'present_count': present_count,
        'absent_count': absent_count,
        'total_students': total_students,
        'attendance_percentage': round(attendance_percentage, 1),
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
    
    # Get all attendance records for calculations (before slicing)
    all_attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    
    # Calculate attendance percentage from full QuerySet
    total_attendance = all_attendance_records.count()
    present_count = all_attendance_records.filter(present=True).count()
    attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0
    
    # Slice for display (only show last 30 records)
    attendance_records = all_attendance_records[:30]
    assignments = Assignment.objects.filter(student=student).order_by('-assigned_date')
    
    context = {
        'student': student,
        'attendance_records': attendance_records,
        'assignments': assignments,
        'attendance_percentage': round(attendance_percentage, 2),
        'present_count': present_count,
        'total_attendance': total_attendance,
        'user': request.user,
        'projected_cgpa': None
    }
    try:
        params = { 'attendance_percentage': attendance_percentage, 'present_count': present_count, 'total_attendance': total_attendance }
        print("HERE")
        pred = predict_from_params(params)
        context['projected_cgpa'] = int(round(float(pred), 2))/10
    except Exception as e:
        print("[ERROR]: ", e)
        context['projected_cgpa'] = round((attendance_percentage / 20), 2)
    

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
