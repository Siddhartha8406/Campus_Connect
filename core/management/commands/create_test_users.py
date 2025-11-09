from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import StudentProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users for the school management system'

    def handle(self, *args, **options):
        # Create a teacher
        teacher, created = User.objects.get_or_create(
            username='teacher1',
            defaults={
                'email': 'teacher1@school.com',
                'role': 'teacher',
                'is_staff': True
            }
        )
        if created:
            teacher.set_password('teacher123')
            teacher.save()
            self.stdout.write(self.style.SUCCESS(f'Created teacher: {teacher.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Teacher {teacher.username} already exists'))

        # Create a librarian
        librarian, created = User.objects.get_or_create(
            username='librarian1',
            defaults={
                'email': 'librarian1@school.com',
                'role': 'librarian',
                'is_staff': True
            }
        )
        if created:
            librarian.set_password('librarian123')
            librarian.save()
            self.stdout.write(self.style.SUCCESS(f'Created librarian: {librarian.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Librarian {librarian.username} already exists'))

        # Create students
        students_data = [
            {'username': 'student1', 'email': 'student1@school.com', 'student_id': 'ST001'},
            {'username': 'student2', 'email': 'student2@school.com', 'student_id': 'ST002'},
            {'username': 'student3', 'email': 'student3@school.com', 'student_id': 'ST003'},
        ]

        for student_data in students_data:
            student_user, created = User.objects.get_or_create(
                username=student_data['username'],
                defaults={
                    'email': student_data['email'],
                    'role': 'student'
                }
            )
            if created:
                student_user.set_password('student123')
                student_user.save()
                # Create student profile
                StudentProfile.objects.create(
                    user=student_user,
                    student_id=student_data['student_id']
                )
                self.stdout.write(self.style.SUCCESS(f'Created student: {student_user.username}'))
            else:
                self.stdout.write(self.style.WARNING(f'Student {student_user.username} already exists'))

        self.stdout.write(self.style.SUCCESS('\nTest users created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('Teacher: teacher1 / teacher123'))
        self.stdout.write(self.style.SUCCESS('Librarian: librarian1 / librarian123'))
        self.stdout.write(self.style.SUCCESS('Students: student1, student2, student3 / student123'))

