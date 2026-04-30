"""
URL configuration for doc_verification project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views 
# this dot means current directory, so we are
#importing views from the current directory which contains all the followng files in it:
# # __init__.py, admin.py, apps.py, models.py, tests.py, views.py


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'), #this is home page, when we open the website it will show this page, and it will call the home function in views.py
    path('info/', views.info, name='info'),
    path('logout/', views.logout, name='logout'),

]
