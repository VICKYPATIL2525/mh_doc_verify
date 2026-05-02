from django.contrib import admin
from .models import DoctorApplication, Comment

@admin.register(DoctorApplication)
class DoctorApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'specialization', 'status', 'submitted_at', 'reviewed_by')
    list_filter = ('status', 'specialization')
    search_fields = ('full_name', 'email')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('application', 'author', 'created_at')
    list_filter = ('author',)
