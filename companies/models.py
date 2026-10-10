from django.db import models


class Company(models.Model):
    company_name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name