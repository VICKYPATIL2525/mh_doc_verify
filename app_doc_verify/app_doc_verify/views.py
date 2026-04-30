 # this is used to return a response to the user, we will use this in future when we 
 # will create html files for login, home and logout pages

from django.http import HttpResponse
 # this is used to render the html files, we will use this in 
 # future when we will create html files for login, home and logout pages
from django.shortcuts import render

def home(request):
    #return HttpResponse("Login Page")  
    return render(request, 'index.html') # this will render the index.html file which is in templates folder, and it will show the content of index.html file when we open the website  

def info(request):
    return render(request, 'info.html') # this will render the info.html file which is in templates folder, and it will show the content of info.html file when we open the website")

def logout(request):
    return HttpResponse("Logout Page")
