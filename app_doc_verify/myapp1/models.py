from email.policy import default
from django.db import models

# Create your models here.
class charvalue(models.Model):
    name = models.CharField(max_length=100)
    #image = models.ImageField(upload_to='images/')