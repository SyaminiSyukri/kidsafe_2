from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER = (
        (1, 'Administrator'),
        (2, 'Teacher'),
        (3, 'Student'),
        (4, 'Canteen'),
    )

    user_type = models.CharField(choices=USER, max_length=50, default=1)
    profile_pic = models.ImageField(upload_to='media/profile_pic')

class Classroom(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    gender = models.CharField(max_length=100)
    classroom_id = models.ForeignKey(Classroom, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name

class Teacher(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    gender = models.CharField(max_length=100)
    classroom_id = models.ForeignKey(Classroom, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name

class Canteen(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name

class Card(models.Model):
    card_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=False)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    deactivated_date = models.DateTimeField(blank=True, null=True)
    deactivation_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.card_id
    

class Subject(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)  # Assign a teacher to the subject
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ExamTitle(models.Model):
    title = models.CharField(max_length=255, unique=True)  # Unique exam title
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    

class ExamResult(models.Model):
    exam_title = models.ForeignKey(ExamTitle, on_delete=models.CASCADE, null=True, blank=True)  # Make the field nullable
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.admin.first_name} - {self.subject.name} - {self.marks}"

    
class Timetable(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    timetable_image = models.ImageField(upload_to='media/timetables/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Timetable for {self.classroom.name} by {self.teacher.admin.first_name}"
    

class Dietary(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, unique=True)  # One entry per student
    food_allergy = models.TextField(blank=True, null=True)  # Store multiple allergies as comma-separated values
    dietary_restriction = models.TextField(blank=True, null=True)  # Store multiple restrictions as comma-separated values
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.admin.first_name} Dietary Details"


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    arrival_time = models.DateTimeField(auto_now_add=True)
    departure_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.admin.first_name} {self.student.admin.last_name} - {self.arrival_time}"
    

class StudentAccount(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='account')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Store balance as a decimal

    def __str__(self):
        return f"{self.student.admin.first_name} {self.student.admin.last_name} - Balance: {self.balance}"
    

class InventoryItem(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Name of the item
    image = models.ImageField(upload_to='inventory_images/', blank=True, null=True)  # Image of the item
    quantity = models.PositiveIntegerField(default=0)     # Quantity in stock
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per unit
    description = models.TextField(blank=True, null=True)  # Optional description
    created_at = models.DateTimeField(auto_now_add=True)   # Timestamp when item was added
    updated_at = models.DateTimeField(auto_now=True)       # Timestamp when item was last updated

    def __str__(self):
        return self.name
