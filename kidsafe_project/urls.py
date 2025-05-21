from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views, administrator_views, teacher_views, student_views, canteen_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('base/', views.BASE, name='base'),

    #Login Path
    path('', views.LOGIN, name='login'),
    path('doLogin', views.doLogin, name='doLogin'),
    path('doLogout', views.doLogout, name='doLogout'),

    #Profile Update
    path('profile', views.profile, name='profile'),
    path('profile/update', views.profile_update, name='profile_update'),
    path('profile/delete/<int:user_id>/', views.profile_delete, name='profile_delete'),
    

    #Forgot Password
    path('reset-password/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',  # Custom template
    ), name='reset_password'),
    path('reset-password-sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'  # Custom template
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'  # Custom template
    ), name='password_reset_confirm'),
    path('reset-password-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'  # Custom template
    ), name='password_reset_complete'),


    #Administrator page URL
    path('administrator/home', administrator_views.home, name='admin_home'),

    path('administrator/admin/add', administrator_views.add_admin, name='add_admin'),
    path('administrator/admin/view', administrator_views.view_admin, name='view_admin'),
    path('administrator/admin/edit/<str:id>', administrator_views.edit_admin, name='edit_admin'),
    path('administrator/admin/delete/<str:id>', administrator_views.delete_admin, name='delete_admin'),

    path('administrator/student/add', administrator_views.add_student, name='add_student'),
    path('administrator/student/view', administrator_views.view_student, name='view_student'),
    path('administrator/student/edit/<str:id>', administrator_views.edit_student, name='edit_student'),
    path('administrator/student/update', administrator_views.update_student, name='update_student'),
    path('administrator/student/delete/<str:admin>', administrator_views.delete_student, name='delete_student'),

    path('administrator/teacher/add', administrator_views.add_teacher, name='add_teacher'),
    path('administrator/teacher/view', administrator_views.view_teacher, name='view_teacher'),
    path('administrator/teacher/edit/<str:id>', administrator_views.edit_teacher, name='edit_teacher'),
    path('administrator/teacher/update', administrator_views.update_teacher, name='update_teacher'),
    path('administrator/teacher/delete/<str:admin>', administrator_views.delete_teacher, name='delete_teacher'),
    
    path('administrator/canteen/add', administrator_views.add_canteen, name='add_canteen'),
    path('administrator/canteen/view', administrator_views.view_canteen, name='view_canteen'),
    path('administrator/canteen/edit/<str:id>', administrator_views.edit_canteen, name='edit_canteen'),
    path('administrator/canteen/update', administrator_views.update_canteen, name='update_canteen'),
    path('administrator/canteen/delete/<str:admin>', administrator_views.delete_canteen, name='delete_canteen'),

    path('administrator/subject/add', administrator_views.add_subject, name='add_subject'),
    path('administrator/subject/view', administrator_views.view_subject, name='view_subject'),
    path('administrator/subject/edit/<int:id>/', administrator_views.edit_subject, name='edit_subject'),
    path('administrator/subject/delete/<int:id>/', administrator_views.delete_subject, name='delete_subject'),

    path('administrator/send-notification/', administrator_views.send_teacher_notification, name='send_teacher_notification'),
    path('administrator/send-student-notification/', administrator_views.send_student_notification, name='send_student_notification'),
    path('administrator/send-canteen-notification/', administrator_views.send_canteen_notification, name='send_canteen_notification'),

    path('administrator/feedback/teachers/', administrator_views.view_teacher_feedback, name='view_teacher_feedback'),
    path('administrator/feedback/students/', administrator_views.view_student_feedback, name='view_student_feedback'),
    path('administrator/feedback/canteen/', administrator_views.view_canteen_feedback, name='view_canteen_feedback'),
    path('administrator/feedback/mark-read/<int:pk>/', administrator_views.mark_feedback_read, name='mark_feedback_read'),

    path('administrator/register-card/', administrator_views.register_card, name='register_card'),
    path('administrator/read-card/', administrator_views.read_card, name='read_card'),
    path('administrator/registered-cards/', administrator_views.view_registered_cards, name='view_registered_cards'),
    path('administrator/scan-and-assign-card/', administrator_views.scan_and_assign_card, name='scan_and_assign_card'),
    path('administrator/get-students-by-classroom/', administrator_views.get_students_by_classroom, name='get_students_by_classroom'),
    path('administrator/assigned-students/', administrator_views.assigned_students, name='assigned_students'),
    path('administrator/student-attendance/', administrator_views.scan_attendance, name='scan_attendance'),
    path('administrator/attendance-list/', administrator_views.attendance_list, name='attendance_list'),
    path('administrator/deactivate-card/<str:card_id>/', administrator_views.deactivate_card, name='deactivate_card'),
    path('administrator/deactivated-cards/', administrator_views.view_deactivated_cards, name='deactivated_cards'),

    path('administrator/scan-and-add-balance/', administrator_views.scan_and_add_balance, name='scan_and_add_balance'),

    #Teacher page URL
    path('teacher/home', teacher_views.home, name='teacher_home'),

    path('teacher/student/view', teacher_views.view_student, name='teacher_view_student'),
    path('teacher/student/add/', teacher_views.add_student, name='teacher_add_student'),
    path('teacher/student/edit/<str:id>/', teacher_views.edit_student, name='teacher_edit_student'),
    path('teacher/student/update/', teacher_views.update_student, name='teacher_update_student'),
    path('teacher/student/delete/<str:admin>/', teacher_views.delete_student, name='teacher_delete_student'),

    path('teacher/add-exam-title/', teacher_views.add_exam_title, name='add_exam_title'),
    path('teacher/delete-exam-title/<int:id>/', teacher_views.delete_exam_title, name='delete_exam_title'),
    path('teacher/add-exam-result/', teacher_views.add_exam_result, name='add_exam_result'),
    path('teacher/exam_result/view/', teacher_views.view_exam_result, name='view_exam_result'),
    path('teacher/exam_result/edit/<int:id>/', teacher_views.edit_exam_result, name='edit_exam_result'),
    path('teacher/exam_result/delete/<int:id>/', teacher_views.delete_exam_result, name='delete_exam_result'),

    path('teacher/timetable/add', teacher_views.add_timetable, name='add_timetable'),
    path('teacher/timetable/view', teacher_views.view_timetable, name='view_timetable'),
    path('teacher/timetable/edit/<int:id>/', teacher_views.edit_timetable, name='edit_timetable'),
    path('teacher/timetable/delete/<int:id>/', teacher_views.delete_timetable, name='delete_timetable'),

    path('teacher/attendance/', teacher_views.teacher_view_attendance, name='teacher_view_attendance'),

    path('teacher/notifications/', teacher_views.view_teacher_notifications, name='view_teacher_notifications'),
    path('teacher/notifications/mark-as-read/<int:notification_id>/', teacher_views.mark_notification_as_read, name='mark_notification_as_read'),
    path('teacher/feedback/', teacher_views.send_teacher_feedback, name='send_teacher_feedback'),
    
    #Student page URL
    path('student/home/', student_views.home, name='student_home'),

    path('student/dietary-details/', student_views.dietary_details, name='dietary_details'),
    path('student/academic-results/', student_views.academic_results, name='academic_results'),
    path('student/timetable/view/', student_views.view_timetable, name='student_view_timetable'),
    path('student/attendance/', student_views.student_attendance, name='student_attendance'),
    path('student/view-account-balance/', student_views.view_account_balance, name='view_account_balance'),
    path('student/transaction-history/', student_views.student_transaction_history, name='student_transaction_history'),

    path('student/notifications/', student_views.view_student_notifications, name='view_student_notifications'),
    path('student/notifications/mark-as-read/<int:notification_id>/', student_views.mark_notification_as_read, name='mark_student_notification_as_read'),
    path('student/feedback/', student_views.send_student_feedback, name='send_student_feedback'),

    #Canteen page URL
    path('canteen/home', canteen_views.home, name='canteen_home'),

    path('canteen/inventory/', canteen_views.inventory_management, name='inventory_management'),
    path('canteen/inventory/item/<int:item_id>/', canteen_views.inventory_item_detail, name='inventory_item_detail'),
    path('canteen/inventory/add/', canteen_views.add_inventory_item, name='add_inventory_item'),
    path('canteen/inventory/edit/<int:item_id>/', canteen_views.edit_inventory_item, name='edit_inventory_item'),
    path('canteen/inventory/delete/<int:item_id>/', canteen_views.delete_inventory_item, name='delete_inventory_item'),


    path('canteen/process-payment/', canteen_views.process_payment, name='process_payment'),
    path('canteen/transaction-history/', canteen_views.transaction_history, name='transaction_history'),

    path('canteen/notifications/', canteen_views.view_canteen_notifications, name='view_canteen_notifications'),
    path('canteen/notifications/mark-as-read/<int:notification_id>/', canteen_views.mark_notification_as_read, name='mark_canteen_notification_as_read'),
    path('canteen/feedback/', canteen_views.send_canteen_feedback, name='send_canteen_feedback'),

]   + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

