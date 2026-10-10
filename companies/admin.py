from django.contrib import admin
from django.contrib import messages
from django.db import transaction

from accounts.audit import describe_changes, log_activity, snapshot_instance
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

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = Company.objects.get(pk=obj.pk)
            before = snapshot_instance(previous)

        with transaction.atomic():
            super().save_model(request, obj, form, change)
            action = 'updated' if change else 'created'
            details = (
                describe_changes(before, snapshot_instance(obj))
                if change
                else 'Company record created.'
            )
            log_activity(
                request.user,
                action,
                'company',
                obj.company_name,
                details
            )

    def delete_model(self, request, obj):
        if obj.receipts.exists():
            self.message_user(
                request,
                'This company cannot be deleted while it has linked receipts.',
                level=messages.ERROR
            )
            return

        with transaction.atomic():
            log_activity(
                request.user,
                'deleted',
                'company',
                obj.company_name,
                'Company record deleted.'
            )
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if queryset.filter(receipts__isnull=False).exists():
            self.message_user(
                request,
                (
                    'Selected companies cannot be deleted while any of them '
                    'have linked receipts.'
                ),
                level=messages.ERROR
            )
            return

        with transaction.atomic():
            for company in queryset.iterator():
                log_activity(
                    request.user,
                    'deleted',
                    'company',
                    company.company_name,
                    'Company record deleted.'
                )
            super().delete_queryset(request, queryset)