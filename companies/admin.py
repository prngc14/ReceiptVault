from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'contact_person',
        'contact_number',
        'created_at',
    )

    search_fields = (
        'company_name',
        'contact_person',
    )