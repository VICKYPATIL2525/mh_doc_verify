from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('application/<int:pk>/review/', views.review_application, name='review_application'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('comments/', views.all_comments, name='all_comments'),
    path('export/', views.export_csv, name='export_csv'),
    path('logout/', views.logout_view, name='logout'),
]
