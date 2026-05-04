from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.db import models

class GroupUserBackup(models.Model):
    group_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.group_name} - {self.username}"
