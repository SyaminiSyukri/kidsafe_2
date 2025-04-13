from django.contrib import admin
from . models import *
from django.contrib.auth.admin import UserAdmin

# Register your models here.
class UserModel(UserAdmin):
    list_display = ['username', 'user_type']

admin.site.register(CustomUser, UserModel)
admin.site.register(Classroom)
admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(Canteen)
admin.site.register(Card)
admin.site.register(Subject)
admin.site.register(ExamTitle)
admin.site.register(ExamResult)
admin.site.register(Timetable)
admin.site.register(Dietary)
admin.site.register(Attendance)
admin.site.register(StudentAccount)
admin.site.register(InventoryItem)
admin.site.register(Transaction)
admin.site.register(TeacherNotification)
admin.site.register(StudentNotification)
admin.site.register(CanteenNotification)
admin.site.register(FeedbackToAdmin)